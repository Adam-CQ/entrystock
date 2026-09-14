from datetime import date, timedelta

from analytics.momentum import PriceObservation, calculate_momentum


def _prices(entity, count=70, slope=0.01, volume=100):
    start = date(2026, 1, 1)
    return [PriceObservation(entity, start + timedelta(days=index), 100 * (1 + slope) ** index, volume) for index in range(count)]


def test_momentum_returns_indicators_dates_units_relative_strength_and_breadth():
    prices = _prices("selected", slope=0.02) + _prices("peer-a", slope=0.01) + _prices("peer-b", slope=-0.01)
    result = calculate_momentum("selected", prices, peer_entities=("peer-a", "peer-b"), industry_entities=("peer-a",), as_of=date(2026, 3, 11), return_windows=(5, 20), moving_average_windows=(5, 10), breadth_window=5)

    selected = {signal.identifier: signal for signal in result.selected.signals}
    assert selected["return_5d"].value > 0
    assert selected["return_5d"].start_date < selected["return_5d"].end_date
    assert selected["return_5d"].units == "return"
    assert selected["moving_average_relationship"].status == "ok"
    assert selected["relative_strength_5d"].value > 0
    up = next(item for item in result.peer_breadth if item.direction == "up")
    assert up.eligible_entities == ("peer-a", "peer-b")
    assert up.proportion == 0.5
    assert "probabilistic" in result.probabilistic_notice


def test_momentum_excludes_future_prices_and_marks_short_or_zero_volume_history():
    prices = [PriceObservation(item.entity_id, item.trading_date, item.adjusted_close, 0) for item in _prices("selected", count=10)] + [PriceObservation("selected", date(2026, 3, 20), 999, 999)]
    result = calculate_momentum("selected", prices, as_of=date(2026, 1, 10), return_windows=(5,), moving_average_windows=(3, 5))
    signals = {signal.identifier: signal for signal in result.selected.signals}

    assert result.selected.observation_count == 10
    assert signals["return_5d"].status == "ok"
    assert signals["return_5d"].end_date == date(2026, 1, 10)
    assert signals["volume_confirmation"].status == "not_evaluable"

    short = calculate_momentum("missing", [], as_of=date(2026, 1, 10), return_windows=(5,))
    assert all(signal.status == "not_evaluable" for signal in short.selected.signals)
    assert all(item.status == "not_evaluable" for item in short.peer_breadth)
