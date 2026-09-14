"""Persistence workflow for reproducible analysis runs."""

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from django.db import transaction

from financials.models import AnalysisRun


@transaction.atomic
def create_analysis_run(*, security, confirmed_peers=(), data_snapshot_ids=None, assumptions=None, score_configuration=None, hard_rules=None, input_parameters=None) -> AnalysisRun:
    """Create a run with JSON-serializable inputs that are not changed later."""
    run = AnalysisRun.objects.create(
        security=security,
        data_snapshot_ids=dict(data_snapshot_ids or {}),
        assumptions=dict(assumptions or {}),
        score_configuration=dict(score_configuration or {}),
        hard_rules=list(hard_rules or []),
        input_parameters=dict(input_parameters or {}),
    )
    run.confirmed_peers.set(confirmed_peers)
    return run


@transaction.atomic
def start_analysis_run(run: AnalysisRun) -> AnalysisRun:
    run.transition_to(AnalysisRun.Status.RUNNING)
    run.started_at = datetime.now(timezone.utc)
    run.save(update_fields=["status", "started_at"])
    return run


@transaction.atomic
def queue_analysis_run(run: AnalysisRun) -> AnalysisRun:
    run.transition_to(AnalysisRun.Status.QUEUED)
    run.save(update_fields=["status"])
    return run


@transaction.atomic
def finish_analysis_run(run: AnalysisRun, *, output: Mapping[str, Any] | None = None, errors=(), partial: bool = False) -> AnalysisRun:
    if run.status != AnalysisRun.Status.RUNNING:
        raise ValueError("only a running analysis run can be completed")
    run.output = dict(output) if output is not None else None
    run.errors = list(errors)
    run.transition_to(AnalysisRun.Status.PARTIALLY_EVALUABLE if partial else AnalysisRun.Status.SUCCEEDED)
    run.completed_at = datetime.now(timezone.utc)
    run.save(update_fields=["status", "output", "errors", "completed_at"])
    return run


@transaction.atomic
def fail_analysis_run(run: AnalysisRun, error: str) -> AnalysisRun:
    if run.status not in (AnalysisRun.Status.CREATED, AnalysisRun.Status.RUNNING):
        raise ValueError("only an unfinished analysis run can fail")
    run.errors = [error]
    run.transition_to(AnalysisRun.Status.FAILED)
    run.completed_at = datetime.now(timezone.utc)
    run.save(update_fields=["status", "errors", "completed_at"])
    return run


def execute_analysis_run(run: AnalysisRun, analyzer: Callable[[AnalysisRun], Mapping[str, Any]]) -> AnalysisRun:
    """Run one supplied domain coordinator and persist its result exactly once."""
    if run.status != AnalysisRun.Status.CREATED:
        raise ValueError("analysis run has already started or completed")
    start_analysis_run(run)
    try:
        result = analyzer(run)
        if not isinstance(result, Mapping):
            raise TypeError("analysis coordinator must return a mapping")
        return finish_analysis_run(run, output=result, partial=bool(result.get("partially_evaluable", False)), errors=result.get("errors", ()))
    except Exception as exc:
        fail_analysis_run(run, str(exc))
        raise
