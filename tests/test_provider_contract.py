from datetime import date, datetime, timezone

from analytics.fixture_provider import FixtureProvider
from analytics.provider_contracts import FinancialDataProvider


def test_fixture_provider_implements_every_contract_operation() -> None:
    provider = FixtureProvider()
    assert isinstance(provider, FinancialDataProvider)

    assert provider.get_company_metadata("missing") is None
    assert provider.get_company_metadata("fixture-company") == provider.get_company_metadata("fixture-company")
    assert provider.get_financial_statements("missing") == ()
    assert provider.get_forecasts("missing", date(2026, 1, 2)) == ()
    assert provider.get_classifications("missing", date(2026, 1, 2)) is None
    assert provider.get_corporate_actions("missing") == ()


def test_fixture_provider_is_repeatable_and_respects_point_in_time_filters() -> None:
    provider = FixtureProvider()
    start = datetime(2026, 1, 2, 20, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, 20, tzinfo=timezone.utc)

    first = provider.get_prices("fixture-security", start, end)
    second = provider.get_prices("fixture-security", start, end)
    assert first == second
    assert first[0].adjustment_status == "fully_adjusted"
    assert provider.get_forecasts("fixture-company", date(2025, 12, 31)) == ()
    assert provider.get_classifications("fixture-company", date(2024, 12, 31)) is None


def test_fixture_records_expose_units_provenance_and_date_semantics() -> None:
    provider = FixtureProvider()
    statement = provider.get_financial_statements("fixture-company")[0]
    action = provider.get_corporate_actions("fixture-security")[0]

    assert statement.units == "USD"
    assert statement.source == "fixture"
    assert statement.effective_date == date(2026, 1, 2)
    assert action.ex_date == date(2025, 6, 1)
