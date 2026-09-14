from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from analytics.fixture_provider import FixtureProvider
from analytics.peer_analysis import propose_peers
from companies.forms import PeerGroupForm
from companies.models import Company, PeerGroupMember, PeerGroupProposal
from analytics.dashboard import build_dashboard_context
from market_data.models import PriceObservation


def dashboard(request):
    companies = Company.objects.filter(is_active=True).select_related("sector", "industry")
    selected_id = request.GET.get("company")
    company = get_object_or_404(companies, pk=selected_id) if selected_id else companies.first()
    context = {"companies": companies, "selected_company": company}
    if company:
        proposal = _get_or_create_proposal(company)
        peers = tuple(member.peer for member in proposal.members.filter(selected=True).select_related("peer"))
        security = company.securities.first()
        prices = tuple(PriceObservation.objects.filter(security=security).order_by("observed_at")) if security else ()
        context.update(build_dashboard_context(company, proposal, peers, prices))
        context["forecast_sources"] = ("management", "consensus", "internal")
        context["dcf_assumptions"] = (("Forecast years", context["assumptions"].forecast_years), ("Revenue growth", "10%"), ("Operating margin", "8%"), ("Tax rate", "21%"), ("Reinvestment rate", "35%"), ("Discount rate", "10%"), ("Terminal growth", "3%"))
    return render(request, "dashboard.html", context)


def peer_group(request, company_id: int):
    company = get_object_or_404(Company, pk=company_id)
    proposal = _get_or_create_proposal(company)
    if request.method == "POST":
        form = PeerGroupForm(proposal=proposal, data=request.POST)
        if form.is_valid():
            _save_selection(proposal, form.cleaned_data["selected_peers"])
            if form.cleaned_data.get("confirm"):
                proposal.status = PeerGroupProposal.Status.CONFIRMED
                proposal.save(update_fields=["status"])
            messages.success(request, "Peer group saved.")
            return redirect("peer-group", company_id=company.pk)
    else:
        selected = proposal.members.filter(selected=True).values_list("peer_id", flat=True)
        form = PeerGroupForm(proposal=proposal, initial={"selected_peers": selected})
    return render(request, "companies/peer_group.html", {"company": company, "proposal": proposal, "form": form})


def _get_or_create_proposal(company: Company) -> PeerGroupProposal:
    existing = PeerGroupProposal.objects.filter(company=company).first()
    if existing:
        return existing
    provider = FixtureProvider()
    selected = next((provider.get_company_metadata(identifier) for identifier in provider.company_ids if provider.get_company_metadata(identifier).legal_name == company.legal_name), None)
    if selected is None:
        raise ValueError(f"No provider profile exists for {company.legal_name}")
    profiles = tuple(provider.get_company_metadata(identifier) for identifier in provider.company_ids)
    result = propose_peers(selected, profiles)
    proposal = PeerGroupProposal.objects.create(company=company, source="fixture", eligible_count=result.eligible_count, minimum_candidates=result.minimum_candidates, sufficient_universe=result.sufficient_universe, explanation=result.explanation)
    for rank, candidate in enumerate(result.candidates, start=1):
        peer = Company.objects.get(legal_name=provider.get_company_metadata(candidate.identifier).legal_name)
        PeerGroupMember.objects.create(proposal=proposal, peer=peer, rank=rank, score=candidate.score, confidence=candidate.confidence, reasons=list(candidate.reasons), component_scores=dict(candidate.component_scores))
    return proposal


def _save_selection(proposal: PeerGroupProposal, selected_peers) -> None:
    selected_ids = {peer.pk for peer in selected_peers}
    existing = {member.peer_id: member for member in proposal.members.all()}
    for peer_id, member in existing.items():
        member.selected = peer_id in selected_ids
        if not member.selected:
            member.origin = PeerGroupMember.Origin.USER_REMOVED
        member.save(update_fields=["selected", "origin"])
    for peer in selected_peers:
        if peer.pk not in existing:
            PeerGroupMember.objects.create(proposal=proposal, peer=peer, origin=PeerGroupMember.Origin.USER_ADDED, selected=True)
