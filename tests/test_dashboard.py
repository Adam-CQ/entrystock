import pytest
from django.core.management import call_command
from django.urls import reverse

from companies.models import Company


pytestmark = pytest.mark.django_db


def test_dashboard_renders_complete_fixture_analysis_workflow():
    call_command("load_fixture_data", verbosity=0)

    response = __import__("django.test", fromlist=["Client"]).Client().get(reverse("dashboard"))

    assert response.status_code == 200
    body = response.content.decode()
    for label in ("Recommendation", "Fair value", "Entry zone", "Proposed peer group", "DCF assumptions", "DCF sensitivity", "Peer valuation", "Historical valuation", "Forecast comparison", "Momentum", "Composite score breakdown", "Data quality"):
        assert label in body
    assert "Fixture Energy" in body
    assert len(response.context["peers"]) == 5


def test_dashboard_company_selector_changes_selected_company():
    call_command("load_fixture_data", verbosity=0)
    company = Company.objects.order_by("id").last()

    response = __import__("django.test", fromlist=["Client"]).Client().get(reverse("dashboard"), {"company": company.pk})

    assert response.status_code == 200
    assert response.context["selected_company"] == company
