import pytest

from analytics.hard_rules import evaluate_hard_rules, price_not_more_than_fair_value_rule
from analytics.recommendations import Evidence, RecommendationInput, build_recommendation


def test_favorable_recommendation_contains_metrics_evidence_and_disclaimer():
    result = build_recommendation(RecommendationInput(
        weighted_rating="ENTRY", current_price=100, fair_value_low=110, fair_value_high=130,
        expected_return=0.3, entry_zone_low=90, entry_zone_high=105, confidence="high",
        positive_drivers=(Evidence("valuation", 0.3, "DCF", "2026-09-14", "8% growth"),),
        negative_drivers=(Evidence("risk", "high", "quality", "2026-09-14"),), source="fixture", as_of="2026-09-14",
    ))
    assert result.rating == "ENTRY"
    assert result.fair_value_range == (110.0, 130.0)
    assert result.valuation_gap == pytest.approx(0.3)
    assert result.entry_zone == (90.0, 105.0)
    assert "DCF" in result.explanation and "8% growth" in result.explanation
    assert "not financial advice" in result.disclaimer


def test_failed_hard_rule_is_visible_over_favorable_score():
    rules = evaluate_hard_rules((price_not_more_than_fair_value_rule(),), {"price": 121, "fair_value": 100}, "ENTRY")
    result = build_recommendation(RecommendationInput("ENTRY", current_price=121, fair_value_low=90, fair_value_high=100, confidence="high", hard_rules=rules))
    assert result.rating == "NO_ENTRY"
    assert result.hard_rule_override
    assert "Hard-rule override" in result.explanation


def test_missing_data_is_not_fabricated_and_reduces_confidence():
    result = build_recommendation(RecommendationInput("WATCH", confidence="high", data_quality_limitations=("fair value missing",), uncertainty=("forecast disagreement",)))
    assert result.fair_value_range is None
    assert result.valuation_gap is None
    assert result.confidence == "insufficient"
    assert "not evaluable" in result.explanation
    assert "Data-quality limitations" in result.explanation


def test_boundary_and_invalid_rating_are_deterministic():
    result = build_recommendation(RecommendationInput("ENTRY", current_price=120, fair_value_low=100, fair_value_high=100, confidence="moderate"))
    assert result.valuation_gap == pytest.approx(-1 / 6)
    try:
        build_recommendation(RecommendationInput("BUY"))
    except ValueError as exc:
        assert "rating" in str(exc)
    else:
        raise AssertionError("invalid rating should be rejected")
