from datetime import date, datetime, timedelta, timezone

from analytics.data_quality import assess_source, summarize_quality


def _report(age=0, **kwargs):
    observed = date(2026, 1, 10) - timedelta(days=age)
    defaults = {"retrieved_at": datetime.combine(observed, datetime.min.time(), tzinfo=timezone.utc), "effective_date": observed, "coverage": 1}
    defaults.update(kwargs)
    return assess_source("prices", analysis_date=date(2026, 1, 10), **defaults)


def test_fresh_and_boundary_data_is_complete_but_stale_data_warns_then_blocks():
    assert _report(age=3).status == "complete"
    assert _report(age=4).status == "warning"
    assert _report(age=10).status == "warning"
    assert _report(age=11).status == "blocked"


def test_missing_provenance_and_zero_coverage_are_not_evaluable_or_blocked():
    assert _report(retrieved_at=None, effective_date=None).status == "not_evaluable"
    assert _report(coverage=0).status == "blocked"


def test_required_fields_and_multiple_source_summary_are_actionable():
    fundamentals = assess_source("fundamentals", analysis_date=date(2026, 1, 10), retrieved_at=datetime(2026, 1, 10, tzinfo=timezone.utc), effective_date=date(2026, 1, 10), coverage=1, missing_fields=("revenue",))
    summary = summarize_quality((fundamentals, _report(age=4)))
    assert fundamentals.status == "blocked"
    assert summary.overall_status == "blocked"
    assert summary.blocking_reasons and summary.warnings
