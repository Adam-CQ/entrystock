"""Compatibility entrypoint for the analytical API.

New deployments should use ``entrystock.analytics_api.main``. Keeping this
module preserves the original ``api.main:app`` command while the package
layout is migrated.
"""

from entrystock.analytics_api.main import HealthResponse, SERVICE_VERSION, app, health

__all__ = ["HealthResponse", "SERVICE_VERSION", "app", "health"]
