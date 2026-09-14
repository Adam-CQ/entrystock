from analytics.valuation import DCFInputs, calculate_dcf, calculate_dcf_sensitivity


def test_dcf_exposes_forecast_cash_flows_terminal_value_and_per_share_value():
    result = calculate_dcf(
        DCFInputs(
            forecast_years=2,
            revenue_growth=0.10,
            operating_margin=0.20,
            tax_rate=0.25,
            reinvestment_rate=0.30,
            discount_rate=0.10,
            terminal_growth=0.03,
            shares_outstanding=100,
            starting_revenue=1_000,
        )
    )

    assert result.valid
    assert [round(item.revenue, 2) for item in result.forecast] == [1100.0, 1210.0]
    assert result.forecast[0].free_cash_flow == 115.5
    assert result.terminal_value is not None
    assert result.terminal_present_value is not None
    assert result.per_share_value == result.enterprise_value / 100


def test_dcf_can_use_starting_free_cash_flow_and_period_specific_growth():
    result = calculate_dcf(
        DCFInputs(2, (0.10, 0.0), 0.2, 0.25, 0.3, 0.1, 0.03, 10, starting_free_cash_flow=100)
    )

    assert result.valid
    assert [item.free_cash_flow for item in result.forecast] == [110.00000000000001, 110.00000000000001]
    assert all(item.revenue is None for item in result.forecast)


def test_dcf_invalid_inputs_are_structured_and_do_not_produce_value():
    result = calculate_dcf(
        DCFInputs(2, 0.1, 0.2, 0.25, 0.3, 0.08, 0.08, 0, starting_revenue=100)
    )

    assert result.per_share_value is None
    assert "terminal_growth must be below discount_rate" in result.errors
    assert "shares_outstanding must be greater than zero" in result.errors


def test_dcf_requires_a_starting_cash_flow_or_revenue():
    result = calculate_dcf(DCFInputs(2, 0.1, 0.2, 0.25, 0.3, 0.1, 0.03, 10))

    assert result.errors == ("starting_revenue or starting_free_cash_flow is required",)


def test_dcf_sensitivity_reuses_engine_and_labels_base_case_and_units():
    inputs = DCFInputs(2, 0.10, 0.20, 0.25, 0.30, 0.10, 0.03, 100, starting_revenue=1_000)
    result = calculate_dcf_sensitivity(inputs, (0.09, 0.10), (0.02, 0.03))

    assert result.evaluable
    assert result.base_case == (0.10, 0.03)
    assert result.units == "currency/share"
    assert len(result.cells) == 4
    assert result.cell(0.10, 0.03).per_share_value == calculate_dcf(inputs).per_share_value


def test_dcf_sensitivity_marks_invalid_rate_growth_pairs_and_missing_inputs():
    inputs = DCFInputs(2, 0.10, 0.20, 0.25, 0.30, 0.10, 0.03, 100, starting_revenue=1_000)
    result = calculate_dcf_sensitivity(inputs, (0.08,), (0.08, 0.02))

    invalid = result.cell(0.08, 0.08)
    assert invalid.status == "not_evaluable"
    assert invalid.per_share_value is None
    assert "terminal_growth must be below discount_rate" in invalid.errors

    missing = calculate_dcf_sensitivity(DCFInputs(2, 0.1, 0.2, 0.25, 0.3, 0.1, 0.03, 100), (0.1,), (0.03,))
    assert missing.evaluable is False
    assert missing.cells == ()
    assert "insufficient DCF inputs" in missing.errors[0]
