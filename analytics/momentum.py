"""Deterministic, point-in-time momentum indicators.

Signals are descriptive features, not forecasts. All calculations use
adjusted closes and observations available on or before ``as_of``.
"""

from dataclasses import dataclass
from datetime import date
from math import isfinite, sqrt
from statistics import mean, median, stdev
from typing import Sequence


@dataclass(frozen=True)
class PriceObservation:
    entity_id: str
    trading_date: date
    adjusted_close: float | None
    volume: float | None


@dataclass(frozen=True)
class MomentumSignal:
    identifier: str
    value: float | None
    lookback_days: int
    start_date: date | None = None
    end_date: date | None = None
    units: str = "unitless"
    status: str = "ok"
    coverage: int = 0
    explanation: str = ""


@dataclass(frozen=True)
class MomentumEntityResult:
    entity_id: str
    signals: tuple[MomentumSignal, ...]
    observation_count: int
    as_of: date


@dataclass(frozen=True)
class PeerBreadth:
    direction: str
    supporting_entities: tuple[str, ...]
    eligible_entities: tuple[str, ...]
    proportion: float | None
    lookback_days: int
    status: str
    explanation: str


@dataclass(frozen=True)
class MomentumResult:
    selected: MomentumEntityResult
    peers: tuple[MomentumEntityResult, ...]
    industry: tuple[MomentumEntityResult, ...]
    peer_breadth: tuple[PeerBreadth, ...]
    as_of: date
    probabilistic_notice: str = "Momentum and peer-leadership signals are probabilistic indicators, not predictive guarantees."


DEFAULT_RETURN_WINDOWS = (21, 63, 126, 252)


def calculate_momentum(
    selected_entity: str,
    prices: Sequence[PriceObservation],
    *,
    peer_entities: Sequence[str] = (),
    industry_entities: Sequence[str] = (),
    as_of: date,
    return_windows: Sequence[int] = DEFAULT_RETURN_WINDOWS,
    moving_average_windows: tuple[int, int] = (20, 50),
    breadth_window: int = 21,
) -> MomentumResult:
    """Calculate selected-company, peer, industry, and breadth signals."""

    windows = tuple(int(window) for window in return_windows)
    if not windows or any(window < 1 for window in windows):
        raise ValueError("return_windows must contain positive integers")
    if len(moving_average_windows) != 2 or any(window < 1 for window in moving_average_windows):
        raise ValueError("moving_average_windows must contain two positive integers")
    if breadth_window < 1:
        raise ValueError("breadth_window must be positive")
    grouped = _group_prices(prices, as_of)
    selected = _entity_result(selected_entity, grouped.get(selected_entity, ()), windows, moving_average_windows)
    peers = tuple(_entity_result(entity, grouped.get(entity, ()), windows, moving_average_windows) for entity in dict.fromkeys(peer_entities) if entity != selected_entity)
    industry = tuple(_entity_result(entity, grouped.get(entity, ()), windows, moving_average_windows) for entity in dict.fromkeys(industry_entities) if entity != selected_entity)
    _add_relative_strength(selected, peers, windows)
    peer_breadth = tuple(_breadth(peers, breadth_window, direction) for direction in ("up", "down"))
    return MomentumResult(selected, peers, industry, peer_breadth, as_of)


def _group_prices(prices: Sequence[PriceObservation], as_of: date) -> dict[str, tuple[PriceObservation, ...]]:
    grouped: dict[str, dict[date, PriceObservation]] = {}
    for observation in prices:
        if observation.trading_date <= as_of:
            grouped.setdefault(observation.entity_id, {})[observation.trading_date] = observation
    return {entity: tuple(sorted(by_date.values(), key=lambda item: item.trading_date)) for entity, by_date in grouped.items()}


def _entity_result(entity: str, observations: Sequence[PriceObservation], return_windows: Sequence[int], moving_average_windows: tuple[int, int]) -> MomentumEntityResult:
    signals = [_return_signal(observations, window) for window in return_windows]
    fast, slow = moving_average_windows
    signals.extend((_moving_average_signal(observations, fast, slow), _volatility_signal(observations, min(return_windows)), _volume_signal(observations, min(return_windows))))
    as_of = observations[-1].trading_date if observations else date.min
    return MomentumEntityResult(entity, tuple(signals), len(observations), as_of)


def _return_signal(observations: Sequence[PriceObservation], window: int) -> MomentumSignal:
    identifier = f"return_{window}d"
    usable = [item for item in observations if _valid_price(item.adjusted_close)]
    if len(usable) < window + 1:
        return MomentumSignal(identifier, None, window, _first_date(usable), _last_date(usable), "return", "not_evaluable", len(usable), "not evaluable: insufficient adjusted-price observations")
    start, end = usable[-window - 1], usable[-1]
    value = float(end.adjusted_close) / float(start.adjusted_close) - 1
    return MomentumSignal(identifier, value, window, start.trading_date, end.trading_date, "return", "ok", window + 1, "adjusted-price total return")


def _moving_average_signal(observations: Sequence[PriceObservation], fast: int, slow: int) -> MomentumSignal:
    lookback = max(fast, slow)
    usable = [item for item in observations if _valid_price(item.adjusted_close)]
    if len(usable) < lookback:
        return MomentumSignal("moving_average_relationship", None, lookback, _first_date(usable), _last_date(usable), "ratio", "not_evaluable", len(usable), "not evaluable: insufficient adjusted-price observations")
    fast_average = mean(float(item.adjusted_close) for item in usable[-fast:])
    slow_average = mean(float(item.adjusted_close) for item in usable[-slow:])
    value = fast_average / slow_average - 1 if slow_average else None
    return MomentumSignal("moving_average_relationship", value, lookback, usable[-lookback].trading_date, usable[-1].trading_date, "ratio", "ok" if value is not None else "not_evaluable", lookback, f"{fast}d average relative to {slow}d average")


def _volatility_signal(observations: Sequence[PriceObservation], window: int) -> MomentumSignal:
    usable = [float(item.adjusted_close) for item in observations if _valid_price(item.adjusted_close)]
    if len(usable) < window + 1:
        return MomentumSignal("volatility", None, window, _first_date(observations), _last_date(observations), "annualized standard deviation", "not_evaluable", len(usable), "not evaluable: insufficient adjusted-price observations")
    returns = [usable[index] / usable[index - 1] - 1 for index in range(len(usable) - window, len(usable))]
    value = stdev(returns) * sqrt(252) if len(returns) > 1 else 0.0
    return MomentumSignal("volatility", value, window, _first_date(observations[-window - 1:]), _last_date(observations), "annualized standard deviation", "ok", len(returns) + 1, "annualized daily adjusted-price volatility")


def _volume_signal(observations: Sequence[PriceObservation], window: int) -> MomentumSignal:
    usable = [item for item in observations if item.volume is not None and _finite(item.volume) and item.volume >= 0]
    if len(usable) < window * 2:
        return MomentumSignal("volume_confirmation", None, window, _first_date(usable), _last_date(usable), "volume ratio", "not_evaluable", len(usable), "not evaluable: insufficient volume observations")
    recent = mean(float(item.volume) for item in usable[-window:])
    prior = mean(float(item.volume) for item in usable[-window * 2:-window])
    value = recent / prior if prior else None
    status = "ok" if value is not None else "not_evaluable"
    explanation = "recent average volume divided by prior average volume" if value is not None else "not evaluable: prior volume is zero"
    return MomentumSignal("volume_confirmation", value, window, usable[-window * 2].trading_date, usable[-1].trading_date, "volume ratio", status, window * 2, explanation)


def _breadth(peers: Sequence[MomentumEntityResult], window: int, direction: str) -> PeerBreadth:
    signal_name = f"return_{window}d"
    eligible, supporting = [], []
    for peer in peers:
        signal = next((item for item in peer.signals if item.identifier == signal_name), None)
        if signal is not None and signal.value is not None:
            eligible.append(peer.entity_id)
            if (signal.value >= 0 if direction == "up" else signal.value < 0):
                supporting.append(peer.entity_id)
    if not eligible:
        return PeerBreadth(direction, (), (), None, window, "not_evaluable", "no peers have evaluable breadth data")
    return PeerBreadth(direction, tuple(supporting), tuple(eligible), len(supporting) / len(eligible), window, "ok", "peer breadth is the proportion supporting this direction")


def _add_relative_strength(selected: MomentumEntityResult, peers: Sequence[MomentumEntityResult], windows: Sequence[int]) -> None:
    for window in windows:
        name = f"return_{window}d"
        selected_signal = next(item for item in selected.signals if item.identifier == name)
        peer_values = [signal.value for peer in peers for signal in peer.signals if signal.identifier == name and signal.value is not None]
        if selected_signal.value is None or not peer_values:
            signal = MomentumSignal(f"relative_strength_{window}d", None, window, selected_signal.start_date, selected_signal.end_date, "return spread", "not_evaluable", selected_signal.coverage, "not evaluable: selected or peer return is missing")
        else:
            signal = MomentumSignal(f"relative_strength_{window}d", selected_signal.value - median(peer_values), window, selected_signal.start_date, selected_signal.end_date, "return spread", "ok", len(peer_values), "selected-company return minus peer median return")
        object.__setattr__(selected, "signals", selected.signals + (signal,))


def _valid_price(value: object) -> bool:
    try:
        return isfinite(float(value)) and float(value) > 0
    except (TypeError, ValueError):
        return False


def _finite(value: object) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _first_date(observations: Sequence[PriceObservation]) -> date | None:
    return observations[0].trading_date if observations else None


def _last_date(observations: Sequence[PriceObservation]) -> date | None:
    return observations[-1].trading_date if observations else None


MomentumAnalysis = MomentumResult
build_momentum = calculate_momentum


@dataclass(frozen=True)
class PeerLeadershipResult:
    window: int
    leaders: tuple[str, ...]
    laggards: tuple[str, ...]
    ties: tuple[str, ...]
    signal_values: tuple[tuple[str, float], ...]
    included_peers: tuple[str, ...]
    excluded_peers: tuple[tuple[str, str], ...]
    lead_lag_value: float | None
    lead_lag_status: str
    lead_lag_explanation: str
    probabilistic_notice: str = "Peer-leadership signals are probabilistic indicators, not predictive guarantees."


def analyze_peer_leadership(
    momentum: MomentumResult,
    *,
    window: int = 21,
    minimum_peers: int = 3,
) -> PeerLeadershipResult:
    """Identify peer leaders/laggards from a point-in-time momentum snapshot.

    The lead-lag feature is a cautious cross-sectional spread: peer median
    return minus selected-company return. It is withheld unless the minimum
    number of peers has evaluable data.
    """

    if window < 1 or minimum_peers < 1:
        raise ValueError("window and minimum_peers must be positive")
    identifier = f"return_{window}d"
    values: list[tuple[str, float]] = []
    excluded: list[tuple[str, str]] = []
    for peer in momentum.peers:
        signal = next((item for item in peer.signals if item.identifier == identifier), None)
        if signal is None:
            excluded.append((peer.entity_id, "momentum window is not configured"))
        elif signal.value is None:
            excluded.append((peer.entity_id, "missing or insufficient momentum history"))
        elif signal.end_date is None or signal.end_date > momentum.as_of:
            excluded.append((peer.entity_id, "observation is after analysis date"))
        else:
            values.append((peer.entity_id, signal.value))
    values.sort(key=lambda item: (-item[1], item[0]))
    included = tuple(identifier for identifier, _ in values)
    if not values:
        return PeerLeadershipResult(window, (), (), (), (), (), tuple(excluded), None, "not_evaluable", "no peers have evaluable point-in-time momentum data")
    highest, lowest = values[0][1], values[-1][1]
    leaders = tuple(identifier for identifier, value in values if value == highest)
    laggards = tuple(identifier for identifier, value in values if value == lowest)
    ties = tuple(identifier for identifier, value in values if sum(item_value == value for _, item_value in values) > 1)
    selected_signal = next((item for item in momentum.selected.signals if item.identifier == identifier), None)
    if len(values) < minimum_peers or selected_signal is None or selected_signal.value is None:
        lead_lag_value = None
        lead_lag_status = "insufficient_data"
        lead_lag_explanation = f"lead-lag feature requires {minimum_peers} peers and an evaluable selected-company return"
    else:
        lead_lag_value = median(value for _, value in values) - selected_signal.value
        lead_lag_status = "ok"
        lead_lag_explanation = "peer median return minus selected-company return at the same point-in-time window"
    return PeerLeadershipResult(window, leaders, laggards, ties, tuple(values), included, tuple(excluded), lead_lag_value, lead_lag_status, lead_lag_explanation)


PeerLeaderLaggardAnalysis = PeerLeadershipResult
build_peer_leadership = analyze_peer_leadership
identify_peer_leaders_and_laggards = analyze_peer_leadership
