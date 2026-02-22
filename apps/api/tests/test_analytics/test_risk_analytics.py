import pandas as pd

from app.analytics.risk import (
    beta,
    compute_risk_metrics,
    gross_exposure,
    max_drawdown,
    net_exposure,
    tracking_error,
    vs_benchmark_total_return,
)


def test_exposure_helpers() -> None:
    signed_weights = {"SPY": 1.2, "GLD": -0.8}
    assert round(net_exposure(signed_weights), 12) == 0.4
    assert round(gross_exposure(signed_weights), 12) == 2.0


def test_max_drawdown_known_value() -> None:
    returns = pd.Series([0.10, -0.20, 0.05])
    assert round(max_drawdown(returns), 10) == round(0.2, 10)


def test_benchmark_relative_metrics() -> None:
    basket = pd.Series([0.01, 0.00, -0.01, 0.02])
    benchmark = pd.Series([0.005, 0.001, -0.005, 0.01])

    assert tracking_error(basket, benchmark) > 0.0
    assert beta(basket, benchmark) > 0.0
    expected_vs = ((1.01 * 1.0 * 0.99 * 1.02) - 1.0) - ((1.005 * 1.001 * 0.995 * 1.01) - 1.0)
    assert round(vs_benchmark_total_return(basket, benchmark), 12) == round(expected_vs, 12)


def test_compute_risk_metrics_shape() -> None:
    returns = pd.Series([0.01, -0.005, 0.004, 0.002])
    benchmark = pd.Series([0.008, -0.003, 0.002, 0.001])
    signed_weights = {"A": 0.7, "B": -0.3}

    metrics = compute_risk_metrics(returns, signed_weights, benchmark_returns=benchmark)

    expected_keys = {
        "ann_vol",
        "sharpe",
        "max_drawdown",
        "calmar",
        "sortino",
        "beta",
        "net_exposure",
        "gross_exposure",
        "total_return",
        "vs_benchmark",
        "tracking_error",
    }
    assert expected_keys.issubset(metrics.keys())