from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
import pandas as pd
from numpy.typing import NDArray


def _to_float_array(series: pd.Series) -> NDArray[np.float64]:
    numeric = pd.to_numeric(series, errors="coerce")
    return np.asarray(numeric.to_numpy(dtype=float), dtype=float)


def cumulative_index(returns: pd.Series, start_value: float = 100.0) -> pd.Series:
    values = _to_float_array(returns)
    if values.size == 0:
        raise ValueError("returns is empty")

    indexed = np.cumprod(1.0 + values) * start_value
    return pd.Series(indexed, index=returns.index)


def annualized_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    values = _to_float_array(returns)
    if values.size == 0:
        return 0.0
    return float(np.std(values, ddof=0) * math.sqrt(periods_per_year))


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    values = _to_float_array(returns)
    if values.size == 0:
        return 0.0

    excess = values - (risk_free_rate / periods_per_year)
    denominator = float(np.std(excess, ddof=0))
    if denominator <= 1e-12:
        return 0.0
    return float(np.mean(excess) / denominator * math.sqrt(periods_per_year))


def max_drawdown(returns: pd.Series) -> float:
    values = _to_float_array(returns)
    if values.size == 0:
        return 0.0

    index_level = np.cumprod(1.0 + values) * 100.0
    running_peak = np.maximum.accumulate(index_level)
    drawdown = (running_peak - index_level) / running_peak
    return float(np.max(drawdown))


def calmar_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    values = _to_float_array(returns)
    if values.size == 0:
        return 0.0

    total_periods = values.size
    total_return = float(np.prod(1.0 + values) - 1.0)
    annualized_return = (1.0 + total_return) ** (periods_per_year / total_periods) - 1.0
    mdd = max_drawdown(returns)
    if mdd <= 1e-12:
        return 0.0
    return float(annualized_return / mdd)


def sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    values = _to_float_array(returns)
    if values.size == 0:
        return 0.0

    target_daily = risk_free_rate / periods_per_year
    downside = values[values < target_daily] - target_daily
    if downside.size == 0:
        return 0.0

    downside_dev = float(np.std(downside, ddof=0))
    if downside_dev <= 1e-12:
        return 0.0

    excess_return = float(np.mean(values - target_daily))
    return float(excess_return / downside_dev * math.sqrt(periods_per_year))


def beta(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    aligned = pd.concat([returns.rename("basket"), benchmark_returns.rename("benchmark")], axis=1)
    aligned = aligned.dropna(how="any")
    if aligned.empty:
        return 0.0

    basket = _to_float_array(aligned["basket"])
    benchmark = _to_float_array(aligned["benchmark"])

    variance = float(np.var(benchmark, ddof=0))
    if variance <= 1e-12:
        return 0.0

    covariance_matrix = np.cov(basket, benchmark, ddof=0)
    covariance = float(covariance_matrix[0, 1])
    return covariance / variance


def net_exposure(signed_weights: Mapping[str, float]) -> float:
    return float(sum(signed_weights.values()))


def gross_exposure(signed_weights: Mapping[str, float]) -> float:
    return float(sum(abs(weight) for weight in signed_weights.values()))


def tracking_error(
    returns: pd.Series,
    benchmark_returns: pd.Series,
    periods_per_year: int = 252,
) -> float:
    aligned = pd.concat([returns.rename("basket"), benchmark_returns.rename("benchmark")], axis=1)
    aligned = aligned.dropna(how="any")
    if aligned.empty:
        return 0.0

    basket = _to_float_array(aligned["basket"])
    benchmark = _to_float_array(aligned["benchmark"])
    active = basket - benchmark
    return float(np.std(active, ddof=0) * math.sqrt(periods_per_year))


def vs_benchmark_total_return(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    aligned = pd.concat([returns.rename("basket"), benchmark_returns.rename("benchmark")], axis=1)
    aligned = aligned.dropna(how="any")
    if aligned.empty:
        return 0.0

    basket = _to_float_array(aligned["basket"])
    benchmark = _to_float_array(aligned["benchmark"])

    basket_total = float(np.prod(1.0 + basket) - 1.0)
    benchmark_total = float(np.prod(1.0 + benchmark) - 1.0)
    return basket_total - benchmark_total


def compute_risk_metrics(
    returns: pd.Series,
    signed_weights: Mapping[str, float],
    benchmark_returns: pd.Series | None = None,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> dict[str, float]:
    return_values = _to_float_array(returns)
    total_return = float(np.prod(1.0 + return_values) - 1.0) if return_values.size > 0 else 0.0

    metrics: dict[str, float] = {
        "ann_vol": annualized_volatility(returns, periods_per_year),
        "sharpe": sharpe_ratio(returns, risk_free_rate, periods_per_year),
        "max_drawdown": max_drawdown(returns),
        "calmar": calmar_ratio(returns, periods_per_year),
        "sortino": sortino_ratio(returns, risk_free_rate, periods_per_year),
        "net_exposure": net_exposure(signed_weights),
        "gross_exposure": gross_exposure(signed_weights),
        "total_return": total_return,
    }

    if benchmark_returns is not None:
        metrics["beta"] = beta(returns, benchmark_returns)
        metrics["vs_benchmark"] = vs_benchmark_total_return(returns, benchmark_returns)
        metrics["tracking_error"] = tracking_error(returns, benchmark_returns, periods_per_year)
    else:
        metrics["beta"] = 0.0
        metrics["vs_benchmark"] = 0.0
        metrics["tracking_error"] = 0.0

    return metrics
