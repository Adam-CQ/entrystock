from datetime import date

import pytest

from analytics.backtesting import build_fixture_backtesting_dataset


def test_snapshot_includes_only_records_available_on_or_before_analysis_date():
    dataset = build_fixture_backtesting_dataset()
    snapshot = dataset.snapshot(date(2026, 1, 2))
    assert [item.trading_date for item in snapshot.prices] == [date(2025, 12, 31)]
    assert [item.effective_date for item in snapshot.fundamentals] == [date(2025, 12, 31)]
    assert [item.period_end for item in snapshot.forecasts] == [date(2026, 12, 31)]
    assert len(snapshot.peer_memberships) == 1
    assert snapshot.classifications[0].industry == "Electrical Equipment"


def test_snapshot_excludes_future_revision_and_supports_exact_availability_date():
    dataset = build_fixture_backtesting_dataset()
    snapshot = dataset.query(date(2026, 7, 2))
    assert len(snapshot.prices) == 2
    assert len(snapshot.fundamentals) == 2
    assert {item.period_end for item in snapshot.forecasts} == {date(2026, 12, 31), date(2027, 12, 31)}
    assert {item.classification for item in snapshot.peer_memberships} == {"direct", "thematic"}
    assert {item.industry for item in snapshot.classifications} == {"Electrical Equipment", "Nuclear Technology"}


def test_empty_date_window_returns_no_future_information():
    snapshot = build_fixture_backtesting_dataset().snapshot(date(2024, 12, 31))
    assert snapshot.prices == snapshot.fundamentals == snapshot.forecasts == ()
    assert snapshot.peer_memberships == snapshot.classifications == ()


def test_invalid_analysis_date_is_rejected():
    with pytest.raises(TypeError):
        build_fixture_backtesting_dataset().snapshot("2026-01-02")
