from analytics.valuation import DCFInputs, calculate_dcf


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
