"""Point-in-time backtesting contracts; datasets and engines are added later."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BacktestObservation:
    as_of: date
    identifier: str
    score: float | None
