from __future__ import annotations

import math
from collections.abc import Mapping

import pandas as pd


def cumulative_index(returns: pd.Series, start_value: float = 100.0) -> pd.Series:
	if returns.empty:
		raise ValueError("returns is empty")
	return (1.0 + returns).cumprod() * start_value


def annualized_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
	if returns.empty:
		return 0.0
	return float(returns.std(ddof=0) * math.sqrt(periods_per_year))


def sharpe_ratio(
	returns: pd.Series,
	risk_free_rate: float = 0.0,
	periods_per_year: int = 252,
) -> float:
	if returns.empty:
		return 0.0
	excess = returns - (risk_free_rate / periods_per_year)
	denominator = float(excess.std(ddof=0))
	if denominator <= 1e-12:
		return 0.0
	return float(excess.mean() / denominator * math.sqrt(periods_per_year))


def max_drawdown(returns: pd.Series) -> float:
	if returns.empty:
		return 0.0
	index_level = cumulative_index(returns, start_value=100.0)
	running_peak = index_level.cummax()
	drawdown = (running_peak - index_level) / running_peak
	return float(drawdown.max())


def calmar_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
	if returns.empty:
		return 0.0
	total_periods = len(returns)
	if total_periods == 0:
		return 0.0
	total_return = float((1.0 + returns).prod() - 1.0)
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
	if returns.empty:
		return 0.0
	target_daily = risk_free_rate / periods_per_year
	downside = returns[returns < target_daily] - target_daily
	downside_dev = float(downside.std(ddof=0)) if not downside.empty else 0.0
	if downside_dev <= 1e-12:
		return 0.0
	excess_return = float((returns - target_daily).mean())
	return float(excess_return / downside_dev * math.sqrt(periods_per_year))


def beta(returns: pd.Series, benchmark_returns: pd.Series) -> float:
	aligned = pd.concat([returns.rename("basket"), benchmark_returns.rename("benchmark")], axis=1)
	aligned = aligned.dropna(how="any")
	if aligned.empty:
		return 0.0

	variance = float(aligned["benchmark"].var(ddof=0))
	if variance <= 1e-12:
		return 0.0
	covariance = float(aligned["basket"].cov(aligned["benchmark"], ddof=0))
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
	active = aligned["basket"] - aligned["benchmark"]
	return float(active.std(ddof=0) * math.sqrt(periods_per_year))


def vs_benchmark_total_return(returns: pd.Series, benchmark_returns: pd.Series) -> float:
	aligned = pd.concat([returns.rename("basket"), benchmark_returns.rename("benchmark")], axis=1)
	aligned = aligned.dropna(how="any")
	if aligned.empty:
		return 0.0
	basket_total = float((1.0 + aligned["basket"]).prod() - 1.0)
	benchmark_total = float((1.0 + aligned["benchmark"]).prod() - 1.0)
	return basket_total - benchmark_total


def compute_risk_metrics(
	returns: pd.Series,
	signed_weights: Mapping[str, float],
	benchmark_returns: pd.Series | None = None,
	risk_free_rate: float = 0.0,
	periods_per_year: int = 252,
) -> dict[str, float]:
	metrics: dict[str, float] = {
		"ann_vol": annualized_volatility(returns, periods_per_year),
		"sharpe": sharpe_ratio(returns, risk_free_rate, periods_per_year),
		"max_drawdown": max_drawdown(returns),
		"calmar": calmar_ratio(returns, periods_per_year),
		"sortino": sortino_ratio(returns, risk_free_rate, periods_per_year),
		"net_exposure": net_exposure(signed_weights),
		"gross_exposure": gross_exposure(signed_weights),
		"total_return": float((1.0 + returns).prod() - 1.0),
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
