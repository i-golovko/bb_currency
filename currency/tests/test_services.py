from decimal import Decimal

import pytest

from currency.services import calculate_twrr


def test_calculate_twrr():
    # Test with normal case
    historical_rates = [
        {"valuation_date": "2021-01-01", "rate_value": Decimal(1.00)},
        {"valuation_date": "2021-01-02", "rate_value": Decimal(1.05)},
        {"valuation_date": "2021-01-03", "rate_value": Decimal(1.10)},
    ]
    amount = Decimal(1000)
    result = calculate_twrr(historical_rates, amount)
    assert result[0]["date"] == "2021-01-02"
    assert result[0]["rate_value"] == Decimal(1.05)
    assert result[0]["twrr"] == Decimal(1050)
    assert result[1]["date"] == "2021-01-03"
    assert result[1]["rate_value"] == Decimal(1.10)
    assert result[1]["twrr"] == Decimal(1100)

    # Test with empty historical_rates
    empty_result = calculate_twrr([], amount)
    assert empty_result == []

    # Test with one historical_rate
    single_result = calculate_twrr(
        [{"valuation_date": "2021-01-01", "rate_value": Decimal(1.00)}], amount
    )
    assert single_result == []

    # Test with zero rate_value
    historical_rates = [
        {"valuation_date": "2021-01-01", "rate_value": Decimal(0)},
        {"valuation_date": "2021-01-02", "rate_value": Decimal(1.0)},
    ]
    with pytest.raises(ZeroDivisionError):
        calculate_twrr(historical_rates, amount)
