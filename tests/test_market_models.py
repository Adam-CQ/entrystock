from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from companies.models import Company, Exchange, Security
from market_data.models import CorporateAction, PriceCorporateAction, PriceObservation


@pytest.fixture
def security() -> Security:
    exchange = Exchange.objects.create(code="NYSE", name="New York Stock Exchange", mic="XNYS")
    company = Company.objects.create(legal_name="Example Market Corporation", common_name="Example Market")
    return Security.objects.create(company=company, exchange=exchange, security_identifier="example-market-common")


def price_defaults(security: Security, observed_at: datetime) -> dict[str, object]:
    return {
        "security": security,
        "source": "fixture",
        "observed_at": observed_at,
        "trading_date": observed_at.date(),
        "currency_code": "USD",
        "close": Decimal("100.00"),
        "adjusted_close": Decimal("98.00"),
        "retrieved_at": datetime(2026, 9, 1, 12, tzinfo=timezone.utc),
    }


@pytest.mark.django_db
def test_prices_preserve_adjustment_status_and_corporate_action_link(security: Security) -> None:
    action = CorporateAction.objects.create(
        security=security,
        source="fixture",
        source_action_id="split-2026-08-01",
        action_type=CorporateAction.ActionType.STOCK_SPLIT,
        ex_date=date(2026, 8, 1),
        ratio=Decimal("2"),
    )
    price = PriceObservation.objects.create(
        **price_defaults(security, datetime(2026, 8, 3, 20, tzinfo=timezone.utc)),
        adjustment_status=PriceObservation.AdjustmentStatus.FULLY_ADJUSTED,
    )
    PriceCorporateAction.objects.create(price_observation=price, corporate_action=action)

    assert price.adjustment_status == "fully_adjusted"
    assert list(price.action_links.values_list("corporate_action_id", flat=True)) == [action.id]


@pytest.mark.django_db
def test_duplicate_price_source_and_timestamp_is_rejected(security: Security) -> None:
    observed_at = datetime(2026, 8, 3, 20, tzinfo=timezone.utc)
    PriceObservation.objects.create(**price_defaults(security, observed_at))

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PriceObservation.objects.create(**price_defaults(security, observed_at))


@pytest.mark.django_db
def test_prices_are_returned_in_timestamp_order_even_when_inserted_out_of_order(security: Security) -> None:
    late = PriceObservation.objects.create(**price_defaults(security, datetime(2026, 8, 3, 20, tzinfo=timezone.utc)))
    early = PriceObservation.objects.create(**price_defaults(security, datetime(2026, 8, 2, 20, tzinfo=timezone.utc)))

    assert list(PriceObservation.objects.values_list("id", flat=True)) == [early.id, late.id]


@pytest.mark.django_db
def test_timestamp_boundary_is_timezone_aware_and_date_is_explicit(security: Security) -> None:
    boundary = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    price = PriceObservation.objects.create(**price_defaults(security, boundary))

    price.refresh_from_db()
    assert price.observed_at == boundary
    assert price.trading_date == date(2026, 1, 1)
