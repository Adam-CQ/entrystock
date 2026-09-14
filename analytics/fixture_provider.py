"""Deterministic, credential-free implementation of the provider contract."""

from datetime import date, datetime, timezone
from decimal import Decimal

from analytics.provider_contracts import (
    ClassificationRecord,
    CompanyMetadata,
    CorporateActionRecord,
    FinancialDataProvider,
    FinancialStatementRecord,
    ForecastRecord,
    PriceRecord,
)


class FixtureProvider(FinancialDataProvider):
    """Small in-memory dataset intended for contract and analytical unit tests."""

    _retrieved_at = datetime(2026, 1, 2, 12, tzinfo=timezone.utc)
    _company = CompanyMetadata(
        company_id="fixture-company",
        legal_name="Fixture Energy Corporation",
        common_name="Fixture Energy",
        country_code="US",
        security_identifiers=("fixture-security",),
        source="fixture",
        retrieved_at=_retrieved_at,
    )
    _statements = (
        FinancialStatementRecord(
            entity_id="fixture-company",
            statement_type="income",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            effective_date=date(2026, 1, 2),
            values={"revenue": Decimal("1000"), "net_income": Decimal("100")},
            units="USD",
            source="fixture",
            retrieved_at=_retrieved_at,
        ),
    )
    _forecasts = (
        ForecastRecord(
            entity_id="fixture-company",
            metric="revenue",
            period_end=date(2026, 12, 31),
            value=Decimal("1100"),
            units="USD",
            as_of=date(2026, 1, 2),
            source="fixture",
            retrieved_at=_retrieved_at,
        ),
    )
    _prices = (
        PriceRecord(
            entity_id="fixture-security",
            observed_at=datetime(2026, 1, 2, 20, tzinfo=timezone.utc),
            trading_date=date(2026, 1, 2),
            open=Decimal("99"),
            high=Decimal("102"),
            low=Decimal("98"),
            close=Decimal("100"),
            adjusted_close=Decimal("100"),
            volume=Decimal("10000"),
            currency_code="USD",
            adjustment_status="fully_adjusted",
            source="fixture",
            retrieved_at=_retrieved_at,
        ),
    )
    _classifications = ClassificationRecord(
        entity_id="fixture-company",
        sector="Energy",
        industry="Electrical Equipment",
        effective_date=date(2025, 1, 1),
        source="fixture",
        retrieved_at=_retrieved_at,
    )
    _actions = (
        CorporateActionRecord(
            entity_id="fixture-security",
            action_type="stock_split",
            ex_date=date(2025, 6, 1),
            ratio=Decimal("2"),
            cash_amount=None,
            currency_code="USD",
            source_action_id="fixture-split-2025-06-01",
            source="fixture",
            retrieved_at=_retrieved_at,
        ),
    )

    def get_company_metadata(self, company_id: str) -> CompanyMetadata | None:
        return self._company if company_id == self._company.company_id else None

    def get_financial_statements(
        self, entity_id: str, period_start: date | None = None, period_end: date | None = None
    ) -> tuple[FinancialStatementRecord, ...]:
        return tuple(
            record
            for record in self._statements
            if record.entity_id == entity_id
            and (period_start is None or record.period_end >= period_start)
            and (period_end is None or record.period_start <= period_end)
        )

    def get_forecasts(self, entity_id: str, as_of: date) -> tuple[ForecastRecord, ...]:
        return tuple(record for record in self._forecasts if record.entity_id == entity_id and record.as_of <= as_of)

    def get_prices(self, entity_id: str, start: datetime, end: datetime) -> tuple[PriceRecord, ...]:
        return tuple(
            sorted(
                (record for record in self._prices if record.entity_id == entity_id and start <= record.observed_at <= end),
                key=lambda record: record.observed_at,
            )
        )

    def get_classifications(self, entity_id: str, as_of: date) -> ClassificationRecord | None:
        if self._classifications.entity_id == entity_id and self._classifications.effective_date <= as_of:
            return self._classifications
        return None

    def get_corporate_actions(
        self, entity_id: str, start: date | None = None, end: date | None = None
    ) -> tuple[CorporateActionRecord, ...]:
        return tuple(
            record
            for record in self._actions
            if record.entity_id == entity_id
            and (start is None or record.ex_date >= start)
            and (end is None or record.ex_date <= end)
        )
