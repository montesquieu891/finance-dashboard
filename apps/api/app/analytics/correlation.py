from __future__ import annotations

import pandas as pd


def pairwise_correlation(returns_df: pd.DataFrame, lookback: int) -> pd.DataFrame:
    if lookback <= 1:
        raise ValueError("lookback must be greater than 1")
    if returns_df.empty:
        raise ValueError("returns_df is empty")

    sample = returns_df.tail(lookback).dropna(how="any")
    if sample.empty:
        raise ValueError("No overlapping rows for correlation calculation")
    return sample.corr()
