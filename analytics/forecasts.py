"""Forecast source and period value objects."""

from dataclasses import dataclass, field
from datetime import date, datetime
from math import isfinite
from typing import Literal, Mapping, Sequence

ForecastSource = Literal["management", "consensus", "internal"]


@dataclass(frozen=True)
class ForecastValue:
    source: ForecastSource
    measure: str
    period: str
    value: float | None
    units: str | None = None
    retrieved_at: datetime | None = None
    effective_date: date | None = None


@dataclass(frozen=True)
class ForecastComparison:
    measure: str
    period: str
    source_values: dict[ForecastSource, ForecastValue | None]
    comparable: bool
    absolute_divergence: float | None
    relative_divergence: float | None
    missing_sources: tuple[ForecastSource, ...] = ()
    stale_sources: tuple[ForecastSource, ...] = ()
    reason: str | None = None


def compare_forecasts(
    values: tuple[ForecastValue, ...] | list[ForecastValue],
    *,
    as_of: date | None = None,
    max_age_days: int = 365,
) -> tuple[ForecastComparison, ...]:
    """Compare source forecasts only when measure, period, and units align.

    Sources remain independently inspectable. Missing records, stale effective
    dates, and incompatible units are returned as explicit comparison state;
    no aggregate forecast is calculated.
    """

    if max_age_days < 0:
        raise ValueError("max_age_days must not be negative")
    grouped: dict[tuple[str, str], list[ForecastValue]] = {}
    for value in values:
        if value.source not in {"management", "consensus", "internal"}:
            raise ValueError(f"unsupported forecast source: {value.source}")
        grouped.setdefault((value.measure, value.period), []).append(value)
    output = []
    for (measure, period), group in sorted(grouped.items()):
        source_values = {source: next((item for item in group if item.source == source), None) for source in ("management", "consensus", "internal")}
        missing = tuple(source for source, value in source_values.items() if value is None)
        stale = tuple(source for source, value in source_values.items() if _is_stale(value, as_of, max_age_days))
        present = tuple(value for value in source_values.values() if value is not None)
        units = {value.units for value in present}
        numeric = tuple(value.value for value in present if value.value is not None and isfinite(value.value))
        comparable = not missing and len(units) == 1 and len(numeric) == 3
        absolute = max(numeric) - min(numeric) if comparable else None
        relative = absolute / abs(min(numeric)) if comparable and min(numeric) != 0 else None
        reason = None
        if missing:
            reason = "missing source: " + ", ".join(missing)
        elif len(units) != 1:
            reason = "incompatible units"
        elif len(numeric) != 3:
            reason = "missing numeric value"
        elif stale:
            reason = "stale source: " + ", ".join(stale)
        output.append(ForecastComparison(measure, period, source_values, comparable, absolute, relative, missing, stale, reason))
    return tuple(output)


def _is_stale(value: ForecastValue | None, as_of: date | None, max_age_days: int) -> bool:
    return bool(value and as_of and value.effective_date and (as_of - value.effective_date).days > max_age_days)


InternalMeasure = Literal["revenue", "ebitda", "eps", "free_cash_flow"]
SUPPORTED_INTERNAL_MEASURES: tuple[InternalMeasure, ...] = ("revenue", "ebitda", "eps", "free_cash_flow")


@dataclass(frozen=True)
class HistoricalFinancialPeriod:
    """One point-in-time historical period; values must not include future data."""

    period: str
    metrics: Mapping[str, float]


@dataclass(frozen=True)
class InternalForecastConfig:
    """Baseline assumptions: 3 annual periods, revenue-led growth, and margins."""

    horizon_years: int = 3
    measures: tuple[InternalMeasure, ...] = SUPPORTED_INTERNAL_MEASURES
    growth_assumptions: Mapping[str, float] = field(default_factory=dict)
    margin_assumptions: Mapping[str, float] = field(default_factory=lambda: {"ebitda": 0.15, "free_cash_flow": 0.08})


@dataclass(frozen=True)
class InternalForecastPoint:
    measure: InternalMeasure
    period: str
    value: float | None
    source_periods: tuple[str, ...]
    confidence: Literal["high", "moderate", "reduced", "insufficient"]


@dataclass(frozen=True)
class InternalForecastResult:
    forecasts: tuple[InternalForecastPoint, ...]
    assumptions: Mapping[str, float]
    source_periods: tuple[str, ...]
    data_coverage: Mapping[str, int]
    confidence: Literal["high", "moderate", "reduced", "insufficient"]
    warnings: tuple[str, ...] = ()


def forecast_internal(
    history: Sequence[HistoricalFinancialPeriod],
    config: InternalForecastConfig | None = None,
) -> InternalForecastResult:
    """Build a deterministic baseline forecast without fabricating history.

    Revenue and direct measures grow from the latest available observation.
    EBITDA and free cash flow use explicit margins against forecast revenue.
    Missing assumptions can be derived only from two adjacent historical
    observations; otherwise the measure is returned as insufficient data.
    """

    config = config or InternalForecastConfig()
    _validate_internal_config(config)
    if not history:
        return InternalForecastResult((), dict(config.growth_assumptions) | dict(config.margin_assumptions), (), {measure: 0 for measure in config.measures}, "insufficient", ("No historical periods supplied.",))
    periods = tuple(history)
    _validate_history(periods, config)
    source_periods = tuple(item.period for item in periods)
    latest = periods[-1]
    coverage = {measure: sum(measure in item.metrics for item in periods) for measure in config.measures}
    assumptions = dict(config.growth_assumptions)
    assumptions.update(config.margin_assumptions)
    growth = {measure: _growth_for(measure, periods, config.growth_assumptions) for measure in config.measures}
    assumptions.update({measure: value for measure, value in growth.items() if value is not None})
    overall = _confidence(min(coverage.values(), default=0), len(periods))
    points: list[InternalForecastPoint] = []
    for year in range(1, config.horizon_years + 1):
        period = f"{latest.period}+{year}Y"
        for measure in config.measures:
            value = _forecast_value(measure, latest.metrics, growth.get(measure), growth.get("revenue"), config.margin_assumptions, year)
            point_confidence = _confidence(coverage[measure], len(periods)) if value is not None else "insufficient"
            points.append(InternalForecastPoint(measure, period, value, source_periods, point_confidence))
    warnings = tuple(f"{measure}: incomplete historical coverage ({coverage[measure]} period(s))" for measure in config.measures if coverage[measure] < 2)
    return InternalForecastResult(tuple(points), assumptions, source_periods, coverage, overall, warnings)


def _validate_internal_config(config: InternalForecastConfig) -> None:
    if not isinstance(config.horizon_years, int) or isinstance(config.horizon_years, bool) or not 1 <= config.horizon_years <= 10:
        raise ValueError("horizon_years must be an integer from 1 through 10")
    if not config.measures or any(measure not in SUPPORTED_INTERNAL_MEASURES for measure in config.measures):
        raise ValueError(f"measures must use only {SUPPORTED_INTERNAL_MEASURES}")
    if len(set(config.measures)) != len(config.measures):
        raise ValueError("measures must not contain duplicates")
    if any(name not in SUPPORTED_INTERNAL_MEASURES for name in config.growth_assumptions):
        raise ValueError(f"growth assumptions must use only {SUPPORTED_INTERNAL_MEASURES}")
    if any(name not in {"ebitda", "free_cash_flow"} for name in config.margin_assumptions):
        raise ValueError("margin assumptions support only ebitda and free_cash_flow")
    for name, value in {**config.growth_assumptions, **config.margin_assumptions}.items():
        if not isfinite(float(value)):
            raise ValueError(f"assumption {name} must be finite")
    if any(float(value) <= -1 for value in config.growth_assumptions.values()):
        raise ValueError("growth assumptions must be greater than -100%")
    if any(not 0 <= float(value) <= 1 for value in config.margin_assumptions.values()):
        raise ValueError("margin assumptions must be between 0% and 100%")


def _validate_history(history: Sequence[HistoricalFinancialPeriod], config: InternalForecastConfig) -> None:
    if len({item.period for item in history}) != len(history):
        raise ValueError("historical periods must be unique")
    for item in history:
        for measure, value in item.metrics.items():
            if not isfinite(float(value)):
                raise ValueError(f"historical metric {measure} must be finite")


def _growth_for(measure: str, history: Sequence[HistoricalFinancialPeriod], configured: Mapping[str, float]) -> float | None:
    if measure in configured:
        return float(configured[measure])
    observations = [(item.period, float(item.metrics[measure])) for item in history if measure in item.metrics]
    if len(observations) < 2 or observations[-2][1] == 0:
        return None
    return observations[-1][1] / observations[-2][1] - 1


def _forecast_value(measure: InternalMeasure, latest: Mapping[str, float], growth: float | None, revenue_growth: float | None, margins: Mapping[str, float], year: int) -> float | None:
    if measure == "revenue":
        base = latest.get("revenue")
        return None if base is None or growth is None else base * (1 + growth) ** year
    if measure in {"ebitda", "free_cash_flow"}:
        revenue = latest.get("revenue")
        margin = margins.get(measure)
        if revenue is None or margin is None or revenue_growth is None:
            return None
        return revenue * (1 + revenue_growth) ** year * margin
    base = latest.get(measure)
    return None if base is None or growth is None else base * (1 + growth) ** year


def _confidence(coverage: int, periods: int) -> Literal["high", "moderate", "reduced", "insufficient"]:
    if coverage == 0:
        return "insufficient"
    if coverage >= 3 and periods >= 3:
        return "high"
    if coverage >= 2:
        return "moderate"
    return "reduced"


# Short aliases keep the domain API convenient for callers that do not need
# to distinguish this baseline model from other forecast implementations.
ForecastConfig = InternalForecastConfig
HistoricalMetric = HistoricalFinancialPeriod
InternalForecast = InternalForecastResult
build_internal_forecast = forecast_internal
