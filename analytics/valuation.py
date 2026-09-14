"""Valuation result contracts; calculation engines are added later."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValuationResult:
    method: str
    value: float | None
    currency: str | None = None
