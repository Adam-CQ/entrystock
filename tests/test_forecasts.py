from datetime import date, datetime, timezone

from analytics.forecasts import ForecastValue, compare_forecasts


def _values():
    retrieved = datetime(2026, 1, 2, tzinfo=timezone.utc)
    return [
        ForecastValue("management", "revenue", "FY2026", 1100, "USD", retrieved, date(2026, 1, 2)),
        ForecastValue("consensus", "revenue", "FY2026", 1200, "USD", retrieved, date(2026, 1, 2)),
        ForecastValue("internal", "revenue", "FY2026", 1300, "USD", retrieved, date(2026, 1, 2)),
    ]


def test_forecast_comparison_keeps_sources_separate_and_calculates_divergence():
    result = compare_forecasts(_values())[0]

    assert result.comparable is True
    assert result.source_values["management"].value == 1100
    assert result.absolute_divergence == 200
    assert result.relative_divergence == 200 / 1100


def test_forecast_comparison_reports_missing_mismatched_and_stale_data():
    values = _values()[:2] + [ForecastValue("internal", "revenue", "FY2026", 1300, "EUR", None, date(2024, 1, 1))]
    result = compare_forecasts(values, as_of=date(2026, 1, 2), max_age_days=365)[0]

    assert result.comparable is False
    assert result.missing_sources == ()
    assert result.stale_sources == ("internal",)
    assert result.reason == "incompatible units"

    missing = compare_forecasts(_values()[:1])[0]
    assert missing.missing_sources == ("consensus", "internal")
    assert missing.absolute_divergence is None


def test_forecast_comparison_does_not_mix_periods_or_measures():
    result = compare_forecasts(_values() + [ForecastValue("management", "eps", "FY2026", 1.1, "USD/share")])

    assert [(row.measure, row.period) for row in result] == [("eps", "FY2026"), ("revenue", "FY2026")]
