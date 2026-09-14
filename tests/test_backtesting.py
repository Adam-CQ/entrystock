from datetime import date

import pytest

from analytics.backtesting import build_fixture_backtesting_dataset, run_recommendation_backtest


def test_minimum_backtest_reports_outcomes_and_benchmark_comparison():
    result = run_recommendation_backtest(
        build_fixture_backtesting_dataset(),
        analysis_dates=(date(2026, 1, 2), date(2026, 7, 1)),
        forward_days=180,
    )

    assert len(result.trades) == 2
    assert result.trades[0].forward_return == pytest.approx(0.1)
    assert result.trades[1].forward_return == pytest.approx(0.18181818181818188)
    assert result.trades[1].benchmark_return == pytest.approx(0.09523809523809512)
    assert result.metrics.evaluable_observations == 2
    assert result.metrics.excess_cumulative_return is not None
    assert {name for name, _ in result.component_metrics} == {"composite_score", "momentum", "peer_leadership"}


def test_backtest_exposes_small_sample_sensitivity_and_rejects_invalid_horizon():
    dataset = build_fixture_backtesting_dataset()
    result = run_recommendation_backtest(dataset, analysis_dates=(date(2026, 7, 1),))

    assert len(result.weight_sensitivity) == 3
    assert len(result.lookback_sensitivity) == 3
    assert "small" in result.sample_notice.lower()

    try:
        run_recommendation_backtest(dataset, forward_days=0)
    except ValueError as error:
        assert "positive" in str(error)
    else:
        raise AssertionError("zero forward horizon must be rejected")
