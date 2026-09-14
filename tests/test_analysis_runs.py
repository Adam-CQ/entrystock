import pytest

from companies.models import Company, Exchange, Security
from financials.models import AnalysisRun
from financials.services import create_analysis_run, execute_analysis_run, finish_analysis_run, queue_analysis_run, start_analysis_run


@pytest.fixture
def security(db):
    exchange = Exchange.objects.create(code="NYSE", name="New York Stock Exchange", mic="XNYS")
    company = Company.objects.create(legal_name="Run Corp", common_name="Run Corp", cik="0000000001")
    return Security.objects.create(company=company, exchange=exchange, security_identifier="run-security")


def test_analysis_run_snapshots_inputs_peers_and_reproduces_successful_output(security):
    peer = Company.objects.create(legal_name="Peer Corp", common_name="Peer Corp", cik="0000000002")
    run = create_analysis_run(security=security, confirmed_peers=[peer], data_snapshot_ids={"prices": "snap-1"}, assumptions={"growth": 0.1}, score_configuration={"version": "v1"}, hard_rules=[{"rule_id": "r1"}], input_parameters={"as_of": "2026-09-14"})
    original_inputs = (run.data_snapshot_ids, run.assumptions, run.score_configuration, run.hard_rules, run.input_parameters)
    saved = execute_analysis_run(run, lambda current: {"rating": "WATCH", "score": 0.5})
    reloaded = AnalysisRun.objects.get(pk=saved.pk)
    assert reloaded.status == AnalysisRun.Status.SUCCEEDED
    assert reloaded.output == {"rating": "WATCH", "score": 0.5}
    assert (reloaded.data_snapshot_ids, reloaded.assumptions, reloaded.score_configuration, reloaded.hard_rules, reloaded.input_parameters) == original_inputs
    assert list(reloaded.confirmed_peers.values_list("pk", flat=True)) == [peer.pk]


def test_analysis_run_supports_partial_and_failure_states(security):
    partial = create_analysis_run(security=security)
    execute_analysis_run(partial, lambda current: {"partially_evaluable": True, "errors": ["missing forecast"]})
    assert partial.status == AnalysisRun.Status.PARTIALLY_EVALUABLE
    failed = create_analysis_run(security=security)
    with pytest.raises(RuntimeError, match="provider unavailable"):
        execute_analysis_run(failed, lambda current: (_ for _ in ()).throw(RuntimeError("provider unavailable")))
    failed.refresh_from_db()
    assert failed.status == AnalysisRun.Status.FAILED
    assert failed.errors == ["provider unavailable"]


def test_analysis_run_rejects_invalid_transitions_and_duplicate_completion(security):
    run = create_analysis_run(security=security)
    with pytest.raises(ValueError, match="only a running"):
        finish_analysis_run(run, output={})
    start_analysis_run(run)
    finish_analysis_run(run, output={"ok": True})
    with pytest.raises(ValueError, match="already"):
        execute_analysis_run(run, lambda current: {})


def test_analysis_run_queue_state_is_explicit_and_transitions_to_running(security):
    run = create_analysis_run(security=security)
    queue_analysis_run(run)
    assert run.status == AnalysisRun.Status.QUEUED
    start_analysis_run(run)
    assert run.status == AnalysisRun.Status.RUNNING
