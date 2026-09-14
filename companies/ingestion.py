"""Provider-neutral fixture ingestion into the normalized application models."""

from dataclasses import dataclass, field
from datetime import date

from django.db import transaction

from analytics.provider_contracts import FinancialDataProvider
from companies.models import Company, Exchange, Industry, Sector, Security, TickerIdentifier
from financials.models import FilingMetadata, IncomeStatement, ReportingPeriod
from market_data.models import CorporateAction, PriceObservation


@dataclass
class ImportReport:
    companies: int = 0
    securities: int = 0
    statements: int = 0
    prices: int = 0
    corporate_actions: int = 0
    errors: list[str] = field(default_factory=list)


def import_fixture_data(provider: FinancialDataProvider, *, as_of: date | None = None) -> ImportReport:
    """Import all companies exposed by a provider, safely repeatable by source IDs."""

    report = ImportReport()
    company_ids = _provider_company_ids(provider)
    exchange, _ = Exchange.objects.get_or_create(code="FIX", defaults={"name": "Fixture Exchange", "country_code": "US"})

    with transaction.atomic():
        for company_id in company_ids:
            metadata = provider.get_company_metadata(company_id)
            if metadata is None or metadata.country_code != "US":
                report.errors.append(f"company {company_id}: missing US metadata")
                continue
            effective_as_of = as_of or metadata.retrieved_at.date()
            classification = provider.get_classifications(company_id, effective_as_of)
            sector = None
            industry = None
            if classification and classification.sector:
                sector, _ = Sector.objects.get_or_create(name=classification.sector)
                if classification.industry:
                    industry, _ = Industry.objects.get_or_create(sector=sector, name=classification.industry)
            company, _ = Company.objects.update_or_create(
                legal_name=metadata.legal_name,
                defaults={"common_name": metadata.common_name, "country_code": metadata.country_code, "sector": sector, "industry": industry},
            )
            report.companies += 1
            for security_identifier in metadata.security_identifiers:
                security, _ = Security.objects.update_or_create(
                    security_identifier=security_identifier,
                    defaults={"company": company, "exchange": exchange, "currency_code": "USD"},
                )
                TickerIdentifier.objects.update_or_create(
                    exchange=exchange,
                    symbol=_ticker_for(security_identifier),
                    defaults={"security": security, "is_primary": True},
                )
                report.securities += 1
                _import_prices(provider, security, report)
                _import_actions(provider, security, report)
            _import_statements(provider, company, report)
    return report


def _provider_company_ids(provider: FinancialDataProvider) -> tuple[str, ...]:
    """Discover fixture companies without adding provider-specific calls to the importer."""

    ids = getattr(provider, "company_ids", None)
    if ids is not None:
        return tuple(ids)
    company = getattr(provider, "_company", None)
    return (company.company_id,) if company is not None else ()


def _ticker_for(identifier: str) -> str:
    return identifier.removeprefix("fixture-").replace("security", "FX").replace("-", "")[:16].upper()


def _import_statements(provider: FinancialDataProvider, company: Company, report: ImportReport) -> None:
    for record in provider.get_financial_statements(company_id_for(company, provider)):
        period, _ = ReportingPeriod.objects.update_or_create(
            company=company,
            security=None,
            period_type=ReportingPeriod.PeriodType.ANNUAL,
            fiscal_year=record.period_end.year,
            fiscal_period="FY",
            defaults={"period_start": record.period_start, "period_end": record.period_end},
        )
        filing, _ = FilingMetadata.objects.update_or_create(
            source=record.source,
            source_document_id=f"{record.entity_id}:{record.period_end.isoformat()}",
            defaults={"company": company, "reporting_period": period, "retrieved_at": record.retrieved_at, "effective_date": record.effective_date, "units": record.units, "form_type": "fixture"},
        )
        if record.statement_type == "income":
            IncomeStatement.objects.update_or_create(
                company=company,
                security=None,
                reporting_period=period,
                source=record.source,
                defaults={"filing": filing, "retrieved_at": record.retrieved_at, "effective_date": record.effective_date, "units": record.units, "revenue": record.values.get("revenue"), "operating_income": record.values.get("operating_income"), "net_income": record.values.get("net_income")},
            )
            report.statements += 1


def company_id_for(company: Company, provider: FinancialDataProvider) -> str:
    for company_id in _provider_company_ids(provider):
        metadata = provider.get_company_metadata(company_id)
        if metadata and metadata.legal_name == company.legal_name:
            return company_id
    raise ValueError(f"no provider identifier for {company.legal_name}")


def _import_prices(provider: FinancialDataProvider, security: Security, report: ImportReport) -> None:
    from datetime import datetime, timezone

    records = provider.get_prices(security.security_identifier, datetime.min.replace(tzinfo=timezone.utc), datetime.max.replace(tzinfo=timezone.utc))
    for record in records:
        PriceObservation.objects.update_or_create(
            security=security, observed_at=record.observed_at, source=record.source,
            defaults={"trading_date": record.trading_date, "currency_code": record.currency_code, "open": record.open, "high": record.high, "low": record.low, "close": record.close, "adjusted_close": record.adjusted_close, "volume": record.volume, "adjustment_status": record.adjustment_status, "retrieved_at": record.retrieved_at},
        )
        report.prices += 1


def _import_actions(provider: FinancialDataProvider, security: Security, report: ImportReport) -> None:
    for record in provider.get_corporate_actions(security.security_identifier):
        CorporateAction.objects.update_or_create(
            source=record.source, source_action_id=record.source_action_id,
            defaults={"security": security, "action_type": record.action_type, "ex_date": record.ex_date, "ratio": record.ratio, "cash_amount": record.cash_amount, "currency_code": record.currency_code},
        )
        report.corporate_actions += 1
