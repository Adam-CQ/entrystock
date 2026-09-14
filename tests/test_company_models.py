import pytest
from django.db import IntegrityError, transaction

from companies.models import Company, Exchange, Industry, Sector, Security, TickerIdentifier


@pytest.fixture
def market_data() -> dict[str, object]:
    exchange = Exchange.objects.create(code="NYSE", name="New York Stock Exchange", mic="XNYS")
    sector = Sector.objects.create(name="Energy")
    industry = Industry.objects.create(sector=sector, name="Electrical Equipment")
    company = Company.objects.create(
        legal_name="Example Energy Corporation",
        common_name="Example Energy",
        cik="0001234567",
        sector=sector,
        industry=industry,
    )
    security = Security.objects.create(
        company=company,
        exchange=exchange,
        security_identifier="example-energy-common",
    )
    return {"exchange": exchange, "sector": sector, "industry": industry, "company": company, "security": security}


@pytest.mark.django_db
def test_company_is_distinct_from_its_listed_security(market_data: dict[str, object]) -> None:
    company = market_data["company"]
    security = market_data["security"]

    assert isinstance(company, Company)
    assert security.company_id == company.id
    assert security.security_identifier != company.legal_name


@pytest.mark.django_db
def test_exchange_code_and_name_are_unique() -> None:
    Exchange.objects.create(code="NYSE", name="New York Stock Exchange", mic="XNYS")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Exchange.objects.create(code="NYSE", name="Another Exchange", mic="XNAS")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Exchange.objects.create(code="XNAS", name="New York Stock Exchange", mic="XNAS")


@pytest.mark.django_db
def test_sector_and_industry_scope_names() -> None:
    sector = Sector.objects.create(name="Energy")
    Industry.objects.create(sector=sector, name="Electrical Equipment")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Industry.objects.create(sector=sector, name="Electrical Equipment")


@pytest.mark.django_db
def test_company_identifiers_are_unique(market_data: dict[str, object]) -> None:
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Company.objects.create(legal_name="Example Energy Corporation", common_name="Different name")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Company.objects.create(legal_name="Different Corporation", common_name="Different name", cik="0001234567")


@pytest.mark.django_db
def test_security_identifiers_and_company_security_class_are_unique(market_data: dict[str, object]) -> None:
    company = market_data["company"]
    exchange = market_data["exchange"]
    security = market_data["security"]

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Security.objects.create(company=company, exchange=exchange, security_identifier="another-id")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Security.objects.create(company=company, exchange=exchange, security_identifier=security.security_identifier)


@pytest.mark.django_db
def test_ticker_is_unique_within_exchange_and_normalized(market_data: dict[str, object]) -> None:
    exchange = market_data["exchange"]
    security = market_data["security"]
    TickerIdentifier.objects.create(security=security, exchange=exchange, symbol="exen")

    assert TickerIdentifier.objects.get().symbol == "EXEN"
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TickerIdentifier.objects.create(security=security, exchange=exchange, symbol="EXEN")
