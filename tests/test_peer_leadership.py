from datetime import date, timedelta

from analytics.momentum import PriceObservation, analyze_peer_leadership, calculate_momentum


def _prices(entity, slope, count=30):
    start = date(2026, 1, 1)
    return [PriceObservation(entity, start + timedelta(days=index), 100 * (1 + slope) ** index, 100) for index in range(count)]


def test_peer_leadership_identifies_sorted_leaders_laggards_and_lead_lag_spread():
    prices = _prices("selected", 0.01) + _prices("leader", 0.03) + _prices("middle", 0.01) + _prices("laggard", -0.02)
    momentum = calculate_momentum("selected", prices, peer_entities=("leader", "middle", "laggard"), as_of=date(2026, 1, 30), return_windows=(5,), moving_average_windows=(3, 5), breadth_window=5)
    result = analyze_peer_leadership(momentum, window=5, minimum_peers=3)

    assert result.leaders == ("leader",)
    assert result.laggards == ("laggard",)
    assert result.included_peers == ("leader", "middle", "laggard")
    assert result.lead_lag_status == "ok"
    assert result.lead_lag_value == 0
    assert "probabilistic" in result.probabilistic_notice


def test_peer_leadership_reports_ties_and_insufficient_or_missing_data():
    prices = _prices("selected", 0.01) + _prices("peer-a", 0.01) + _prices("peer-b", 0.01)
    momentum = calculate_momentum("selected", prices, peer_entities=("peer-a", "peer-b", "missing"), as_of=date(2026, 1, 30), return_windows=(5,), moving_average_windows=(3, 5), breadth_window=5)
    result = analyze_peer_leadership(momentum, window=5, minimum_peers=3)

    assert result.leaders == ("peer-a", "peer-b")
    assert result.laggards == ("peer-a", "peer-b")
    assert result.ties == ("peer-a", "peer-b")
    assert result.lead_lag_status == "insufficient_data"
    assert ("missing", "missing or insufficient momentum history") in result.excluded_peers


def test_peer_leadership_uses_only_the_momentum_snapshot_date():
    prices = _prices("selected", 0.01) + _prices("peer", 0.02) + [PriceObservation("peer", date(2026, 2, 1), 10_000, 100)]
    momentum = calculate_momentum("selected", prices, peer_entities=("peer",), as_of=date(2026, 1, 30), return_windows=(5,), moving_average_windows=(3, 5), breadth_window=5)
    result = analyze_peer_leadership(momentum, window=5, minimum_peers=1)

    assert result.lead_lag_status == "ok"
    assert result.signal_values[0][1] < 1
