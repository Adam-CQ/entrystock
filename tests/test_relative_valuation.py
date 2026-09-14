from analytics.valuation import RelativeValuationObservation, calculate_relative_valuation


def _observation(identifier, *, ev=1_000, market_cap=900, ebitda=100, earnings=50, revenue=500, fcf=40, currency="USD"):
    return RelativeValuationObservation(identifier, ev, market_cap, ebitda, earnings, revenue, fcf, currency, "2026-06-30", "fixture")


def test_relative_valuation_calculates_supported_multiples_and_preserves_coverage():
    selected = _observation("selected")
    peers = [_observation("peer-a", ev=800, market_cap=720), _observation("peer-b", ev=1_200, market_cap=1_080)]
    result = calculate_relative_valuation(selected, peers)

    assert result.peer_universe == ("peer-a", "peer-b")
    by_name = {item.multiple: item for item in result.multiples}
    assert by_name["ev_ebitda"].status == "selected"
    assert by_name["ev_ebitda"].selected_value == 10
    assert by_name["ev_ebitda"].peer_median == 10
    assert by_name["pe"].units == "multiple"
    assert by_name["fcf_yield"].units == "yield"
    assert by_name["ev_ebitda"].coverage == 2
    assert by_name["ev_ebitda"].source_dates == ("2026-06-30",)


def test_relative_valuation_suppresses_unprofitable_multiples_and_marks_missing_peers():
    selected = _observation("selected", ebitda=-1, earnings=0, fcf=-5)
    peers = [_observation("peer-a"), _observation("peer-b", currency="EUR"), _observation("peer-c", ebitda=None)]
    result = calculate_relative_valuation(selected, peers)
    by_name = {item.multiple: item for item in result.multiples}

    assert by_name["ev_ebitda"].status == "suppressed"
    assert by_name["pe"].status == "suppressed"
    assert by_name["fcf_yield"].status == "suppressed"
    assert by_name["ev_sales"].status == "selected"
    assert ("peer-b", "incompatible currency") in by_name["ev_sales"].excluded_peers
    assert ("peer-c", "missing or non-positive denominator") in by_name["ev_ebitda"].excluded_peers or by_name["ev_ebitda"].status == "suppressed"


def test_relative_valuation_reports_insufficient_peers_and_excludes_extreme_outlier():
    selected = _observation("selected")
    peers = [_observation("peer-a", ev=800), _observation("peer-b", ev=900), _observation("peer-c", ev=1_100), _observation("outlier", ev=100_000)]
    result = calculate_relative_valuation(selected, peers)
    ev = next(item for item in result.multiples if item.multiple == "ev_ebitda")

    assert ev.status == "selected"
    assert ev.outlier_peers == ("outlier",)
    assert ev.peer_median == 9

    insufficient = calculate_relative_valuation(selected, peers[:1])
    assert all(item.status in {"not_evaluable", "selected", "suppressed"} for item in insufficient.multiples)
    assert next(item for item in insufficient.multiples if item.multiple == "ev_ebitda").status == "not_evaluable"
