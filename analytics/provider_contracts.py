"""Provider-neutral contracts and normalized records for financial data."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Mapping, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class CompanyMetadata:
    """Company identity keyed by a provider-neutral company identifier."""

    company_id: str
    legal_name: str
    common_name: str
    country_code: str
    security_identifiers: tuple[str, ...]
    source: str
    retrieved_at: datetime
    business_model: str | None = None
    industry: str | None = None
    size: Decimal | None = None
    growth: Decimal | None = None
    profitability: Decimal | None = None
    capital_intensity: Decimal | None = None
    themes: tuple[str, ...] = ()


@dataclass(frozen=True)
class FinancialStatementRecord:
    """A point-in-time statement snapshot; values use the declared units."""

    entity_id: str
    statement_type: str
    period_start: date
    period_end: date
    effective_date: date
    values: Mapping[str, Decimal]
    units: str
    source: str
    retrieved_at: datetime


@dataclass(frozen=True)
class ForecastRecord:
    """A forecast for a period, requested as known at ``as_of``."""

    entity_id: str
    metric: str
    period_end: date
    value: Decimal
    units: str
    as_of: date
    source: str
    retrieved_at: datetime


@dataclass(frozen=True)
class PriceRecord:
    """A timestamped OHLCV observation with explicit adjustment semantics."""

    entity_id: str
    observed_at: datetime
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal | None
    volume: Decimal
    currency_code: str
    adjustment_status: str
    source: str
    retrieved_at: datetime


@dataclass(frozen=True)
class ClassificationRecord:
    """Classification effective on ``effective_date``; missing data is no record."""

    entity_id: str
    sector: str | None
    industry: str | None
    effective_date: date
    source: str
    retrieved_at: datetime


@dataclass(frozen=True)
class CorporateActionRecord:
    """Corporate action keyed by its source identifier and effective ex-date."""

    entity_id: str
    action_type: str
    ex_date: date
    ratio: Decimal | None
    cash_amount: Decimal | None
    currency_code: str
    source_action_id: str
    source: str
    retrieved_at: datetime


@runtime_checkable
class FinancialDataProvider(Protocol):
    """Provider contract used by analytics; implementations must be network-agnostic to callers."""

    def get_company_metadata(self, company_id: str) -> CompanyMetadata | None:
        """Return identity and provenance, or ``None`` when the identifier is unknown."""

    def get_financial_statements(
        self, entity_id: str, period_start: date | None = None, period_end: date | None = None
    ) -> Sequence[FinancialStatementRecord]:
        """Return statements whose periods overlap the inclusive date range; empty means no data."""

    def get_forecasts(self, entity_id: str, as_of: date) -> Sequence[ForecastRecord]:
        """Return forecasts available as of the inclusive point-in-time date; empty means no data."""

    def get_prices(self, entity_id: str, start: datetime, end: datetime) -> Sequence[PriceRecord]:
        """Return observations in the inclusive timestamp range, ordered oldest first; empty means no data."""

    def get_classifications(self, entity_id: str, as_of: date) -> ClassificationRecord | None:
        """Return the classification effective at the requested date, or ``None`` if unavailable."""

    def get_corporate_actions(
        self, entity_id: str, start: date | None = None, end: date | None = None
    ) -> Sequence[CorporateActionRecord]:
        """Return actions in the inclusive ex-date range, ordered oldest first; empty means no data."""
