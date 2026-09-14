"""Django/Celery-side import boundary for shared analytics contracts."""

from analytics import PACKAGE_VERSION


def analytics_package_version() -> str:
    return PACKAGE_VERSION
