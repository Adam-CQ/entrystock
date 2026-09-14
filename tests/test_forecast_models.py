from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from django.core.management import call_command

from companies.models import Company
from financials.models import CompanyForecast, ForecastMeasure, ForecastPeriod


pytestmark = pytest.mark.django_db


def test_forecast_records_store_three_sources_periods_units_and_freshness():
    call_command("load_fixture_data", verbosity=0)
    company = Company.objects.get(legal_name="Fixture Energy Corporation")
    period = ForecastPeriod.objects.create(company=company, period_start=date(2026, 1, 1), period_end=date(2026, 12, 31), label="FY2026")
    measure = ForecastMeasure.objects.create(code="revenue", name="Revenue", default_units="USD")
    retrieved = datetime(2026, 1, 2, tzinfo=timezone.utc)
    for source, value in (("management", "1100"), ("consensus", "1200"), ("internal", "1300")):
        CompanyForecast.objects.create(company=company, measure=measure, period=period, source=source, value=Decimal(value), units="USD", retrieved_at=retrieved, effective_date=date(2026, 1, 2))

    assert list(CompanyForecast.objects.values_list("source", flat=True)) == ["consensus", "internal", "management"]
    assert CompanyForecast.objects.get(source="internal").units == "USD"
    assert CompanyForecast.objects.get(source="management").effective_date == date(2026, 1, 2)
