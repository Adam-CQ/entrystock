import pytest
from django.core.management import call_command
from django.urls import reverse

from companies.forms import PeerGroupForm
from companies.models import Company, PeerGroupMember, PeerGroupProposal


pytestmark = pytest.mark.django_db


@pytest.fixture
def fixture_companies():
    call_command("load_fixture_data", verbosity=0)
    return list(Company.objects.order_by("id"))


def test_peer_workflow_proposes_and_confirms_group(fixture_companies):
    selected = fixture_companies[0]
    client = __import__("django.test", fromlist=["Client"]).Client()

    response = client.get(reverse("peer-group", args=[selected.pk]))
    proposal = PeerGroupProposal.objects.get(company=selected)
    peers = list(proposal.members.values_list("peer_id", flat=True))

    assert response.status_code == 200
    assert proposal.status == PeerGroupProposal.Status.PROPOSED
    assert len(peers) == 5
    assert proposal.members.first().reasons

    response = client.post(reverse("peer-group", args=[selected.pk]), {"selected_peers": peers, "confirm": "on"})
    proposal.refresh_from_db()
    assert response.status_code == 302
    assert proposal.status == PeerGroupProposal.Status.CONFIRMED


def test_peer_workflow_preserves_additions_and_removals_on_reopen(fixture_companies):
    selected = fixture_companies[0]
    added = Company.objects.create(legal_name="Eligible Added Corporation", common_name="Eligible Added")
    client = __import__("django.test", fromlist=["Client"]).Client()
    client.get(reverse("peer-group", args=[selected.pk]))
    proposal = PeerGroupProposal.objects.get(company=selected)
    initial = list(proposal.members.values_list("peer_id", flat=True))

    client.post(reverse("peer-group", args=[selected.pk]), {"selected_peers": [initial[1], added.pk]})
    removed_member = proposal.members.get(peer_id=initial[0])
    added_member = proposal.members.get(peer_id=added.pk)

    assert removed_member.selected is False
    assert removed_member.origin == PeerGroupMember.Origin.USER_REMOVED
    assert added_member.origin == PeerGroupMember.Origin.USER_ADDED
    reopened = client.get(reverse("peer-group", args=[selected.pk]))
    assert str(added.pk) in reopened.content.decode()


def test_peer_form_rejects_self_and_duplicate_or_under_minimum_confirmation(fixture_companies):
    proposal = PeerGroupProposal.objects.create(company=fixture_companies[0], eligible_count=6, sufficient_universe=True, explanation="test")
    form = PeerGroupForm(proposal=proposal, data={"selected_peers": [fixture_companies[0].pk], "confirm": "on"})
    assert not form.is_valid()
    assert "valid choice" in str(form.errors)

    form = PeerGroupForm(proposal=proposal, data={"selected_peers": [fixture_companies[1].pk], "confirm": "on"})
    assert not form.is_valid()
    assert "at least 5" in str(form.errors)


def test_insufficient_universe_can_be_confirmed_only_as_complete_set(fixture_companies):
    proposal = PeerGroupProposal.objects.create(company=fixture_companies[0], eligible_count=2, sufficient_universe=False, explanation="Insufficient")
    PeerGroupMember.objects.create(proposal=proposal, peer=fixture_companies[1])
    PeerGroupMember.objects.create(proposal=proposal, peer=fixture_companies[2])
    form = PeerGroupForm(proposal=proposal, data={"selected_peers": [fixture_companies[1].pk, fixture_companies[2].pk], "confirm": "on"})
    assert form.is_valid()
