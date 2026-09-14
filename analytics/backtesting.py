"""Small deterministic point-in-time dataset for unbiased backtesting inputs."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Sequence

from analytics.provider_contracts import ClassificationRecord, FinancialStatementRecord, ForecastRecord, PriceRecord


@dataclass(frozen=True)
class BacktestObservation:
    as_of: date
    identifier: str
    score: float | None


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


class PointInTimeDataset:
    """Immutable records queried using both availability and observation dates."""

    def __init__(self, *, prices: Sequence[PriceRecord] = (), fundamentals: Sequence[FinancialStatementRecord] = (), forecasts: Sequence[ForecastRecord] = (), peer_memberships: Sequence[PeerMembershipRecord] = (), classifications: Sequence[ClassificationRecord] = ()):
        self.prices = tuple(prices)
        self.fundamentals = tuple(fundamentals)
        self.forecasts = tuple(forecasts)
        self.peer_memberships = tuple(peer_memberships)
        self.classifications = tuple(classifications)

    def snapshot(self, as_of: date) -> PointInTimeSnapshot:
        if not isinstance(as_of, date):
            raise TypeError("as_of must be a date")
        prices = tuple(item for item in self.prices if item.trading_date <= as_of and item.retrieved_at.date() <= as_of)
        fundamentals = tuple(item for item in self.fundamentals if item.effective_date <= as_of and item.retrieved_at.date() <= as_of)
        forecasts = tuple(item for item in self.forecasts if item.as_of <= as_of and item.retrieved_at.date() <= as_of and item.period_end >= item.as_of)
        peers = tuple(item for item in self.peer_memberships if item.effective_date <= as_of and item.available_at <= as_of and item.retrieved_at.date() <= as_of)
        classifications = tuple(item for item in self.classifications if item.effective_date <= as_of and item.retrieved_at.date() <= as_of)
        return PointInTimeSnapshot(as_of, prices, fundamentals, forecasts, peers, classifications)

    query = snapshot


def build_fixture_backtesting_dataset() -> PointInTimeDataset:
    """Return a network-free fixture with a revision and intentional gaps."""
    price = lambda day, value, available: PriceRecord("fixture-security", datetime.combine(available, datetime.min.time(), tzinfo=timezone.utc), day, Decimal(value), Decimal(value), Decimal(value), Decimal(value), Decimal(value), Decimal("1000"), "USD", "fully_adjusted", "fixture-backtest", datetime.combine(available, datetime.min.time(), tzinfo=timezone.utc))
    statement = lambda effective, revenue, available: FinancialStatementRecord("fixture-company", "income", date(effective.year - 1, 1, 1), effective, effective, {"revenue": Decimal(revenue)}, "USD", "fixture-backtest", datetime.combine(available, datetime.min.time(), tzinfo=timezone.utc))
    forecasts = (ForecastRecord("fixture-company", "revenue", date(2026, 12, 31), Decimal("1100"), "USD", date(2026, 1, 2), "fixture-backtest", datetime(2026, 1, 2, tzinfo=timezone.utc)), ForecastRecord("fixture-company", "revenue", date(2027, 12, 31), Decimal("1200"), "USD", date(2026, 7, 2), "fixture-backtest", datetime(2026, 7, 2, tzinfo=timezone.utc)))
    peers = (PeerMembershipRecord("fixture-company", "fixture-peer-1", "direct", date(2025, 1, 1), date(2025, 1, 2), "fixture-backtest", datetime(2026, 1, 2, tzinfo=timezone.utc)), PeerMembershipRecord("fixture-company", "fixture-peer-2", "thematic", date(2026, 7, 1), date(2026, 7, 2), "fixture-backtest", datetime(2026, 7, 2, tzinfo=timezone.utc)))
    classifications = (ClassificationRecord("fixture-company", "Energy", "Electrical Equipment", date(2025, 1, 1), "fixture-backtest", datetime(2026, 1, 2, tzinfo=timezone.utc)), ClassificationRecord("fixture-company", "Energy", "Nuclear Technology", date(2026, 7, 1), "fixture-backtest", datetime(2026, 7, 2, tzinfo=timezone.utc)))
    return PointInTimeDataset(prices=(price(date(2025, 12, 31), "100", date(2026, 1, 2)), price(date(2026, 6, 30), "110", date(2026, 7, 1))), fundamentals=(statement(date(2025, 12, 31), "1000", date(2026, 1, 2)), statement(date(2026, 6, 30), "1080", date(2026, 7, 1))), forecasts=forecasts, peer_memberships=peers, classifications=classifications)


build_fixture_dataset = build_fixture_backtesting_dataset
