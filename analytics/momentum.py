"""Momentum signal contracts; indicator calculations are added later."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MomentumSignal:
    identifier: str
    value: float | None
    lookback_days: int
