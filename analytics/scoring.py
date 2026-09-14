"""Versioned, explainable composite scoring.

The weighted score intentionally contains no hard decision rules. A separate
caller may evaluate hard rules against the returned score and source data.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


SUPPORTED_COMPONENTS = ("valuation", "forecasts", "momentum", "quality", "catalysts", "risk")


@dataclass(frozen=True)
class ScoreNormalization:
    minimum: float = 0.0
    maximum: float = 1.0
    invert: bool = False


@dataclass(frozen=True)
class ScoreConfiguration:
    version: str = "v1"
    preset: str = "balanced"
    weights: Mapping[str, float] | None = None
    normalizations: Mapping[str, ScoreNormalization] | None = None

    def resolved_weights(self) -> dict[str, float]:
        return dict(self.weights or {"valuation": 0.25, "forecasts": 0.15, "momentum": 0.20, "quality": 0.20, "catalysts": 0.10, "risk": 0.10})

    def resolved_normalizations(self) -> dict[str, ScoreNormalization]:
        return {component: (self.normalizations or {}).get(component, ScoreNormalization()) for component in SUPPORTED_COMPONENTS}


@dataclass(frozen=True)
class ScoreContribution:
    component: str
    weight: float
    value: float | None
    normalized_value: float | None = None
    contribution: float = 0.0
    status: str = "not_evaluable"
    explanation: str = ""


@dataclass(frozen=True)
class CompositeScoreResult:
    aggregate_score: float | None
    contributions: tuple[ScoreContribution, ...]
    configuration_version: str
    preset: str
    total_weight: float
    evaluable_weight: float
    coverage: float
    confidence: str
    errors: tuple[str, ...] = ()
    explanation: str = ""

    @property
    def valid(self) -> bool:
        return not self.errors and self.aggregate_score is not None


def validate_score_configuration(configuration: ScoreConfiguration) -> tuple[str, ...]:
    errors: list[str] = []
    weights = configuration.resolved_weights()
    if not configuration.version.strip():
        errors.append("configuration version must not be empty")
    if set(weights) != set(SUPPORTED_COMPONENTS):
        missing = sorted(set(SUPPORTED_COMPONENTS) - set(weights))
        unsupported = sorted(set(weights) - set(SUPPORTED_COMPONENTS))
        if missing:
            errors.append("missing components: " + ", ".join(missing))
        if unsupported:
            errors.append("unsupported components: " + ", ".join(unsupported))
    for component, weight in weights.items():
        if not _finite(weight) or weight < 0:
            errors.append(f"weight for {component} must be finite and non-negative")
    if sum(float(value) for value in weights.values()) <= 0:
        errors.append("at least one score weight must be positive")
    normalizations = configuration.resolved_normalizations()
    unsupported_normalizations = sorted(set(configuration.normalizations or {}) - set(SUPPORTED_COMPONENTS))
    if unsupported_normalizations:
        errors.append("unsupported normalization components: " + ", ".join(unsupported_normalizations))
    for component, rule in normalizations.items():
        if not _finite(rule.minimum) or not _finite(rule.maximum) or rule.minimum >= rule.maximum:
            errors.append(f"normalization range for {component} must be finite with minimum below maximum")
    return tuple(dict.fromkeys(errors))


def calculate_composite_score(
    component_values: Mapping[str, float | None],
    configuration: ScoreConfiguration | None = None,
) -> CompositeScoreResult:
    """Calculate a weighted score with missing components reported explicitly."""

    configuration = configuration or ScoreConfiguration()
    errors = validate_score_configuration(configuration)
    unsupported_values = sorted(set(component_values) - set(SUPPORTED_COMPONENTS))
    if unsupported_values:
        errors = (*errors, "unsupported component values: " + ", ".join(unsupported_values))
    if errors:
        return CompositeScoreResult(None, (), configuration.version, configuration.preset, 0.0, 0.0, 0.0, "insufficient", errors, "invalid score configuration")
    weights = configuration.resolved_weights()
    rules = configuration.resolved_normalizations()
    total_weight = sum(float(value) for value in weights.values())
    contributions: list[ScoreContribution] = []
    evaluable_weight = 0.0
    weighted_sum = 0.0
    for component in SUPPORTED_COMPONENTS:
        weight = float(weights[component])
        raw_value = component_values.get(component)
        rule = rules[component]
        normalized, status, explanation = _normalize(raw_value, rule)
        if normalized is None:
            contributions.append(ScoreContribution(component, weight, raw_value, None, 0.0, status, explanation))
            continue
        contribution = normalized * weight
        weighted_sum += contribution
        evaluable_weight += weight
        contributions.append(ScoreContribution(component, weight, raw_value, normalized, contribution, "ok", explanation))
    coverage = evaluable_weight / total_weight if total_weight else 0.0
    aggregate = weighted_sum / evaluable_weight if evaluable_weight else None
    confidence = "high" if coverage >= 0.9 else "moderate" if coverage >= 0.6 else "reduced" if coverage > 0 else "insufficient"
    explanation = "aggregate is normalized by evaluable component weight; missing components reduce coverage and confidence"
    return CompositeScoreResult(aggregate, tuple(contributions), configuration.version, configuration.preset, total_weight, evaluable_weight, coverage, confidence, (), explanation)


def _normalize(value: float | None, rule: ScoreNormalization) -> tuple[float | None, str, str]:
    if value is None:
        return None, "not_evaluable", "component value is missing"
    if not _finite(value):
        return None, "not_evaluable", "component value is not finite"
    if value < rule.minimum or value > rule.maximum:
        return None, "invalid", f"component value must be between {rule.minimum} and {rule.maximum}"
    normalized = (float(value) - rule.minimum) / (rule.maximum - rule.minimum)
    if rule.invert:
        normalized = 1 - normalized
    return normalized, "ok", "normalized using the versioned configuration range"


def _finite(value: object) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


CompositeScore = CompositeScoreResult
ScoreConfig = ScoreConfiguration
build_composite_score = calculate_composite_score
