"""Thin Celery boundary for durable analysis-run execution."""

from typing import Any

from config.celery import app
from financials.models import AnalysisRun
from financials.services import execute_analysis_run, start_analysis_run


def coordinate_analysis_run(run: AnalysisRun) -> dict[str, Any]:
    """Default coordinator seam; analytical engines can be composed here later.

    The task delegates persistence and status handling to ``execute_analysis_run``;
    this function is intentionally replaceable in tests and by the full analysis
    coordinator without changing the worker boundary.
    """
    return {"analysis_run_id": run.pk, "security_id": run.security_id, "status": "analysis_completed"}


@app.task(bind=True, name="financials.run_analysis", autoretry_for=(), acks_late=True)
def run_analysis(self, run_id: int) -> dict[str, Any]:
    """Execute a queued run once; redelivery of a completed run is harmless."""
    run = AnalysisRun.objects.get(pk=run_id)
    if run.status in (AnalysisRun.Status.SUCCEEDED, AnalysisRun.Status.PARTIALLY_EVALUABLE, AnalysisRun.Status.FAILED):
        return {"run_id": run.pk, "status": run.status, "idempotent": True}
    if run.status == AnalysisRun.Status.QUEUED:
        start_analysis_run(run)
    return _execute(run)


def _execute(run: AnalysisRun) -> dict[str, Any]:
    saved = execute_analysis_run(run, coordinate_analysis_run) if run.status == AnalysisRun.Status.CREATED else execute_queued_run(run)
    return {"run_id": saved.pk, "status": saved.status, "idempotent": False}


def execute_queued_run(run: AnalysisRun) -> AnalysisRun:
    """Complete a run already moved to RUNNING by the task."""
    try:
        result = coordinate_analysis_run(run)
        from financials.services import finish_analysis_run
        return finish_analysis_run(run, output=result, partial=bool(result.get("partially_evaluable", False)), errors=result.get("errors", ()))
    except Exception as exc:
        from financials.services import fail_analysis_run
        fail_analysis_run(run, str(exc))
        raise


def submit_analysis_run(run: AnalysisRun):
    """Queue work and return immediately with the broker's async handle."""
    from financials.services import queue_analysis_run
    queue_analysis_run(run)
    return run_analysis.apply_async(args=(run.pk,))


submit_full_analysis = submit_analysis_run
