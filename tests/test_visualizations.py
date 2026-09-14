import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_chart_payloads_have_five_auditable_plotly_figures():
    call_command("load_fixture_data", verbosity=0)
    charts = Client().get(reverse("dashboard")).context["chart_payloads"]
    assert [chart["id"] for chart in charts] == ["dcf-sensitivity", "historical-valuation", "peer-multiples", "forecast-divergence", "company-peer-momentum"]
    assert all(chart["as_of"] and chart["source"] and chart["units"] for chart in charts)
    assert all("data" in chart["figure"] and "layout" in chart["figure"] for chart in charts)
