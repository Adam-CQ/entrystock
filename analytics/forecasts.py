"""Forecast source and period value objects."""

from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from typing import Literal

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
