from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def _apply_max_weight_cap(
    raw_weights: pd.Series,
    gross_exposure: float,
    max_weight_multiplier: float = 5.0,
) -> pd.Series:
    if raw_weights.empty:
        raise ValueError("raw_weights is empty")
    if gross_exposure <= 0:
        raise ValueError("gross_exposure must be > 0")

    weights = raw_weights.clip(lower=0.0).astype(float)
    if float(weights.sum()) == 0.0:
        weights = pd.Series(1.0, index=raw_weights.index, dtype=float)

    target_sum = float(gross_exposure)
    cap = max_weight_multiplier * (target_sum / len(weights))

    scaled = weights / float(weights.sum()) * target_sum
    for _ in range(16):
        capped = scaled.clip(upper=cap)
        residual = target_sum - float(capped.sum())
        if residual <= 1e-12:
            scaled = capped
            break

        free_mask = capped < (cap - 1e-12)
        if not free_mask.any():
            scaled = capped
            break

        free_values = scaled[free_mask]
        if float(free_values.sum()) <= 1e-12:
            free_values = pd.Series(1.0, index=free_values.index, dtype=float)

        scaled = capped
        scaled.loc[free_mask] = (
            free_values / float(free_values.sum()) * residual + scaled.loc[free_mask]
        )

    normalized = scaled / float(scaled.sum()) * target_sum
    return normalized


def equal_weights(
    symbols: Iterable[str],
    gross_exposure: float = 1.0,
    max_weight_multiplier: float = 5.0,
) -> pd.Series:
    symbol_list = list(symbols)
    if not symbol_list:
        raise ValueError("At least one symbol is required")
    raw = pd.Series(1.0, index=symbol_list, dtype=float)
    return _apply_max_weight_cap(raw, gross_exposure, max_weight_multiplier)


def inverse_vol_weights(
    returns_df: pd.DataFrame,
    gross_exposure: float = 1.0,
    lookback: int | None = None,
    max_weight_multiplier: float = 5.0,
) -> pd.Series:
    sample = returns_df.tail(lookback) if lookback is not None else returns_df
    sample = sample.dropna(how="any")
    if sample.empty:
        raise ValueError("returns_df has no overlapping rows")

    vol = sample.std(ddof=0)
    raw = 1.0 / vol.replace(0.0, np.nan)
    raw = raw.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if float(raw.sum()) == 0.0:
        raw = pd.Series(1.0, index=sample.columns, dtype=float)

    return _apply_max_weight_cap(raw, gross_exposure, max_weight_multiplier)


def inverse_corr_weights(
    returns_df: pd.DataFrame,
    gross_exposure: float = 1.0,
    lookback: int | None = None,
    max_weight_multiplier: float = 5.0,
) -> pd.Series:
    sample = returns_df.tail(lookback) if lookback is not None else returns_df
    sample = sample.dropna(how="any")
    if sample.empty:
        raise ValueError("returns_df has no overlapping rows")

    n_assets = sample.shape[1]
    if n_assets == 1:
        return equal_weights(sample.columns, gross_exposure, max_weight_multiplier)

    corr = sample.corr().abs()
    avg_abs_corr = (corr.sum(axis=1) - 1.0) / (n_assets - 1)
    raw = 1.0 / avg_abs_corr.clip(lower=1e-6)
    return _apply_max_weight_cap(raw, gross_exposure, max_weight_multiplier)


def risk_parity_weights(
    returns_df: pd.DataFrame,
    gross_exposure: float = 1.0,
    lookback: int | None = None,
    max_weight_multiplier: float = 5.0,
    max_iter: int = 500,
    tolerance: float = 1e-7,
) -> pd.Series:
    sample = returns_df.tail(lookback) if lookback is not None else returns_df
    sample = sample.dropna(how="any")
    if sample.empty:
        raise ValueError("returns_df has no overlapping rows")

    cov = sample.cov().to_numpy(dtype=float)
    n_assets = cov.shape[0]
    weight_vector = np.full(n_assets, 1.0 / n_assets, dtype=float)

    for _ in range(max_iter):
        marginal = cov @ weight_vector
        portfolio_var = float(weight_vector @ marginal)
        if portfolio_var <= 0.0:
            break

        contribution = weight_vector * marginal
        target = portfolio_var / n_assets
        if np.max(np.abs(contribution - target)) < tolerance:
            break

        safe_contribution = np.where(contribution <= 1e-12, 1e-12, contribution)
        weight_vector *= target / safe_contribution
        weight_vector = np.maximum(weight_vector, 1e-12)
        weight_vector /= float(weight_vector.sum())

    raw = pd.Series(weight_vector, index=sample.columns, dtype=float)
    return _apply_max_weight_cap(raw, gross_exposure, max_weight_multiplier)


def beta_adjusted_weights(
    returns_df: pd.DataFrame,
    benchmark_returns: pd.Series,
    gross_exposure: float = 1.0,
    lookback: int | None = None,
    max_weight_multiplier: float = 5.0,
) -> pd.Series:
    asset_sample = returns_df.tail(lookback) if lookback is not None else returns_df
    benchmark_sample = (
        benchmark_returns.tail(lookback) if lookback is not None else benchmark_returns
    )

    aligned = pd.concat(
        [asset_sample, benchmark_sample.rename("benchmark")],
        axis=1,
    ).dropna(how="any")
    if aligned.empty:
        raise ValueError("No overlapping dates between assets and benchmark")

    benchmark = aligned["benchmark"]
    variance = float(benchmark.var(ddof=0))
    if variance <= 1e-12:
        return equal_weights(returns_df.columns, gross_exposure, max_weight_multiplier)

    betas: dict[str, float] = {}
    for column in returns_df.columns:
        covariance = float(aligned[column].cov(benchmark, ddof=0))
        betas[column] = covariance / variance

    beta_series = pd.Series(betas, dtype=float)
    raw = 1.0 / beta_series.abs().clip(lower=1e-6)
    return _apply_max_weight_cap(raw, gross_exposure, max_weight_multiplier)
