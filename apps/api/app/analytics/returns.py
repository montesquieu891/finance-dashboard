from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict

import pandas as pd


class BasketLeg(TypedDict):
    symbol: str
    side: Literal["long", "short"]
    currency: str


def align_trading_calendar(returns_df: pd.DataFrame) -> pd.DataFrame:
    if returns_df.empty:
        raise ValueError("returns_df is empty")
    aligned = returns_df.dropna(how="any")
    if aligned.empty:
        raise ValueError("No overlapping dates remain after calendar alignment")
    return aligned


def convert_returns_to_base_currency(
    returns_df: pd.DataFrame,
    instrument_currency: Mapping[str, str],
    fx_returns_df: pd.DataFrame,
    base_currency: str = "USD",
) -> pd.DataFrame:
    converted = returns_df.copy()
    for symbol in converted.columns:
        currency = instrument_currency.get(symbol, base_currency)
        if currency == base_currency:
            continue
        if currency not in fx_returns_df.columns:
            raise ValueError(f"Missing FX return series for currency={currency}")
        fx_series = fx_returns_df[currency]
        converted[symbol] = (1.0 + converted[symbol]).mul(1.0 + fx_series, fill_value=pd.NA) - 1.0

    return align_trading_calendar(converted)


def leg_contributions(
    legs: Sequence[Mapping[str, str]],
    weights: Mapping[str, float],
    returns_df: pd.DataFrame,
) -> pd.DataFrame:
    if not legs:
        raise ValueError("At least one leg is required")

    leg_symbols = [leg["symbol"] for leg in legs]
    missing_symbols = [symbol for symbol in leg_symbols if symbol not in returns_df.columns]
    if missing_symbols:
        raise ValueError(f"Missing return series for symbols: {missing_symbols}")

    missing_weights = [symbol for symbol in leg_symbols if symbol not in weights]
    if missing_weights:
        raise ValueError(f"Missing weights for symbols: {missing_weights}")

    aligned = align_trading_calendar(returns_df[leg_symbols])
    contribution_frame = pd.DataFrame(index=aligned.index)

    for leg in legs:
        symbol = leg["symbol"]
        side = leg["side"]
        side_multiplier = 1.0 if side == "long" else -1.0
        contribution_frame[symbol] = aligned[symbol] * float(weights[symbol]) * side_multiplier

    return contribution_frame


def basket_returns(
    legs: Sequence[Mapping[str, str]],
    weights: Mapping[str, float],
    returns_df: pd.DataFrame,
) -> pd.Series:
    contributions = leg_contributions(legs=legs, weights=weights, returns_df=returns_df)
    return contributions.sum(axis=1).rename("basket_return")
