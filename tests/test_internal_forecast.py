import math

import pytest

from analytics.forecasts import HistoricalFinancialPeriod, InternalForecastConfig, forecast_internal


def _history():
    return [
        HistoricalFinancialPeriod("FY2023", {"revenue": 1000, "ebitda": 100, "eps": 1.0, "free_cash_flow": 70}),
        HistoricalFinancialPeriod("FY2024", {"revenue": 1100, "ebitda": 120, "eps": 1.1, "free_cash_flow": 80}),
        HistoricalFinancialPeriod("FY2025", {"revenue": 1210, "ebitda": 145, "eps": 1.2, "free_cash_flow": 90}),
    ]


def test_internal_forecast_is_deterministic_and_inspectable():
    config = InternalForecastConfig(horizon_years=2, growth_assumptions={"revenue": 0.10, "eps": 0.05}, margin_assumptions={"ebitda": 0.15, "free_cash_flow": 0.08})
    first = forecast_internal(_history(), config)
    second = forecast_internal(_history(), config)

    assert first == second
    assert first.forecasts[0].value == 1331
    assert first.forecasts[1].value == 1210 * 1.1 * 0.15
    assert first.confidence == "high"
    assert first.source_periods == ("FY2023", "FY2024", "FY2025")
    assert first.assumptions["revenue"] == 0.10


def test_internal_forecast_accepts_boundary_assumptions():
    result = forecast_internal(_history(), InternalForecastConfig(horizon_years=1, measures=("revenue",), growth_assumptions={"revenue": 0}))

    assert result.forecasts[0].value == 1210


@pytest.mark.parametrize("config", [
    InternalForecastConfig(horizon_years=0),
    InternalForecastConfig(horizon_years=11),
    InternalForecastConfig(growth_assumptions={"revenue": math.nan}),
    InternalForecastConfig(margin_assumptions={"ebitda": 1.1}),
    InternalForecastConfig(growth_assumptions={"revenue": -1}),
])
def test_internal_forecast_rejects_invalid_configuration(config):
    with pytest.raises(ValueError):
        forecast_internal(_history(), config)


def test_incomplete_history_reduces_confidence_without_inventing_values():
    history = [HistoricalFinancialPeriod("FY2025", {"revenue": 1000})]
    result = forecast_internal(history, InternalForecastConfig(horizon_years=2, measures=("revenue", "eps")))

    assert result.confidence in {"reduced", "insufficient"}
    assert [point.value for point in result.forecasts if point.measure == "revenue"] == [None, None]
    assert all(point.confidence == "insufficient" for point in result.forecasts)
    assert any("revenue: incomplete historical coverage" in warning for warning in result.warnings)
