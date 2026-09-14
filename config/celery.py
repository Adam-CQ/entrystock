"""Celery application configured from Django's environment settings."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("entrystock")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


celery_app = app
