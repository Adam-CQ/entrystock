"""Presentation-ready recommendation dashboard data assembled from domain engines."""

from datetime import date

from analytics.forecasts import ForecastValue, compare_forecasts
from analytics.hard_rules import evaluate_hard_rules, price_not_more_than_fair_value_rule
from analytics.momentum import PriceObservation as MomentumPrice, calculate_momentum
from analytics.recommendations import Evidence, RecommendationInput, build_recommendation
from analytics.scoring import calculate_composite_score
from analytics.valuation import (
    DCFInputs,
    RelativeValuationObservation,
    calculate_dcf,
    calculate_dcf_sensitivity,
    calculate_historical_valuation,
    calculate_relative_valuation,
)
from analytics.visualizations import build_chart_payloads


def build_dashboard_context(company, proposal, peers, price_observations=()):
    """Return all sections needed by the PoC dashboard.

    The fixture has one price observation and one forecast source, so the
    engines intentionally return visible insufficient-data states for the
    missing series rather than inventing values.
    """
    as_of = _latest_date(company)
    selected_statement = _latest_statement(company)
    selected = _observation(company, selected_statement, as_of)
    peer_observations = tuple(_observation(peer, _latest_statement(peer), as_of) for peer in peers)

    dcf_inputs = DCFInputs(
        forecast_years=5, revenue_growth=0.10, operating_margin=0.08,
        tax_rate=0.21, reinvestment_rate=0.35, discount_rate=0.10,
        terminal_growth=0.03, shares_outstanding=10, starting_revenue=selected.revenue,
        source_period="FY2025 fixture statement",
    )
    dcf = calculate_dcf(dcf_inputs)
    sensitivity = calculate_dcf_sensitivity(dcf_inputs, (0.08, 0.10, 0.12), (0.02, 0.03, 0.04))
    fair_value = dcf.per_share_value
    fair_low = fair_value * 0.85 if fair_value is not None else None
    fair_high = fair_value * 1.15 if fair_value is not None else None
    current_price = _current_price(company, price_observations)

    score = calculate_composite_score({
        "valuation": _bounded((fair_high / current_price) if fair_high and current_price else None),
        "forecasts": None,
        "momentum": None,
        "quality": 0.75,
        "catalysts": 0.50,
        "risk": 0.50,
    })
    weighted_rating = "ENTRY" if score.aggregate_score is not None and score.aggregate_score >= 0.75 else "WATCH"
    rules = evaluate_hard_rules((price_not_more_than_fair_value_rule(),), {"price": current_price, "fair_value": fair_high}, weighted_rating)
    recommendation = build_recommendation(RecommendationInput(
        weighted_rating=weighted_rating, current_price=current_price,
        fair_value_low=fair_low, fair_value_high=fair_high,
        expected_return=(fair_high / current_price - 1) if fair_high and current_price else None,
        entry_zone_low=fair_low * 0.90 if fair_low else None,
        entry_zone_high=fair_high if fair_high else None,
        confidence=score.confidence, score=score, hard_rules=rules,
        positive_drivers=(Evidence("operating margin", "8%", "FY2025 fixture statement", as_of.isoformat(), "DCF base case"),),
        negative_drivers=(Evidence("forecast coverage", "1 of 3 sources", "fixture provider", as_of.isoformat()),),
        catalysts=(Evidence("nuclear energy exposure", "present", "fixture classification", as_of.isoformat()),),
        risks=(Evidence("limited price history", "1 observation", "fixture market data", as_of.isoformat()),),
        data_quality_limitations=("management and consensus forecasts are unavailable in the fixture", "price history has one observation"),
        uncertainty=("forecast-source divergence cannot yet be measured",), source="fixture", as_of=as_of.isoformat(),
    ))

    forecast_values = _forecast_values(company, as_of)
    forecasts = compare_forecasts(forecast_values, as_of=as_of)
    selected_identifier = company.securities.first().security_identifier
    prices = tuple(MomentumPrice(selected_identifier, item.trading_date, float(item.adjusted_close or item.close), float(item.volume) if item.volume is not None else None) for item in price_observations)
    momentum = calculate_momentum(selected_identifier, prices, peer_entities=tuple(peer.securities.first().security_identifier for peer in peers), as_of=as_of)
    relative = calculate_relative_valuation(selected, peer_observations)
    historical = calculate_historical_valuation(selected, tuple(_observation(company, statement, as_of) for statement in company.incomestatement_set.order_by("reporting_period__period_end")))
    charts = build_chart_payloads(sensitivity=sensitivity, historical=historical, relative=relative, forecasts=forecasts, momentum=momentum, as_of=as_of.isoformat())

    return {
        "as_of": as_of, "selected_company": company, "proposal": proposal,
        "peers": peers, "recommendation": recommendation, "score": score,
        "dcf": dcf, "sensitivity": sensitivity, "relative_valuation": relative,
        "historical_valuation": historical, "forecasts": forecasts, "momentum": momentum,
        "current_price": current_price, "assumptions": dcf_inputs,
        "chart_payloads": charts,
    }


def _latest_date(company):
    statement = _latest_statement(company)
    return statement.effective_date if statement else date.today()


def _latest_statement(company):
    return company.incomestatement_set.order_by("reporting_period__period_end").last()


def _observation(company, statement, as_of):
    revenue = float(statement.revenue) if statement and statement.revenue is not None else None
    earnings = float(statement.net_income) if statement and statement.net_income is not None else None
    return RelativeValuationObservation(company.common_name, 1000.0 if revenue else None, 1000.0 if revenue else None, float(statement.operating_income) if statement and statement.operating_income is not None else None, earnings, revenue, earnings, "USD", str(statement.effective_date if statement else as_of), "fixture")


def _current_price(company, observations):
    item = next((item for item in observations if item.security_id == company.securities.first().id), None)
    return float(item.adjusted_close or item.close) if item else None


def _forecast_values(company, as_of):
    forecast = company.forecasts.select_related("measure", "period").first()
    if forecast:
        return (ForecastValue("management", forecast.measure.code, forecast.period.label, float(forecast.value) if forecast.value is not None else None, forecast.units, forecast.retrieved_at, forecast.effective_date),)
    return ()


def _bounded(value):
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))
