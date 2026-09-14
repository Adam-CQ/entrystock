"""Composite-score contracts; scoring rules are added later."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreContribution:
    component: str
    weight: float
    value: float | None
