from django.core.validators import MinLengthValidator
from django.db import models


class Exchange(models.Model):
    code = models.CharField(max_length=16, unique=True, validators=[MinLengthValidator(2)])
    name = models.CharField(max_length=120, unique=True)
    country_code = models.CharField(max_length=2, default="US")
    mic = models.CharField(max_length=4, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Sector(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Industry(models.Model):
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="industries")
    name = models.CharField(max_length=120)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sector", "name"], name="unique_industry_per_sector"),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Company(models.Model):
    legal_name = models.CharField(max_length=240, unique=True)
    common_name = models.CharField(max_length=240)
    cik = models.CharField(max_length=10, unique=True, null=True, blank=True)
    country_code = models.CharField(max_length=2, default="US")
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="companies", null=True, blank=True)
    industry = models.ForeignKey(Industry, on_delete=models.PROTECT, related_name="companies", null=True, blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["common_name", "id"]

    def __str__(self) -> str:
        return self.common_name


class Security(models.Model):
    class SecurityType(models.TextChoices):
        COMMON_STOCK = "common_stock", "Common stock"
        PREFERRED_STOCK = "preferred_stock", "Preferred stock"
        ADR = "adr", "American depositary receipt"
        ETF = "etf", "Exchange-traded fund"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="securities")
    exchange = models.ForeignKey(Exchange, on_delete=models.PROTECT, related_name="securities")
    security_identifier = models.CharField(max_length=64, unique=True)
    security_type = models.CharField(max_length=24, choices=SecurityType.choices, default=SecurityType.COMMON_STOCK)
    share_class = models.CharField(max_length=16, default="")
    currency_code = models.CharField(max_length=3, default="USD")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "exchange", "security_type", "share_class"],
                name="unique_company_exchange_security_class",
            ),
        ]
        ordering = ["security_identifier"]

    def __str__(self) -> str:
        return self.security_identifier


class TickerIdentifier(models.Model):
    security = models.ForeignKey(Security, on_delete=models.CASCADE, related_name="ticker_identifiers")
    exchange = models.ForeignKey(Exchange, on_delete=models.PROTECT, related_name="ticker_identifiers")
    symbol = models.CharField(max_length=16, validators=[MinLengthValidator(1)])
    is_primary = models.BooleanField(default=False)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["exchange", "symbol"], name="unique_ticker_per_exchange"),
        ]
        ordering = ["exchange", "symbol"]

    def save(self, *args, **kwargs):
        self.symbol = self.symbol.upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.symbol}:{self.exchange.code}"


class PeerGroupProposal(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        CONFIRMED = "confirmed", "Confirmed"

    company = models.OneToOneField(Company, on_delete=models.PROTECT, related_name="peer_group_proposal")
    source = models.CharField(max_length=120, default="fixture")
    generated_at = models.DateTimeField(auto_now=True)
    minimum_candidates = models.PositiveSmallIntegerField(default=5)
    eligible_count = models.PositiveIntegerField(default=0)
    sufficient_universe = models.BooleanField(default=False)
    explanation = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PROPOSED)

    class Meta:
        ordering = ["company__common_name"]


class PeerGroupMember(models.Model):
    class Origin(models.TextChoices):
        ALGORITHM = "algorithm", "Algorithmic proposal"
        USER_ADDED = "user_added", "User added"
        USER_REMOVED = "user_removed", "User removed"

    proposal = models.ForeignKey(PeerGroupProposal, on_delete=models.CASCADE, related_name="members")
    peer = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="peer_group_memberships")
    rank = models.PositiveIntegerField(null=True, blank=True)
    score = models.FloatField(default=0)
    confidence = models.FloatField(default=0)
    reasons = models.JSONField(default=list)
    component_scores = models.JSONField(default=dict)
    selected = models.BooleanField(default=True)
    origin = models.CharField(max_length=16, choices=Origin.choices, default=Origin.ALGORITHM)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["proposal", "peer"], name="unique_peer_group_member"),
        ]
        ordering = ["rank", "peer__common_name", "id"]
