"""Independent hard decision rules for recommendation constraints.

Hard rules are evaluated after weighted scoring and cannot be changed by score
weights.  Rule thresholds use the same units as the observed input unless the
operator explicitly describes a ratio or percentage.
"""

from dataclasses import dataclass
from math import isclose, isfinite
from typing import Mapping


SUPPORTED_OPERATORS = ("eq", "neq", "gt", "gte", "lt", "lte", "max_percent_above")


@dataclass(frozen=True)
class HardRule:
    """A serializable rule definition evaluated against named observations."""

    rule_id: str
    inputs: tuple[str, ...]
    operator: str
    threshold: float
    reason: str

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("rule_id must not be empty")
        if not self.inputs:
            raise ValueError("at least one rule input is required")
        if self.operator not in SUPPORTED_OPERATORS:
            raise ValueError(f"unsupported rule operator: {self.operator}")
        if not isfinite(float(self.threshold)):
            raise ValueError("rule threshold must be finite")
        if not self.reason.strip():
            raise ValueError("rule reason must not be empty")


@dataclass(frozen=True)
class HardRuleResult:
    rule_id: str
    status: str
    observed_values: Mapping[str, float | None]
    operator: str
    threshold: float
    reason: str


@dataclass(frozen=True)
class HardRulesResult:
    results: tuple[HardRuleResult, ...]
    weighted_recommendation: str
    recommendation: str
    overridden: bool
    explanation: str

    @property
    def valid(self) -> bool:
        return all(result.status != "not_evaluable" for result in self.results)


def price_not_more_than_fair_value_rule(max_premium: float = 0.20) -> HardRule:
    """Return the standard rule that blocks ENTRY above fair value + premium."""

    return HardRule(
        rule_id="price_not_more_than_fair_value",
        inputs=("price", "fair_value"),
        operator="max_percent_above",
        threshold=max_premium,
        reason="ENTRY is allowed only when price is no more than 20% above fair value",
    )


def evaluate_hard_rules(
    rules: tuple[HardRule, ...] | list[HardRule],
    observed_values: Mapping[str, object],
    weighted_recommendation: str,
) -> HardRulesResult:
    """Evaluate rules in declaration order and apply deterministic precedence.

    Any failed rule changes ``ENTRY`` to ``NO_ENTRY``.  A failed rule never
    downgrades a non-ENTRY rating, while a not-evaluable rule changes ENTRY to
    ``NOT_EVALUABLE`` so missing critical inputs cannot silently pass.
    """

    evaluated = tuple(_evaluate_rule(rule, observed_values) for rule in rules)
    failed = any(result.status == "failed" for result in evaluated)
    not_evaluable = any(result.status == "not_evaluable" for result in evaluated)
    if failed:
        recommendation = "NO_ENTRY" if weighted_recommendation == "ENTRY" else weighted_recommendation
        overridden = weighted_recommendation == "ENTRY"
        explanation = "a failed hard rule takes precedence over an ENTRY weighted recommendation"
    elif not_evaluable and weighted_recommendation == "ENTRY":
        recommendation = "NOT_EVALUABLE"
        overridden = True
        explanation = "ENTRY is not allowed because a required hard-rule input is not evaluable"
    else:
        recommendation = weighted_recommendation
        overridden = False
        explanation = "all applicable hard rules passed; weighted recommendation is unchanged"
    return HardRulesResult(evaluated, weighted_recommendation, recommendation, overridden, explanation)


def _evaluate_rule(rule: HardRule, observed: Mapping[str, object]) -> HardRuleResult:
    values = {name: _number(observed.get(name)) for name in rule.inputs}
    if any(value is None for value in values.values()):
        reason = f"{rule.reason}; required inputs are missing or not finite"
        return HardRuleResult(rule.rule_id, "not_evaluable", values, rule.operator, rule.threshold, reason)
    numbers = tuple(value for value in values.values() if value is not None)
    if rule.operator == "max_percent_above":
        price, fair_value = numbers
        if fair_value <= 0:
            reason = f"{rule.reason}; fair_value must be positive to calculate the premium"
            return HardRuleResult(rule.rule_id, "not_evaluable", values, rule.operator, rule.threshold, reason)
        observed_ratio = price / fair_value
        passed = observed_ratio <= 1 + rule.threshold
        detail = f"price/fair_value={observed_ratio:.6g}, allowed maximum={1 + rule.threshold:.6g}"
    else:
        observed_ratio = numbers[0]
        passed = _compare(observed_ratio, rule.operator, rule.threshold)
        detail = f"observed={observed_ratio:.6g}, threshold={rule.threshold:.6g}"
    status = "passed" if passed else "failed"
    return HardRuleResult(rule.rule_id, status, values, rule.operator, rule.threshold, f"{rule.reason}; {detail}")


def _compare(value: float, operator: str, threshold: float) -> bool:
    if operator == "eq":
        return isclose(value, threshold, rel_tol=1e-12, abs_tol=1e-12)
    return {"neq": value != threshold, "gt": value > threshold, "gte": value >= threshold, "lt": value < threshold, "lte": value <= threshold}[operator]


def _number(value: object) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if isfinite(converted) else None


HardDecisionRule = HardRule
evaluate_rules = evaluate_hard_rules
