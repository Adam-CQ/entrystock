from django.core.validators import MinValueValidator
from django.db import models

from companies.models import Company, Security


class ForecastPeriod(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="forecast_periods")
    security = models.ForeignKey(Security, on_delete=models.PROTECT, related_name="forecast_periods", null=True, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    label = models.CharField(max_length=32)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company", "security", "period_start", "period_end"], name="unique_forecast_period"),
            models.CheckConstraint(condition=models.Q(period_start__lte=models.F("period_end")), name="forecast_period_start_before_end"),
        ]
        ordering = ["period_end", "id"]


class ForecastMeasure(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    default_units = models.CharField(max_length=32)

    class Meta:
        ordering = ["code"]


class CompanyForecast(models.Model):
    class Source(models.TextChoices):
        MANAGEMENT = "management", "Management guidance"
        CONSENSUS = "consensus", "Analyst consensus"
        INTERNAL = "internal", "Internal model"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="forecasts")
    security = models.ForeignKey(Security, on_delete=models.PROTECT, related_name="forecasts", null=True, blank=True)
    measure = models.ForeignKey(ForecastMeasure, on_delete=models.PROTECT, related_name="forecasts")
    period = models.ForeignKey(ForecastPeriod, on_delete=models.PROTECT, related_name="forecasts")
    source = models.CharField(max_length=16, choices=Source.choices)
    value = models.DecimalField(max_digits=28, decimal_places=8, null=True, blank=True)
    units = models.CharField(max_length=32)
    retrieved_at = models.DateTimeField(null=True, blank=True)
    effective_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company", "security", "measure", "period", "source", "effective_date"], name="unique_company_forecast_snapshot"),
        ]
        ordering = ["period__period_end", "measure__code", "source"]


class ReportingPeriod(models.Model):
    class PeriodType(models.TextChoices):
        ANNUAL = "annual", "Annual"
        QUARTERLY = "quarterly", "Quarterly"
        TTM = "ttm", "Trailing twelve months"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="reporting_periods")
    security = models.ForeignKey(
        Security, on_delete=models.PROTECT, related_name="reporting_periods", null=True, blank=True
    )
    period_type = models.CharField(max_length=16, choices=PeriodType.choices)
    fiscal_year = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    fiscal_period = models.CharField(max_length=8)
    period_start = models.DateField()
    period_end = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "security", "period_type", "fiscal_year", "fiscal_period"],
                name="unique_reporting_period_identity",
            ),
            models.CheckConstraint(
                condition=models.Q(period_start__lte=models.F("period_end")),
                name="reporting_period_start_before_end",
            ),
        ]
        ordering = ["-period_end", "-id"]

    def __str__(self) -> str:
        return f"{self.company} {self.fiscal_year} {self.fiscal_period}"


class FilingMetadata(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="filings")
    security = models.ForeignKey(Security, on_delete=models.PROTECT, related_name="filings", null=True, blank=True)
    reporting_period = models.ForeignKey(ReportingPeriod, on_delete=models.PROTECT, related_name="filings")
    source = models.CharField(max_length=120)
    source_document_id = models.CharField(max_length=240)
    retrieved_at = models.DateTimeField()
    effective_date = models.DateField()
    units = models.CharField(max_length=32)
    form_type = models.CharField(max_length=32)
    document_url = models.URLField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_document_id"], name="unique_filing_source_document"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.source}:{self.source_document_id}"


class StatementBase(models.Model):
    class DataQuality(models.TextChoices):
        MISSING = "missing", "Missing"
        VALID = "valid", "Valid"
        SUSPECT = "suspect", "Suspect"

    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    security = models.ForeignKey(Security, on_delete=models.PROTECT, null=True, blank=True)
    reporting_period = models.ForeignKey(ReportingPeriod, on_delete=models.PROTECT)
    filing = models.ForeignKey(FilingMetadata, on_delete=models.PROTECT)
    source = models.CharField(max_length=120)
    retrieved_at = models.DateTimeField()
    effective_date = models.DateField()
    units = models.CharField(max_length=32)
    data_quality = models.CharField(max_length=16, choices=DataQuality.choices, default=DataQuality.VALID)

    class Meta:
        abstract = True


class IncomeStatement(StatementBase):
    revenue = models.DecimalField(max_digits=24, decimal_places=4, null=True, blank=True)
    operating_income = models.DecimalField(max_digits=24, decimal_places=4, null=True, blank=True)
    net_income = models.DecimalField(max_digits=24, decimal_places=4, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "security", "reporting_period", "source"],
                name="unique_income_statement_snapshot",
            ),
        ]


class BalanceSheet(StatementBase):
    total_assets = models.DecimalField(max_digits=24, decimal_places=4, null=True, blank=True)
    total_liabilities = models.DecimalField(max_digits=24, decimal_places=4, null=True, blank=True)
    shareholders_equity = models.DecimalField(max_digits=24, decimal_places=4, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "security", "reporting_period", "source"],
                name="unique_balance_sheet_snapshot",
            ),
        ]


class CashFlowStatement(StatementBase):
    operating_cash_flow = models.DecimalField(max_digits=24, decimal_places=4, null=True, blank=True)
    investing_cash_flow = models.DecimalField(max_digits=24, decimal_places=4, null=True, blank=True)
    financing_cash_flow = models.DecimalField(max_digits=24, decimal_places=4, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "security", "reporting_period", "source"],
                name="unique_cash_flow_statement_snapshot",
            ),
        ]
