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

_RETRIEVED_AT = datetime(2026, 1, 2, 12, tzinfo=timezone.utc)
_COMPANIES = (
    CompanyMetadata("fixture-company", "Fixture Energy Corporation", "Fixture Energy", "US", ("fixture-security",), "fixture", _RETRIEVED_AT, "equipment", "Electrical Equipment", Decimal("1000"), Decimal("0.10"), Decimal("0.12"), Decimal("0.35"), ("nuclear", "energy")),
    CompanyMetadata("fixture-peer-1", "Fixture Grid Systems", "Fixture Grid", "US", ("fixture-security-1",), "fixture", _RETRIEVED_AT, "equipment", "Electrical Equipment", Decimal("900"), Decimal("0.08"), Decimal("0.11"), Decimal("0.32"), ("energy",)),
    CompanyMetadata("fixture-peer-2", "Fixture Reactor Works", "Fixture Reactor", "US", ("fixture-security-2",), "fixture", _RETRIEVED_AT, "equipment", "Electrical Equipment", Decimal("700"), Decimal("0.15"), Decimal("0.06"), Decimal("0.48"), ("nuclear", "energy")),
    CompanyMetadata("fixture-peer-3", "Fixture Power Services", "Fixture Power", "US", ("fixture-security-3",), "fixture", _RETRIEVED_AT, "services", "Electrical Equipment", Decimal("1100"), Decimal("0.07"), Decimal("0.14"), Decimal("0.22"), ("energy",)),
    CompanyMetadata("fixture-peer-4", "Fixture Turbine Group", "Fixture Turbine", "US", ("fixture-security-4",), "fixture", _RETRIEVED_AT, "equipment", "Industrial Machinery", Decimal("800"), Decimal("0.09"), Decimal("0.10"), Decimal("0.38"), ("energy",)),
    CompanyMetadata("fixture-peer-5", "Fixture Atomic Labs", "Fixture Atomic", "US", ("fixture-security-5",), "fixture", _RETRIEVED_AT, "technology", "Electrical Equipment", Decimal("500"), Decimal("0.20"), Decimal("-0.05"), Decimal("0.55"), ("nuclear",)),
)
_STATEMENTS = tuple(
    FinancialStatementRecord(
        entity_id=company.company_id,
        statement_type="income",
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        effective_date=date(year + 1, 1, 2),
        values={"revenue": company.size * (Decimal("0.82") + Decimal(year - 2023) * Decimal("0.09")), "operating_income": company.size * Decimal("0.08"), "net_income": company.size * Decimal("0.06")},
        units="USD",
        source="fixture",
        retrieved_at=_RETRIEVED_AT,
    )
    for company in _COMPANIES
    for year in (2023, 2024, 2025)
)


class FixtureProvider(FinancialDataProvider):
    """Small, deterministic US-company dataset for local analysis and tests."""

    _retrieved_at = _RETRIEVED_AT
    _companies = _COMPANIES
    _company = _companies[0]
    _statements = _STATEMENTS
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
        return next((company for company in self._companies if company.company_id == company_id), None)

    @property
    def company_ids(self) -> tuple[str, ...]:
        return tuple(company.company_id for company in self._companies)

    def get_financial_statements(
        self, entity_id: str, period_start: date | None = None, period_end: date | None = None
    ) -> tuple[FinancialStatementRecord, ...]:
        return tuple(sorted(
            (record for record in self._statements
             if record.entity_id == entity_id
             and (period_start is None or record.period_end >= period_start)
             and (period_end is None or record.period_start <= period_end)),
            key=lambda record: record.period_end,
            reverse=True,
        ))

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
        company = self.get_company_metadata(entity_id)
        if company is None or date(2025, 1, 1) > as_of:
            return None
        return ClassificationRecord(
            entity_id=entity_id,
            sector="Energy",
            industry=company.industry,
            effective_date=date(2025, 1, 1),
            source="fixture",
            retrieved_at=self._retrieved_at,
        )

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
