from dataclasses import replace
from decimal import Decimal

from analytics.fixture_provider import FixtureProvider
from analytics.peer_analysis import propose_peers


def _profiles():
    provider = FixtureProvider()
    return [provider.get_company_metadata(identifier) for identifier in provider.company_ids]


def test_peer_proposal_is_ranked_explainable_and_excludes_self():
    profiles = _profiles()
    proposal = propose_peers(profiles[0], profiles[1:])

    assert proposal.sufficient_universe is True
    assert len(proposal.candidates) == 5
    assert all(candidate.identifier != profiles[0].company_id for candidate in proposal.candidates)
    assert proposal.candidates[0].identifier == "fixture-peer-1"
    assert any("industry: match" in reason for reason in proposal.candidates[0].reasons)
    assert proposal.candidates[0].component_scores


def test_peer_ties_are_resolved_by_identifier_and_missing_attributes_are_explicit():
    profiles = _profiles()
    first = replace(profiles[1], company_id="a-peer", legal_name="A Peer", common_name="A Peer")
    second = replace(profiles[2], company_id="z-peer", legal_name="Z Peer", common_name="Z Peer", size=profiles[1].size, growth=profiles[1].growth, profitability=profiles[1].profitability, capital_intensity=profiles[1].capital_intensity, themes=profiles[1].themes)
    selected = replace(profiles[0], industry=None, themes=())
    proposal = propose_peers(selected, [second, first], limit=2)

    assert [candidate.identifier for candidate in proposal.candidates] == ["a-peer", "z-peer"]
    assert any("industry: unavailable" in reason for reason in proposal.candidates[0].reasons)
    assert any("theme: unavailable" in reason for reason in proposal.candidates[0].reasons)


def test_peer_proposal_reports_insufficient_universe_without_fabricating_candidates():
    profiles = _profiles()
    proposal = propose_peers(profiles[0], profiles[1:3])

    assert proposal.sufficient_universe is False
    assert len(proposal.candidates) == 2
    assert "Insufficient peer universe" in proposal.explanation
