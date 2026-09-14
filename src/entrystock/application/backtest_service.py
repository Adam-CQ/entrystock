"""Application boundary for running recommendation backtests."""

from collections.abc import Sequence
from datetime import date

from analytics.backtesting import BacktestResult, PointInTimeDataset, run_recommendation_backtest
from analytics.scoring import ScoreConfiguration


def run_backtest(
    dataset: PointInTimeDataset,
    *,
    analysis_dates: Sequence[date] | None = None,
    forward_days: int = 180,
    lookback_days: int = 21,
    score_configuration: ScoreConfiguration | None = None,
    benchmark_entity_id: str | None = "fixture-benchmark",
) -> BacktestResult:
    """Coordinate a backtest without putting formulas in a job or view."""

    return run_recommendation_backtest(
        dataset,
        analysis_dates=analysis_dates,
        forward_days=forward_days,
        lookback_days=lookback_days,
        score_configuration=score_configuration,
        benchmark_entity_id=benchmark_entity_id,
    )
