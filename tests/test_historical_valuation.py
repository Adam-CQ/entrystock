from dataclasses import replace

from analytics.valuation import RelativeValuationObservation, calculate_historical_valuation


def _observation(identifier, period, *, ev=1_000, market_cap=900, ebitda=100, earnings=50, revenue=500, fcf=40, currency="USD"):
    return RelativeValuationObservation(identifier, ev, market_cap, ebitda, earnings, revenue, fcf, currency, period, "fixture")


def test_historical_valuation_reports_median_percentile_dates_and_bands():
    current = _observation("selected", "2026-06-30", ev=1_200)
    history = [_observation("selected", "2023-06-30", ev=800), _observation("selected", "2024-06-30", ev=900), _observation("selected", "2025-06-30", ev=1_000)]
    result = calculate_historical_valuation(current, history)
    ev = next(item for item in result.multiples if item.multiple == "ev_ebitda")

    assert ev.status == "selected"
    assert ev.current_value == 12
    assert ev.historical_median == 9
    assert ev.current_percentile == 1.0
    assert ev.valid_periods == ("2023-06-30", "2024-06-30", "2025-06-30")
    assert ev.band == (8, 10)
    assert ev.source_coverage == 3


def test_historical_valuation_excludes_invalid_periods_and_withholds_bands_when_history_is_short():
    current = _observation("selected", "2026-06-30")
    history = [
        _observation("selected", "2025-06-30"),
        _observation("selected", "2024-06-30", ebitda=0),
        _observation("other", "2023-06-30"),
        _observation("selected", "2022-06-30", currency="EUR"),
    ]
    result = calculate_historical_valuation(current, history, minimum_periods_for_band=3)
    ev = next(item for item in result.multiples if item.multiple == "ev_ebitda")

    assert ev.source_coverage == 1
    assert ev.band is None
    assert ("2024-06-30", "missing or non-positive denominator") in ev.excluded_periods
    assert ("2023-06-30", "different company") in ev.excluded_periods
    assert ("2022-06-30", "incompatible currency") in ev.excluded_periods


def test_historical_valuation_marks_missing_current_multiple():
    current = _observation("selected", "2026-06-30", revenue=None)
    result = calculate_historical_valuation(current, [_observation("selected", "2025-06-30")])
    sales = next(item for item in result.multiples if item.multiple == "ev_sales")

    assert sales.status == "not_evaluable"
    assert sales.current_value is None
    assert sales.historical_median is not None
