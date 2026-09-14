import subprocess
import sys

from analytics import PACKAGE_VERSION
from api.main import SERVICE_VERSION
from config.analytics_boundary import analytics_package_version


def test_django_side_and_fastapi_side_share_analytics_boundary() -> None:
    assert analytics_package_version() == PACKAGE_VERSION
    assert SERVICE_VERSION == PACKAGE_VERSION


def test_analytics_package_imports_without_web_frameworks() -> None:
    script = """
import sys
import analytics
import analytics.backtesting
import analytics.data_quality
import analytics.explanations
import analytics.forecasts
import analytics.momentum
import analytics.peer_analysis
import analytics.scoring
import analytics.valuation
assert not any(name == 'django' or name.startswith('django.') for name in sys.modules)
assert not any(name == 'fastapi' or name.startswith('fastapi.') for name in sys.modules)
assert not any(name == 'celery' or name.startswith('celery.') for name in sys.modules)
"""
    result = subprocess.run([sys.executable, "-c", script], check=False, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
