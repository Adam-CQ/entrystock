"""Structured, cautious recommendation output for the analytical PoC."""

from dataclasses import dataclass
from typing import Any, Mapping

from analytics.hard_rules import HardRulesResult
from analytics.scoring import CompositeScoreResult


RATING_SCALE = ("NO_ENTRY", "AVOID", "WATCH", "ENTRY")
VALUATION_GAP_DECIMAL_PLACES = 10


@dataclass(frozen=True)
class Evidence:
    name: str
    value: Any
    source: str
    as_of: str | None = None
    assumption: str | None = None


@dataclass(frozen=True)
class RecommendationInput:
    weighted_rating: str
    current_price: float | None = None
    fair_value_low: float | None = None
    fair_value_high: float | None = None
    expected_return: float | None = None
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    confidence: str = "insufficient"
    score: CompositeScoreResult | None = None
    hard_rules: HardRulesResult | None = None
    positive_drivers: tuple[Evidence, ...] = ()
    negative_drivers: tuple[Evidence, ...] = ()
    catalysts: tuple[Evidence, ...] = ()
    risks: tuple[Evidence, ...] = ()
    data_quality_limitations: tuple[str, ...] = ()
    uncertainty: tuple[str, ...] = ()
    source: str = "shared analytics inputs"
    as_of: str | None = None


@dataclass(frozen=True)
class RecommendationResult:
    rating: str
    rating_scale: tuple[str, ...]
    fair_value_range: tuple[float, float] | None
    valuation_gap: float | None
    expected_return: float | None
    entry_zone: tuple[float, float] | None
    confidence: str
    positive_drivers: tuple[Evidence, ...]
    negative_drivers: tuple[Evidence, ...]
    catalysts: tuple[Evidence, ...]
    risks: tuple[Evidence, ...]
    data_quality_limitations: tuple[str, ...]
    uncertainty: tuple[str, ...]
    hard_rule_override: str | None
    explanation: str
    disclaimer: str = "This is an analytical PoC output, not financial advice or a guarantee."


def build_recommendation(inputs: RecommendationInput) -> RecommendationResult:
    """Build deterministic output without inventing unavailable analytical facts."""

    _validate_rating(inputs.weighted_rating)
    fair_range = _fair_range(inputs.fair_value_low, inputs.fair_value_high)
    gap = _valuation_gap(inputs.current_price, fair_range[1] if fair_range else None)
    confidence = _reduce_confidence(inputs.confidence, inputs.data_quality_limitations, inputs.uncertainty, gap)
    rating = inputs.weighted_rating
    override = None
    if inputs.hard_rules is not None:
        rating = inputs.hard_rules.recommendation
        if inputs.hard_rules.overridden:
            override = inputs.hard_rules.explanation
    explanation = _explain(inputs, rating, fair_range, gap, confidence, override)
    return RecommendationResult(
        rating=rating,
        rating_scale=RATING_SCALE,
        fair_value_range=fair_range,
        valuation_gap=gap,
        expected_return=_finite_or_none(inputs.expected_return),
        entry_zone=_fair_range(inputs.entry_zone_low, inputs.entry_zone_high),
        confidence=confidence,
        positive_drivers=inputs.positive_drivers,
        negative_drivers=inputs.negative_drivers,
        catalysts=inputs.catalysts,
        risks=inputs.risks,
        data_quality_limitations=inputs.data_quality_limitations,
        uncertainty=inputs.uncertainty,
        hard_rule_override=override,
        explanation=explanation,
    )


def _explain(inputs: RecommendationInput, rating: str, fair_range: tuple[float, float] | None, gap: float | None, confidence: str, override: str | None) -> str:
    parts = [f"Rating: {rating}. Confidence: {confidence}."]
    if fair_range is not None:
        parts.append(f"Fair value range is {fair_range[0]:.2f}–{fair_range[1]:.2f}.")
    else:
        parts.append("Fair value range is not evaluable because required valuation inputs are missing or invalid.")
    if gap is not None:
        parts.append(f"Valuation gap to the high end of the range is {gap:.1%} based on {inputs.source} as of {inputs.as_of or 'an unspecified date'}.")
    _append_evidence(parts, "Positive driver", inputs.positive_drivers)
    _append_evidence(parts, "Negative driver", inputs.negative_drivers)
    if override:
        parts.append(f"Hard-rule override: {override}.")
    if inputs.data_quality_limitations:
        parts.append("Data-quality limitations: " + "; ".join(inputs.data_quality_limitations) + ".")
    if inputs.uncertainty:
        parts.append("Uncertainty: " + "; ".join(inputs.uncertainty) + ".")
    parts.append("This analytical PoC is not financial advice and does not guarantee an outcome.")
    return " ".join(parts)


def _append_evidence(parts: list[str], label: str, evidence: tuple[Evidence, ...]) -> None:
    for item in evidence:
        details = f"{item.name}={item.value} (source: {item.source}"
        if item.as_of:
            details += f", date: {item.as_of}"
        if item.assumption:
            details += f", assumption: {item.assumption}"
        parts.append(f"{label}: {details}).")


def _fair_range(low: float | None, high: float | None) -> tuple[float, float] | None:
    low_value, high_value = _finite_or_none(low), _finite_or_none(high)
    if low_value is None or high_value is None or low_value < 0 or low_value > high_value:
        return None
    return low_value, high_value


def _valuation_gap(current: float | None, fair_high: float | None) -> float | None:
    current_value = _finite_or_none(current)
    if current_value is None or current_value <= 0 or fair_high is None:
        return None
    return round(fair_high / current_value - 1, VALUATION_GAP_DECIMAL_PLACES)


def _reduce_confidence(confidence: str, limitations: tuple[str, ...], uncertainty: tuple[str, ...], gap: float | None) -> str:
    levels = {"insufficient": 0, "reduced": 1, "moderate": 2, "high": 3}
    if confidence not in levels:
        return "insufficient"
    score = levels[confidence] - min(2, len(limitations)) - (1 if uncertainty else 0)
    if gap is None:
        score = min(score, 0)
    return next(level for level, value in levels.items() if value == max(0, min(3, score)))


def _finite_or_none(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _validate_rating(rating: str) -> None:
    if rating not in RATING_SCALE:
        raise ValueError(f"rating must be one of {RATING_SCALE}")


Recommendation = RecommendationResult
create_recommendation = build_recommendation
