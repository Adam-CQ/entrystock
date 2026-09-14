"""Forecast source and period value objects."""

from dataclasses import dataclass
from typing import Literal

ForecastSource = Literal["management", "consensus", "internal"]


@dataclass(frozen=True)
class ForecastValue:
    source: ForecastSource
    measure: str
    period: str
    value: float | None
