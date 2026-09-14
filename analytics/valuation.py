"""Framework-independent valuation engines.

The calculations use explicit decimal-like units represented as ``float`` for
the small PoC.  Results retain the assumptions and intermediate values needed
to explain or audit a valuation; presentation code should not duplicate these
formulas.
"""

from dataclasses import dataclass, replace
from math import isfinite
from statistics import median
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


@dataclass(frozen=True)
class DCFSensitivityCell:
    discount_rate: float
    terminal_growth: float
    per_share_value: float | None
    status: str
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class DCFSensitivityResult:
    discount_rates: tuple[float, ...]
    terminal_growths: tuple[float, ...]
    cells: tuple[DCFSensitivityCell, ...]
    base_case: tuple[float, float]
    units: str
    errors: tuple[str, ...] = ()

    @property
    def evaluable(self) -> bool:
        return not self.errors and bool(self.cells)

    def cell(self, discount_rate: float, terminal_growth: float) -> DCFSensitivityCell:
        return next(item for item in self.cells if item.discount_rate == discount_rate and item.terminal_growth == terminal_growth)


def calculate_dcf_sensitivity(
    inputs: DCFInputs,
    discount_rates: Sequence[float],
    terminal_growths: Sequence[float],
) -> DCFSensitivityResult:
    """Evaluate the existing DCF engine over a labelled assumption grid."""

    base = validate_dcf_inputs(inputs)
    rows = tuple(float(value) for value in discount_rates)
    columns = tuple(float(value) for value in terminal_growths)
    if base:
        return DCFSensitivityResult(rows, columns, (), (inputs.discount_rate, inputs.terminal_growth), "currency/share", ("insufficient DCF inputs: " + "; ".join(base),))
    if not rows or not columns:
        return DCFSensitivityResult(rows, columns, (), (inputs.discount_rate, inputs.terminal_growth), "currency/share", ("discount_rates and terminal_growths must not be empty",))
    cells: list[DCFSensitivityCell] = []
    for discount_rate in rows:
        for terminal_growth in columns:
            candidate = replace(inputs, discount_rate=discount_rate, terminal_growth=terminal_growth)
            result = calculate_dcf(candidate)
            if result.valid:
                cells.append(DCFSensitivityCell(discount_rate, terminal_growth, result.per_share_value, "ok"))
            else:
                cells.append(DCFSensitivityCell(discount_rate, terminal_growth, None, "not_evaluable", result.errors))
    return DCFSensitivityResult(rows, columns, tuple(cells), (inputs.discount_rate, inputs.terminal_growth), "currency/share")


DCFScenarioGrid = DCFSensitivityResult
build_dcf_sensitivity = calculate_dcf_sensitivity


@dataclass(frozen=True)
class RelativeValuationObservation:
    identifier: str
    enterprise_value: float | None
    market_capitalization: float | None
    ebitda: float | None
    earnings: float | None
    revenue: float | None
    free_cash_flow: float | None
    currency: str
    as_of: str
    source: str = "unknown"


@dataclass(frozen=True)
class RelativeMultipleResult:
    multiple: str
    status: str
    selected_value: float | None
    peer_median: float | None
    peer_values: tuple[float, ...]
    included_peers: tuple[str, ...]
    excluded_peers: tuple[tuple[str, str], ...]
    outlier_peers: tuple[str, ...]
    source_dates: tuple[str, ...]
    coverage: int
    explanation: str
    units: str


@dataclass(frozen=True)
class RelativeValuationResult:
    selected_company: str
    peer_universe: tuple[str, ...]
    multiples: tuple[RelativeMultipleResult, ...]
    minimum_peers: int
    as_of: str


_RELATIVE_DEFINITIONS = {
    "ev_ebitda": ("enterprise_value", "ebitda", "EV/EBITDA", "multiple"),
    "pe": ("market_capitalization", "earnings", "P/E", "multiple"),
    "ev_sales": ("enterprise_value", "revenue", "EV/Sales", "multiple"),
    "fcf_yield": ("free_cash_flow", "market_capitalization", "FCF yield", "yield"),
}


def calculate_relative_valuation(
    selected: RelativeValuationObservation,
    peers: Sequence[RelativeValuationObservation],
    *,
    minimum_peers: int = 2,
) -> RelativeValuationResult:
    """Compare a selected company with its confirmed, point-in-time peers."""

    if minimum_peers < 1:
        raise ValueError("minimum_peers must be positive")
    unique_peers: dict[str, RelativeValuationObservation] = {}
    for peer in peers:
        if peer.identifier != selected.identifier:
            unique_peers.setdefault(peer.identifier, peer)
    universe = tuple(unique_peers)
    results = tuple(_relative_multiple(name, selected, tuple(unique_peers.values()), minimum_peers) for name in _RELATIVE_DEFINITIONS)
    return RelativeValuationResult(selected.identifier, universe, results, minimum_peers, selected.as_of)


def _relative_multiple(name: str, selected: RelativeValuationObservation, peers: Sequence[RelativeValuationObservation], minimum_peers: int) -> RelativeMultipleResult:
    numerator_name, denominator_name, label, units = _RELATIVE_DEFINITIONS[name]
    selected_numerator = getattr(selected, numerator_name)
    selected_denominator = getattr(selected, denominator_name)
    source_dates = tuple(dict.fromkeys([selected.as_of, *(peer.as_of for peer in peers)]))
    if selected.currency == "":
        return RelativeMultipleResult(name, "not_evaluable", None, None, (), (), tuple((peer.identifier, "missing currency") for peer in peers), (), source_dates, 0, "selected currency is missing", units)
    if not _valid_ratio_inputs(selected_numerator, selected_denominator):
        reason = "suppressed: selected company has a non-positive or missing denominator"
        return RelativeMultipleResult(name, "suppressed", None, None, (), (), tuple((peer.identifier, reason) for peer in peers), (), source_dates, 0, reason, units)
    selected_value = float(selected_numerator) / float(selected_denominator)
    values: list[tuple[str, float, str]] = []
    excluded: list[tuple[str, str]] = []
    for peer in peers:
        if peer.currency != selected.currency:
            excluded.append((peer.identifier, "incompatible currency"))
        elif not _valid_ratio_inputs(getattr(peer, numerator_name), getattr(peer, denominator_name)):
            excluded.append((peer.identifier, "missing or non-positive denominator"))
        else:
            values.append((peer.identifier, float(getattr(peer, numerator_name)) / float(getattr(peer, denominator_name)), peer.as_of))
    if len(values) < minimum_peers:
        return RelativeMultipleResult(name, "not_evaluable", selected_value, None, tuple(value for _, value, _ in values), tuple(identifier for identifier, _, _ in values), tuple(excluded), (), source_dates, len(values), f"insufficient peer data: {len(values)} valid peer(s), minimum is {minimum_peers}", units)
    outliers = _iqr_outliers(values)
    usable = [item for item in values if item[0] not in outliers]
    peer_median = median(item[1] for item in usable)
    return RelativeMultipleResult(name, "selected", selected_value, peer_median, tuple(value for _, value, _ in values), tuple(identifier for identifier, _, _ in values), tuple(excluded), tuple(sorted(outliers)), source_dates, len(values), f"selected because the required {denominator_name} is positive and available", units)


def _valid_ratio_inputs(numerator: object, denominator: object) -> bool:
    return _finite(numerator) and _finite(denominator) and float(numerator) >= 0 and float(denominator) > 0


def _iqr_outliers(values: Sequence[tuple[str, float, str]]) -> set[str]:
    if len(values) < 4:
        return set()
    ordered = sorted(item[1] for item in values)
    lower_half = ordered[: len(ordered) // 2]
    upper_half = ordered[(len(ordered) + 1) // 2 :]
    q1, q3 = median(lower_half), median(upper_half)
    fence = 1.5 * (q3 - q1)
    baseline = median(ordered)
    return {
        identifier
        for identifier, value, _ in values
        if value < q1 - fence or value > q3 + fence or value > baseline * 3 or value < baseline / 3
    }


RelativeValuation = RelativeValuationResult
build_relative_valuation = calculate_relative_valuation
