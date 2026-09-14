from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from companies.models import Company, Exchange, Security
from financials.models import BalanceSheet, CashFlowStatement, FilingMetadata, IncomeStatement, ReportingPeriod


@pytest.fixture
def financial_data() -> dict[str, object]:
    exchange = Exchange.objects.create(code="NYSE", name="New York Stock Exchange", mic="XNYS")
    company = Company.objects.create(legal_name="Example Financials Corporation", common_name="Example Financials")
    security = Security.objects.create(company=company, exchange=exchange, security_identifier="example-common")
    period = ReportingPeriod.objects.create(
        company=company,
        security=security,
        period_type=ReportingPeriod.PeriodType.QUARTERLY,
        fiscal_year=2026,
        fiscal_period="Q2",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 6, 30),
    )
    filing = FilingMetadata.objects.create(
        company=company,
        security=security,
        reporting_period=period,
        source="sec",
        source_document_id="0000000001-26-000001",
        retrieved_at=datetime(2026, 8, 1, 12, tzinfo=timezone.utc),
        effective_date=date(2026, 7, 31),
        units="USD",
        form_type="10-Q",
    )
    return {"company": company, "security": security, "period": period, "filing": filing}


@pytest.mark.django_db
def test_statement_stores_period_provenance_units_and_quality(financial_data: dict[str, object]) -> None:
    statement = IncomeStatement.objects.create(
        company=financial_data["company"],
        security=financial_data["security"],
        reporting_period=financial_data["period"],
        filing=financial_data["filing"],
        source="sec",
        retrieved_at=financial_data["filing"].retrieved_at,
        effective_date=date(2026, 7, 31),
        units="USD",
        data_quality=IncomeStatement.DataQuality.VALID,
        revenue=Decimal("100.50"),
        net_income=Decimal("10.25"),
    )

    assert statement.reporting_period.period_end == date(2026, 6, 30)
    assert statement.units == "USD"
    assert statement.data_quality == "valid"
    assert statement.filing.units == "USD"


@pytest.mark.django_db
def test_each_statement_type_has_a_distinct_snapshot_constraint(financial_data: dict[str, object]) -> None:
    common = {
        "company": financial_data["company"],
        "security": financial_data["security"],
        "reporting_period": financial_data["period"],
        "filing": financial_data["filing"],
        "source": "sec",
        "retrieved_at": financial_data["filing"].retrieved_at,
        "effective_date": date(2026, 7, 31),
        "units": "USD",
    }
    IncomeStatement.objects.create(**common)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IncomeStatement.objects.create(**common)

    BalanceSheet.objects.create(**common)
    CashFlowStatement.objects.create(**common)


@pytest.mark.django_db
def test_filing_source_document_and_reporting_period_identity_are_unique(financial_data: dict[str, object]) -> None:
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            FilingMetadata.objects.create(
                company=financial_data["company"],
                reporting_period=financial_data["period"],
                source="sec",
                source_document_id="0000000001-26-000001",
                retrieved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
                effective_date=date(2026, 7, 31),
                units="USD",
                form_type="10-Q",
            )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ReportingPeriod.objects.create(
                company=financial_data["company"],
                security=financial_data["security"],
                period_type="quarterly",
                fiscal_year=2026,
                fiscal_period="Q2",
                period_start=date(2026, 4, 1),
                period_end=date(2026, 6, 30),
            )
