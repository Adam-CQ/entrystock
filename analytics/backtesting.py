"""Small deterministic point-in-time dataset for unbiased backtesting inputs."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from math import isfinite
from typing import Sequence

from analytics.provider_contracts import ClassificationRecord, FinancialStatementRecord, ForecastRecord, PriceRecord
from analytics.recommendations import RecommendationInput, build_recommendation
from analytics.scoring import ScoreConfiguration, calculate_composite_score


@dataclass(frozen=True)
class BacktestObservation:
    as_of: date
    identifier: str
    score: float | None


@dataclass(frozen=True)
class BacktestTrade:
    """One point-in-time signal and its subsequently observable outcome."""

    as_of: date
    exit_date: date | None
    score: float | None
    recommendation: str
    forward_return: float | None
    benchmark_return: float | None
    excess_return: float | None
    component_returns: tuple[tuple[str, float | None], ...]
    status: str = "ok"


@dataclass(frozen=True)
class BacktestMetrics:
    """Small-sample performance summary; values are descriptive, not predictive."""

    observations: int
    evaluable_observations: int
    hit_rate: float | None
    cumulative_return: float | None
    benchmark_cumulative_return: float | None
    excess_cumulative_return: float | None
    maximum_drawdown: float | None
    sharpe_like: float | None


@dataclass(frozen=True)
class BacktestSensitivity:
    parameter: str
    value: object
    metrics: BacktestMetrics


@dataclass(frozen=True)
class BacktestResult:
    trades: tuple[BacktestTrade, ...]
    metrics: BacktestMetrics
    component_metrics: tuple[tuple[str, BacktestMetrics], ...]
    weight_sensitivity: tuple[BacktestSensitivity, ...]
    lookback_sensitivity: tuple[BacktestSensitivity, ...]
    sample_notice: str = (
        "Small fixture-based PoC sample. Results are descriptive and do not establish predictive performance."
    )


@dataclass(frozen=True)
class PeerMembershipRecord:
    entity_id: str
    peer_entity_id: str
    classification: str
    effective_date: date
    available_at: date
    source: str
    retrieved_at: datetime


@dataclass(frozen=True)
class PointInTimeSnapshot:
    as_of: date
    prices: tuple[PriceRecord, ...]
    fundamentals: tuple[FinancialStatementRecord, ...]
    forecasts: tuple[ForecastRecord, ...]
    peer_memberships: tuple[PeerMembershipRecord, ...]
    classifications: tuple[ClassificationRecord, ...]
    benchmark_prices: tuple[PriceRecord, ...] = ()


class PointInTimeDataset:
    """Immutable records queried using both availability and observation dates."""

    def __init__(self, *, prices: Sequence[PriceRecord] = (), fundamentals: Sequence[FinancialStatementRecord] = (), forecasts: Sequence[ForecastRecord] = (), peer_memberships: Sequence[PeerMembershipRecord] = (), classifications: Sequence[ClassificationRecord] = (), benchmark_prices: Sequence[PriceRecord] = ()):
        self.prices = tuple(prices)
        self.fundamentals = tuple(fundamentals)
        self.forecasts = tuple(forecasts)
        self.peer_memberships = tuple(peer_memberships)
        self.classifications = tuple(classifications)
        self.benchmark_prices = tuple(benchmark_prices)

    def snapshot(self, as_of: date) -> PointInTimeSnapshot:
        if not isinstance(as_of, date):
            raise TypeError("as_of must be a date")
        prices = tuple(item for item in self.prices if item.trading_date <= as_of and item.retrieved_at.date() <= as_of)
        fundamentals = tuple(item for item in self.fundamentals if item.effective_date <= as_of and item.retrieved_at.date() <= as_of)
        forecasts = tuple(item for item in self.forecasts if item.as_of <= as_of and item.retrieved_at.date() <= as_of and item.period_end >= item.as_of)
        peers = tuple(item for item in self.peer_memberships if item.effective_date <= as_of and item.available_at <= as_of and item.retrieved_at.date() <= as_of)
        classifications = tuple(item for item in self.classifications if item.effective_date <= as_of and item.retrieved_at.date() <= as_of)
        benchmark_prices = tuple(item for item in self.benchmark_prices if item.trading_date <= as_of and item.retrieved_at.date() <= as_of)
        return PointInTimeSnapshot(as_of, prices, fundamentals, forecasts, peers, classifications, benchmark_prices)

    query = snapshot


def build_fixture_backtesting_dataset() -> PointInTimeDataset:
    """Return a network-free fixture with a revision and intentional gaps."""
    price = lambda day, value, available: PriceRecord("fixture-security", datetime.combine(available, datetime.min.time(), tzinfo=timezone.utc), day, Decimal(value), Decimal(value), Decimal(value), Decimal(value), Decimal(value), Decimal("1000"), "USD", "fully_adjusted", "fixture-backtest", datetime.combine(available, datetime.min.time(), tzinfo=timezone.utc))
    statement = lambda effective, revenue, available: FinancialStatementRecord("fixture-company", "income", date(effective.year - 1, 1, 1), effective, effective, {"revenue": Decimal(revenue)}, "USD", "fixture-backtest", datetime.combine(available, datetime.min.time(), tzinfo=timezone.utc))
    forecasts = (ForecastRecord("fixture-company", "revenue", date(2026, 12, 31), Decimal("1100"), "USD", date(2026, 1, 2), "fixture-backtest", datetime(2026, 1, 2, tzinfo=timezone.utc)), ForecastRecord("fixture-company", "revenue", date(2027, 12, 31), Decimal("1200"), "USD", date(2026, 7, 2), "fixture-backtest", datetime(2026, 7, 2, tzinfo=timezone.utc)))
    peers = (PeerMembershipRecord("fixture-company", "fixture-peer-1", "direct", date(2025, 1, 1), date(2025, 1, 2), "fixture-backtest", datetime(2026, 1, 2, tzinfo=timezone.utc)), PeerMembershipRecord("fixture-company", "fixture-peer-2", "thematic", date(2026, 7, 1), date(2026, 7, 2), "fixture-backtest", datetime(2026, 7, 2, tzinfo=timezone.utc)))
    classifications = (ClassificationRecord("fixture-company", "Energy", "Electrical Equipment", date(2025, 1, 1), "fixture-backtest", datetime(2026, 1, 2, tzinfo=timezone.utc)), ClassificationRecord("fixture-company", "Energy", "Nuclear Technology", date(2026, 7, 1), "fixture-backtest", datetime(2026, 7, 2, tzinfo=timezone.utc)))
    future_price = price(date(2026, 12, 31), "130", date(2026, 12, 31))
    benchmark_price = lambda day, value, available: PriceRecord("fixture-benchmark", datetime.combine(available, datetime.min.time(), tzinfo=timezone.utc), day, Decimal(value), Decimal(value), Decimal(value), Decimal(value), Decimal(value), Decimal("1000"), "USD", "fully_adjusted", "fixture-backtest", datetime.combine(available, datetime.min.time(), tzinfo=timezone.utc))
    return PointInTimeDataset(prices=(price(date(2025, 12, 31), "100", date(2026, 1, 2)), price(date(2026, 6, 30), "110", date(2026, 7, 1)), future_price), benchmark_prices=(benchmark_price(date(2025, 12, 31), "100", date(2026, 1, 2)), benchmark_price(date(2026, 6, 30), "105", date(2026, 7, 1)), benchmark_price(date(2026, 12, 31), "115", date(2026, 12, 31))), fundamentals=(statement(date(2025, 12, 31), "1000", date(2026, 1, 2)), statement(date(2026, 6, 30), "1080", date(2026, 7, 1))), forecasts=forecasts, peer_memberships=peers, classifications=classifications)


def run_recommendation_backtest(
    dataset: PointInTimeDataset,
    *,
    analysis_dates: Sequence[date] | None = None,
    forward_days: int = 180,
    lookback_days: int = 21,
    score_configuration: ScoreConfiguration | None = None,
    benchmark_entity_id: str | None = "fixture-benchmark",
) -> BacktestResult:
    """Run a conservative, point-in-time recommendation backtest.

    A signal is generated from the latest visible price, revenue growth,
    forecast growth, and peer leadership. No record after ``as_of`` is used
    to create the signal; prices after ``as_of`` are used only for outcomes.
    """
    if forward_days < 1 or lookback_days < 1:
        raise ValueError("forward_days and lookback_days must be positive")
    dates = tuple(analysis_dates or _candidate_dates(dataset))
    trades = tuple(_make_trade(dataset, day, forward_days, lookback_days, score_configuration, benchmark_entity_id) for day in dates)
    metrics = _summarize(trades)
    component_metrics = tuple((name, _summarize(tuple(_component_trade(trade, name) for trade in trades))) for name in ("composite_score", "momentum", "peer_leadership"))
    presets = {
        "balanced": None,
        "momentum_focus": {"valuation": 0.10, "forecasts": 0.10, "momentum": 0.40, "quality": 0.15, "catalysts": 0.15, "risk": 0.10},
        "valuation_focus": {"valuation": 0.40, "forecasts": 0.15, "momentum": 0.10, "quality": 0.15, "catalysts": 0.05, "risk": 0.15},
    }
    weight_sensitivity = tuple(BacktestSensitivity("weight_preset", preset, _summarize(tuple(_make_trade(dataset, day, forward_days, lookback_days, ScoreConfiguration(preset=preset, weights=weights), benchmark_entity_id) for day in dates))) for preset, weights in presets.items())
    lookback_sensitivity = tuple(BacktestSensitivity("lookback_days", window, _summarize(tuple(_make_trade(dataset, day, forward_days, window, score_configuration, benchmark_entity_id) for day in dates))) for window in (5, 21, 63))
    return BacktestResult(trades, metrics, component_metrics, weight_sensitivity, lookback_sensitivity)


def _candidate_dates(dataset: PointInTimeDataset) -> tuple[date, ...]:
    return tuple(sorted({item.retrieved_at.date() for item in dataset.prices if item.retrieved_at.date() <= date.today()}))


def _make_trade(dataset: PointInTimeDataset, as_of: date, forward_days: int, lookback_days: int, configuration: ScoreConfiguration | None, benchmark_id: str | None) -> BacktestTrade:
    snapshot = dataset.snapshot(as_of)
    prices = sorted((item for item in snapshot.prices if item.entity_id == "fixture-security"), key=lambda item: item.trading_date)
    current = prices[-1] if prices else None
    prior = next((item for item in reversed(prices[:-1]) if (current and (current.trading_date - item.trading_date).days >= lookback_days)), None)
    momentum = _return(current, prior)
    revenue = sorted(snapshot.fundamentals, key=lambda item: item.effective_date)
    growth = _growth(revenue[-1].values.get("revenue"), revenue[-2].values.get("revenue")) if len(revenue) > 1 else None
    forecast = sorted(snapshot.forecasts, key=lambda item: item.as_of)
    forecast_growth = _growth(forecast[-1].value, forecast[0].value) if len(forecast) > 1 else None
    peer_leadership = 1.0 if len(snapshot.peer_memberships) > 1 else 0.0 if snapshot.peer_memberships else None
    score = calculate_composite_score({"valuation": 0.5, "forecasts": _bounded(forecast_growth), "momentum": _bounded(momentum), "quality": _bounded(growth), "catalysts": peer_leadership, "risk": 0.5}, configuration)
    aggregate = score.aggregate_score
    recommendation_result = build_recommendation(RecommendationInput("ENTRY" if aggregate is not None and aggregate >= 0.6 else "WATCH", score=score, confidence=score.confidence, current_price=float(current.adjusted_close) if current and current.adjusted_close else None, fair_value_low=float(current.adjusted_close) if current and current.adjusted_close else None, fair_value_high=float(current.adjusted_close) * 1.1 if current and current.adjusted_close else None, source="point-in-time backtest", as_of=as_of.isoformat()))
    recommendation = recommendation_result.rating
    exit_date, forward, benchmark = _forward_outcome(dataset, current, as_of, forward_days, benchmark_id)
    components = (("composite_score", forward if aggregate is not None and aggregate >= 0.6 else None), ("momentum", forward if momentum is not None and momentum > 0 else None), ("peer_leadership", forward if peer_leadership == 1.0 else None))
    excess = forward - benchmark if forward is not None and benchmark is not None else None
    status = "ok" if forward is not None else "not_evaluable"
    return BacktestTrade(as_of, exit_date, aggregate, recommendation, forward, benchmark, excess, components, status)


def _forward_outcome(dataset: PointInTimeDataset, current: PriceRecord | None, as_of: date, horizon: int, benchmark_id: str | None) -> tuple[date | None, float | None, float | None]:
    if current is None:
        return None, None, None
    target = current.trading_date + timedelta(days=horizon)
    future = next((item for item in sorted(dataset.prices, key=lambda item: item.trading_date) if item.entity_id == current.entity_id and item.trading_date >= target and item.retrieved_at.date() >= as_of), None)
    benchmark = next((item for item in sorted(dataset.benchmark_prices, key=lambda item: item.trading_date) if item.entity_id == benchmark_id and item.trading_date >= target and item.retrieved_at.date() >= as_of), None) if benchmark_id else None
    benchmark_start = next((item for item in reversed(sorted(dataset.benchmark_prices, key=lambda item: item.trading_date)) if item.entity_id == benchmark_id and item.trading_date <= current.trading_date), None) if benchmark_id else None
    return (future.trading_date if future else None, _return(future, current), _return(benchmark, benchmark_start)) if future else (None, None, None)


def _component_trade(trade: BacktestTrade, name: str) -> BacktestTrade:
    value = dict(trade.component_returns).get(name)
    return BacktestTrade(trade.as_of, trade.exit_date, trade.score, trade.recommendation, value, trade.benchmark_return, value - trade.benchmark_return if value is not None and trade.benchmark_return is not None else None, (), trade.status if value is not None else "not_evaluable")


def _summarize(trades: Sequence[BacktestTrade]) -> BacktestMetrics:
    returns = [item.forward_return for item in trades if item.forward_return is not None]
    benchmarks = [item.benchmark_return for item in trades if item.benchmark_return is not None]
    hits = [item for item in trades if item.forward_return is not None and item.recommendation == "ENTRY"]
    hit_rate = sum(item.forward_return >= 0 for item in hits) / len(hits) if hits else None
    cumulative = _compound(returns)
    benchmark_cumulative = _compound(benchmarks)
    return BacktestMetrics(len(trades), len(returns), hit_rate, cumulative, benchmark_cumulative, cumulative - benchmark_cumulative if cumulative is not None and benchmark_cumulative is not None else None, _drawdown(returns), _sharpe_like(returns))


def _return(end: PriceRecord | None, start: PriceRecord | None) -> float | None:
    if not end or not start:
        return None
    try:
        return float(end.adjusted_close or end.close) / float(start.adjusted_close or start.close) - 1
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _growth(new: object, old: object) -> float | None:
    try:
        return float(new) / float(old) - 1 if float(old) else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _bounded(value: float | None) -> float | None:
    return max(0.0, min(1.0, value + 0.5)) if value is not None and isfinite(value) else None


def _compound(values: Sequence[float]) -> float | None:
    return None if not values else _product(values) - 1


def _product(values: Sequence[float]) -> float:
    result = 1.0
    for value in values:
        result *= 1 + value
    return result


def _drawdown(values: Sequence[float]) -> float | None:
    if not values:
        return None
    level = peak = 1.0
    drawdown = 0.0
    for value in values:
        level *= 1 + value
        peak = max(peak, level)
        drawdown = min(drawdown, level / peak - 1)
    return drawdown


def _sharpe_like(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    average = sum(values) / len(values)
    variance = sum((value - average) ** 2 for value in values) / (len(values) - 1)
    return average / variance**0.5 if variance else None


build_fixture_dataset = build_fixture_backtesting_dataset
