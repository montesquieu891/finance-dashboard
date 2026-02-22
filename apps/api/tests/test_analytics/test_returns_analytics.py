import pandas as pd

from app.analytics.returns import (
    align_trading_calendar,
    basket_returns,
    convert_returns_to_base_currency,
    leg_contributions,
)


def test_short_leg_sign_flip_is_explicit() -> None:
    index = pd.to_datetime(["2025-01-01", "2025-01-02"])
    returns_df = pd.DataFrame(
        {
            "SPY": [0.02, -0.01],
            "GLD": [0.01, 0.03],
        },
        index=index,
    )
    legs = [
        {"symbol": "SPY", "side": "long", "currency": "USD"},
        {"symbol": "GLD", "side": "short", "currency": "USD"},
    ]
    weights = {"SPY": 1.0, "GLD": 1.0}

    contribution_frame = leg_contributions(legs=legs, weights=weights, returns_df=returns_df)

    assert contribution_frame.loc[index[0], "SPY"] == 0.02
    assert contribution_frame.loc[index[0], "GLD"] == -0.01
    assert contribution_frame.loc[index[1], "GLD"] == -0.03


def test_basket_returns_sum_contributions() -> None:
    index = pd.to_datetime(["2025-01-01", "2025-01-02"])
    returns_df = pd.DataFrame(
        {
            "SPY": [0.01, 0.02],
            "GLD": [0.005, -0.01],
        },
        index=index,
    )
    legs = [
        {"symbol": "SPY", "side": "long", "currency": "USD"},
        {"symbol": "GLD", "side": "short", "currency": "USD"},
    ]
    weights = {"SPY": 0.6, "GLD": 0.4}

    series = basket_returns(legs=legs, weights=weights, returns_df=returns_df)

    assert series.name == "basket_return"
    assert series.tolist() == [0.004, 0.016]


def test_calendar_alignment_uses_intersection() -> None:
    index = pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"])
    frame = pd.DataFrame({"A": [0.01, None, 0.02], "B": [0.03, 0.01, None]}, index=index)

    aligned = align_trading_calendar(frame)

    assert aligned.index.tolist() == [index[0]]


def test_fx_conversion_is_applied_before_weighting() -> None:
    index = pd.to_datetime(["2025-01-01", "2025-01-02"])
    local_returns = pd.DataFrame({"BMW": [0.01, 0.00], "SPY": [0.00, 0.01]}, index=index)
    instrument_currency = {"BMW": "EUR", "SPY": "USD"}
    fx_returns = pd.DataFrame({"EUR": [0.02, -0.01]}, index=index)

    converted = convert_returns_to_base_currency(
        returns_df=local_returns,
        instrument_currency=instrument_currency,
        fx_returns_df=fx_returns,
        base_currency="USD",
    )

    expected_bmw_day1 = (1.01 * 1.02) - 1.0
    expected_bmw_day2 = (1.00 * 0.99) - 1.0
    assert round(float(converted.loc[index[0], "BMW"]), 8) == round(expected_bmw_day1, 8)
    assert round(float(converted.loc[index[1], "BMW"]), 8) == round(expected_bmw_day2, 8)
