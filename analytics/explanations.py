"""Structured explanation contracts for analytical outputs."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Explanation:
    summary: str
    drivers: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
