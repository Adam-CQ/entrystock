"""Framework-independent valuation engines.

The calculations use explicit decimal-like units represented as ``float`` for
the small PoC.  Results retain the assumptions and intermediate values needed
to explain or audit a valuation; presentation code should not duplicate these
formulas.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Sequence


@dataclass(frozen=True)
class ValuationResult:
    method: str
    value: float | None
    currency: str | None = None


@dataclass(frozen=True)
class DCFForecastPeriod:
    period: int
    revenue: float | None
    operating_profit_after_tax: float | None
    reinvestment: float | None
    free_cash_flow: float
    discount_factor: float
    present_value: float


@dataclass(frozen=True)
class DCFInputs:
    """DCF assumptions using decimal fractions for rates.

    ``starting_revenue`` drives an operating-profit/reinvestment model.  A
    caller may instead provide ``starting_free_cash_flow`` when revenue and
    margin data are unavailable.  ``revenue_growth`` can be one rate applied
    to every period or one rate per forecast period.
    """

    forecast_years: int
    revenue_growth: float | Sequence[float]
    operating_margin: float
    tax_rate: float
    reinvestment_rate: float
    discount_rate: float
    terminal_growth: float
    shares_outstanding: float
    starting_revenue: float | None = None
    starting_free_cash_flow: float | None = None
    currency: str = "USD"
    source_period: str = "latest"


@dataclass(frozen=True)
class DCFResult:
    per_share_value: float | None
    enterprise_value: float | None
    forecast: tuple[DCFForecastPeriod, ...]
    terminal_value: float | None
    terminal_present_value: float | None
    assumptions: DCFInputs
    errors: tuple[str, ...] = ()
    currency: str = "USD"

    @property
    def valid(self) -> bool:
        return not self.errors and self.per_share_value is not None


def validate_dcf_inputs(inputs: DCFInputs) -> tuple[str, ...]:
    """Return actionable validation messages without attempting valuation."""

    errors: list[str] = []
    if not isinstance(inputs.forecast_years, int) or isinstance(inputs.forecast_years, bool) or not 1 <= inputs.forecast_years <= 20:
        errors.append("forecast_years must be an integer from 1 through 20")
    if inputs.starting_revenue is None and inputs.starting_free_cash_flow is None:
        errors.append("starting_revenue or starting_free_cash_flow is required")
    for name in ("operating_margin", "tax_rate", "reinvestment_rate", "discount_rate", "terminal_growth", "shares_outstanding"):
        value = getattr(inputs, name)
        if not _finite(value):
            errors.append(f"{name} must be finite")
    if inputs.starting_revenue is not None and (not _finite(inputs.starting_revenue) or inputs.starting_revenue <= 0):
        errors.append("starting_revenue must be greater than zero")
    if inputs.starting_free_cash_flow is not None and not _finite(inputs.starting_free_cash_flow):
        errors.append("starting_free_cash_flow must be finite")
    for name in ("tax_rate", "reinvestment_rate"):
        value = getattr(inputs, name)
        if _finite(value) and not 0 <= value <= 1:
            errors.append(f"{name} must be between 0 and 1")
    if _finite(inputs.operating_margin) and not -1 <= inputs.operating_margin <= 1:
        errors.append("operating_margin must be between -1 and 1")
    if _finite(inputs.discount_rate) and not 0 < inputs.discount_rate < 1:
        errors.append("discount_rate must be greater than 0 and less than 1")
    if _finite(inputs.terminal_growth) and not -1 < inputs.terminal_growth < 1:
        errors.append("terminal_growth must be greater than -1 and less than 1")
    if _finite(inputs.discount_rate) and _finite(inputs.terminal_growth) and inputs.terminal_growth >= inputs.discount_rate:
        errors.append("terminal_growth must be below discount_rate")
    if _finite(inputs.shares_outstanding) and inputs.shares_outstanding <= 0:
        errors.append("shares_outstanding must be greater than zero")
    growth = inputs.revenue_growth if isinstance(inputs.revenue_growth, Sequence) and not isinstance(inputs.revenue_growth, (str, bytes)) else (inputs.revenue_growth,)
    if len(growth) not in {1, inputs.forecast_years}:
        errors.append("revenue_growth must be one rate or contain one rate per forecast year")
    for value in growth:
        if not _finite(value):
            errors.append("revenue_growth values must be finite")
        elif value <= -1:
            errors.append("revenue_growth values must be greater than -1")
    return tuple(dict.fromkeys(errors))


def calculate_dcf(inputs: DCFInputs) -> DCFResult:
    """Calculate a deterministic Gordon-growth DCF with inspectable steps."""

    errors = validate_dcf_inputs(inputs)
    if errors:
        return DCFResult(None, None, (), None, None, inputs, errors, inputs.currency)
    growth = inputs.revenue_growth if isinstance(inputs.revenue_growth, Sequence) and not isinstance(inputs.revenue_growth, (str, bytes)) else (inputs.revenue_growth,)
    rates = tuple(float(growth[0]) for _ in range(inputs.forecast_years)) if len(growth) == 1 else tuple(float(value) for value in growth)
    forecast: list[DCFForecastPeriod] = []
    previous_revenue = inputs.starting_revenue
    previous_fcf = inputs.starting_free_cash_flow
    for period, rate in enumerate(rates, start=1):
        revenue = None if previous_revenue is None else previous_revenue * (1 + rate)
        if revenue is not None:
            after_tax_profit = revenue * inputs.operating_margin * (1 - inputs.tax_rate)
            reinvestment = after_tax_profit * inputs.reinvestment_rate
            free_cash_flow = after_tax_profit - reinvestment
            previous_revenue = revenue
        else:
            after_tax_profit = None
            reinvestment = None
            free_cash_flow = previous_fcf * (1 + rate)
            previous_fcf = free_cash_flow
        discount_factor = 1 / (1 + inputs.discount_rate) ** period
        forecast.append(DCFForecastPeriod(period, revenue, after_tax_profit, reinvestment, free_cash_flow, discount_factor, free_cash_flow * discount_factor))
    terminal_fcf = forecast[-1].free_cash_flow * (1 + inputs.terminal_growth)
    terminal_value = terminal_fcf / (inputs.discount_rate - inputs.terminal_growth)
    terminal_present_value = terminal_value * forecast[-1].discount_factor
    enterprise_value = sum(item.present_value for item in forecast) + terminal_present_value
    return DCFResult(enterprise_value / inputs.shares_outstanding, enterprise_value, tuple(forecast), terminal_value, terminal_present_value, inputs, (), inputs.currency)


def _finite(value: object) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


# Public aliases for callers using the domain terminology.
DCFConfig = DCFInputs
DCFValuation = DCFResult
build_dcf = calculate_dcf
