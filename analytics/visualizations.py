"""Plotly-compatible chart payloads derived from existing analysis results.

This module deliberately contains no analytical formulas.  It converts the
typed valuation, forecast, and momentum results into JSON-safe figures and
explicit fallback states for the dashboard.
"""

from dataclasses import asdict
from typing import Any, Iterable


PLOTLY_JS_VERSION = "2.35.2"


def _chart(chart_id: str, title: str, *, units: str, as_of: str, source: str, data: list[dict[str, Any]], layout: dict[str, Any], message: str | None = None) -> dict[str, Any]:
    state = "ok" if data else "not_evaluable"
    return {"id": chart_id, "title": title, "state": state, "message": message or (None if data else "Not evaluable: required data is unavailable."), "source": source, "as_of": as_of, "units": units, "figure": {"data": data, "layout": {"title": {"text": f"{title} · {source} · as of {as_of}"}, "xaxis": {"title": "Date / scenario"}, "yaxis": {"title": units}, "legend": {"orientation": "h"}, "hovermode": "x unified", **layout}}}


def build_chart_payloads(*, sensitivity, historical, relative, forecasts, momentum, as_of: str, source: str = "fixture") -> tuple[dict[str, Any], ...]:
    """Build the five dashboard figures from already-computed result objects."""
    return (
        _dcf_chart(sensitivity, as_of, source),
        _historical_chart(historical, as_of, source),
        _peer_chart(relative, as_of, source),
        _forecast_chart(forecasts, as_of, source),
        _momentum_chart(momentum, as_of, source),
    )


def _dcf_chart(result, as_of: str, source: str) -> dict[str, Any]:
    data = [{"type": "heatmap", "x": [f"{rate:.1%}" for rate in result.terminal_growths], "y": [f"{rate:.1%}" for rate in result.discount_rates], "z": [[result.cell(rate, growth).per_share_value for growth in result.terminal_growths] for rate in result.discount_rates], "text": [[result.cell(rate, growth).status for growth in result.terminal_growths] for rate in result.discount_rates], "colorscale": "Blues", "colorbar": {"title": result.units}}] if result.evaluable else []
    return _chart("dcf-sensitivity", "DCF sensitivity", units=result.units, as_of=as_of, source=source, data=data, layout={"xaxis": {"title": "Terminal growth rate"}, "yaxis": {"title": "Discount rate"}}, message="Not evaluable: DCF inputs are invalid or incomplete." if not data else None)


def _historical_chart(result, as_of: str, source: str) -> dict[str, Any]:
    data = []
    for item in result.multiples:
        if item.historical_values:
            data.append({"type": "scatter", "mode": "lines+markers", "name": item.multiple, "x": list(item.valid_periods), "y": list(item.historical_values), "customdata": [item.units] * len(item.historical_values)})
    return _chart("historical-valuation", "Historical valuation bands", units="multiple / yield", as_of=result.current_observation_date or as_of, source=source, data=data, layout={"xaxis": {"title": "Observation date"}, "yaxis": {"title": "Multiple / yield"}}, message="Insufficient data: historical bands require valid periods." if not data else None)


def _peer_chart(result, as_of: str, source: str) -> dict[str, Any]:
    data = []
    for item in result.multiples:
        labels = [result.selected_company, *item.included_peers]
        values = [item.selected_value, *item.peer_values]
        if any(value is not None for value in values):
            data.append({"type": "bar", "name": item.multiple, "x": labels, "y": values, "text": [item.units] * len(values)})
    return _chart("peer-multiples", "Peer valuation multiples", units="multiple / yield", as_of=result.as_of or as_of, source=source, data=data, layout={"barmode": "group", "xaxis": {"title": "Company"}, "yaxis": {"title": "Multiple / yield"}}, message="Insufficient data: no comparable peer multiples are available." if not data else None)


def _forecast_chart(results: Iterable, as_of: str, source: str) -> dict[str, Any]:
    data = []
    for name in ("management", "consensus", "internal"):
        points = [(item.period, item.source_values[name].value) for item in results if item.source_values.get(name) and item.source_values[name].value is not None]
        if points:
            data.append({"type": "bar", "name": name.title(), "x": [point[0] for point in points], "y": [point[1] for point in points]})
    return _chart("forecast-divergence", "Forecast source divergence", units="source units", as_of=as_of, source=source, data=data, layout={"barmode": "group", "xaxis": {"title": "Forecast period"}, "yaxis": {"title": "Forecast value"}}, message="Insufficient data: fewer than one forecast source has a numeric value." if not data else None)


def _momentum_chart(result, as_of: str, source: str) -> dict[str, Any]:
    entities = [result.selected, *result.peers]
    data = []
    for entity in entities:
        signal = next((item for item in entity.signals if item.identifier == "return_21d"), None)
        if signal and signal.value is not None:
            data.append({"type": "bar", "name": entity.entity_id, "x": [entity.entity_id], "y": [signal.value], "text": [f"{signal.start_date} to {signal.end_date}"], "customdata": [[signal.start_date.isoformat(), signal.end_date.isoformat()]]})
    return _chart("company-peer-momentum", "Company versus peer momentum", units="21-day return", as_of=as_of, source=source, data=data, layout={"xaxis": {"title": "Entity"}, "yaxis": {"title": "Return"}}, message="Insufficient data: no entity has an evaluable 21-day return." if not data else None)
