from django.core.management import call_command
import pytest

from companies.models import Company, Security
from financials.models import IncomeStatement
from market_data.models import CorporateAction, PriceObservation


pytestmark = pytest.mark.django_db


def test_fixture_import_loads_case_study_and_is_idempotent(capsys):
    call_command("load_fixture_data")
    first_counts = (Company.objects.count(), Security.objects.count(), IncomeStatement.objects.count())
    output = capsys.readouterr().out

    call_command("load_fixture_data")
    second_counts = (Company.objects.count(), Security.objects.count(), IncomeStatement.objects.count())

    assert first_counts == (6, 6, 18)
    assert second_counts == first_counts
    assert "Imported 6 companies" in output
    assert PriceObservation.objects.count() == 1
    assert CorporateAction.objects.count() == 1


def test_fixture_import_keeps_provenance_and_freshness():
    call_command("load_fixture_data", verbosity=0)
    statement = IncomeStatement.objects.get(company__legal_name="Fixture Energy Corporation", reporting_period__fiscal_year=2025)

    assert statement.source == "fixture"
    assert statement.units == "USD"
    assert statement.effective_date.isoformat() == "2026-01-02"
    assert statement.retrieved_at.isoformat().startswith("2026-01-02T12:00:00")
