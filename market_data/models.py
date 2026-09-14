from django.core.validators import MinValueValidator
from django.db import models

from companies.models import Security


class CorporateAction(models.Model):
    class ActionType(models.TextChoices):
        CASH_DIVIDEND = "cash_dividend", "Cash dividend"
        STOCK_SPLIT = "stock_split", "Stock split"
        SPINOFF = "spinoff", "Spinoff"
        RIGHTS_ISSUE = "rights_issue", "Rights issue"

    security = models.ForeignKey(Security, on_delete=models.PROTECT, related_name="corporate_actions")
    source = models.CharField(max_length=120)
    source_action_id = models.CharField(max_length=240)
    action_type = models.CharField(max_length=24, choices=ActionType.choices)
    announced_at = models.DateTimeField(null=True, blank=True)
    ex_date = models.DateField()
    ratio = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True, validators=[MinValueValidator(0)])
    cash_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    currency_code = models.CharField(max_length=3, default="USD")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_action_id"], name="unique_corporate_action_source_id"
            ),
        ]
        ordering = ["ex_date", "id"]

    def __str__(self) -> str:
        return f"{self.security} {self.action_type} {self.ex_date}"


class PriceObservation(models.Model):
    class AdjustmentStatus(models.TextChoices):
        UNADJUSTED = "unadjusted", "Unadjusted"
        SPLIT_ADJUSTED = "split_adjusted", "Split adjusted"
        FULLY_ADJUSTED = "fully_adjusted", "Fully adjusted"

    security = models.ForeignKey(Security, on_delete=models.PROTECT, related_name="price_observations")
    source = models.CharField(max_length=120)
    observed_at = models.DateTimeField()
    trading_date = models.DateField()
    currency_code = models.CharField(max_length=3)
    price_units = models.CharField(max_length=24, default="currency/share")
    volume_units = models.CharField(max_length=24, default="shares")
    open = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True)
    high = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True)
    low = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True)
    close = models.DecimalField(max_digits=24, decimal_places=8)
    adjusted_close = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True)
    volume = models.DecimalField(max_digits=30, decimal_places=4, null=True, blank=True)
    adjustment_status = models.CharField(
        max_length=24, choices=AdjustmentStatus.choices, default=AdjustmentStatus.UNADJUSTED
    )
    retrieved_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["security", "observed_at", "source"], name="unique_price_observation_source"
            ),
        ]
        ordering = ["security", "observed_at", "source", "id"]

    def __str__(self) -> str:
        return f"{self.security} {self.observed_at.isoformat()}"


class PriceCorporateAction(models.Model):
    price_observation = models.ForeignKey(PriceObservation, on_delete=models.CASCADE, related_name="action_links")
    corporate_action = models.ForeignKey(CorporateAction, on_delete=models.PROTECT, related_name="price_links")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["price_observation", "corporate_action"], name="unique_price_corporate_action_link"
            ),
        ]
