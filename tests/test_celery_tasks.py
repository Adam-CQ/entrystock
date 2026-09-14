import pytest

from companies.models import Company, Exchange, Security
from financials.models import AnalysisRun
from financials.services import create_analysis_run
from financials import tasks


@pytest.fixture
def security(db):
    exchange = Exchange.objects.create(code="NASDAQ", name="Nasdaq", mic="XNAS")
    company = Company.objects.create(legal_name="Async Corp", common_name="Async Corp", cik="0000000003")
    return Security.objects.create(company=company, exchange=exchange, security_identifier="async-security")


def test_eager_task_completes_analysis_and_is_idempotent(security, settings, monkeypatch):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    run = create_analysis_run(security=security)
    monkeypatch.setattr(tasks, "coordinate_analysis_run", lambda current: {"rating": "WATCH"})
    first = tasks.submit_analysis_run(run)
    run.refresh_from_db()
    assert first.result["status"] == AnalysisRun.Status.SUCCEEDED
    assert run.status == AnalysisRun.Status.SUCCEEDED
    duplicate = tasks.run_analysis.apply(args=(run.pk,)).get()
    assert duplicate["idempotent"] is True
    assert AnalysisRun.objects.get(pk=run.pk).output == {"rating": "WATCH"}


def test_eager_task_records_actionable_failure(security, settings, monkeypatch):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    run = create_analysis_run(security=security)
    monkeypatch.setattr(tasks, "coordinate_analysis_run", lambda current: (_ for _ in ()).throw(RuntimeError("missing price snapshot")))
    with pytest.raises(RuntimeError, match="missing price snapshot"):
        tasks.submit_analysis_run(run)
    run.refresh_from_db()
    assert run.status == AnalysisRun.Status.FAILED
    assert run.errors == ["missing price snapshot"]
    assert run.completed_at is not None
