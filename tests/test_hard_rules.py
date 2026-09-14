import pytest

from analytics.hard_rules import HardRule, evaluate_hard_rules, price_not_more_than_fair_value_rule


def test_price_rule_passes_below_and_at_twenty_percent_boundary():
    rule = price_not_more_than_fair_value_rule()
    assert evaluate_hard_rules((rule,), {"price": 100, "fair_value": 100}, "ENTRY").results[0].status == "passed"
    assert evaluate_hard_rules((rule,), {"price": 120, "fair_value": 100}, "ENTRY").results[0].status == "passed"


def test_price_rule_fails_and_overrides_favorable_weighted_recommendation():
    result = evaluate_hard_rules((price_not_more_than_fair_value_rule(),), {"price": 120.01, "fair_value": 100}, "ENTRY")
    assert result.results[0].status == "failed"
    assert result.recommendation == "NO_ENTRY"
    assert result.overridden
    assert result.results[0].observed_values == {"price": 120.01, "fair_value": 100.0}


def test_missing_invalid_and_nonpositive_inputs_are_not_evaluable():
    rule = price_not_more_than_fair_value_rule()
    for values in ({"price": 100}, {"price": "bad", "fair_value": 100}, {"price": 100, "fair_value": 0}):
        result = evaluate_hard_rules((rule,), values, "ENTRY")
        assert result.results[0].status == "not_evaluable"
        assert result.recommendation == "NOT_EVALUABLE"
        assert "required" in result.results[0].reason or "positive" in result.results[0].reason


def test_multiple_rules_are_deterministic_and_failed_non_entry_does_not_rewrite_rating():
    rules = (
        HardRule("minimum_quality", ("quality",), "gte", 0.5, "quality must be acceptable"),
        price_not_more_than_fair_value_rule(),
    )
    result = evaluate_hard_rules(rules, {"quality": 0.4, "price": 100, "fair_value": 100}, "WATCH")
    assert [item.rule_id for item in result.results] == ["minimum_quality", "price_not_more_than_fair_value"]
    assert result.results[0].status == "failed"
    assert result.results[1].status == "passed"
    assert result.recommendation == "WATCH"


def test_rule_representation_rejects_invalid_operator():
    with pytest.raises(ValueError, match="unsupported"):
        HardRule("bad", ("value",), "contains", 1, "not supported")
