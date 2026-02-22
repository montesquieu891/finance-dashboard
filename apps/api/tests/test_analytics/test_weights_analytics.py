import pandas as pd

from app.analytics.weights import (
    beta_adjusted_weights,
    equal_weights,
    inverse_corr_weights,
    inverse_vol_weights,
    risk_parity_weights,
)


def _sample_returns() -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=6, freq="D")
    return pd.DataFrame(
        {
            "A": [0.01, 0.02, -0.01, 0.03, 0.01, -0.02],
            "B": [0.005, 0.004, -0.003, 0.007, 0.006, -0.002],
            "C": [0.02, -0.01, 0.015, -0.005, 0.01, 0.0],
        },
        index=index,
    )


def _assert_weight_invariants(weights: pd.Series, gross_exposure: float) -> None:
    n_assets = len(weights)
    cap = 5.0 * (gross_exposure / n_assets)
    assert round(float(weights.sum()), 10) == gross_exposure
    assert (weights >= 0.0).all()
    assert (weights <= cap + 1e-10).all()


def test_equal_weights_invariants() -> None:
    weights = equal_weights(["A", "B", "C"], gross_exposure=2.0)
    _assert_weight_invariants(weights, gross_exposure=2.0)


def test_inverse_vol_weights_invariants() -> None:
    weights = inverse_vol_weights(_sample_returns(), gross_exposure=3.0)
    _assert_weight_invariants(weights, gross_exposure=3.0)


def test_inverse_corr_weights_invariants() -> None:
    weights = inverse_corr_weights(_sample_returns(), gross_exposure=1.5)
    _assert_weight_invariants(weights, gross_exposure=1.5)


def test_risk_parity_weights_invariants() -> None:
    weights = risk_parity_weights(_sample_returns(), gross_exposure=2.5)
    _assert_weight_invariants(weights, gross_exposure=2.5)


def test_beta_adjusted_weights_invariants() -> None:
    returns_df = _sample_returns()
    benchmark = pd.Series([0.01, 0.008, -0.005, 0.012, 0.009, -0.003], index=returns_df.index)
    weights = beta_adjusted_weights(returns_df, benchmark_returns=benchmark, gross_exposure=2.0)
    _assert_weight_invariants(weights, gross_exposure=2.0)