import pandas as pd

from app.analytics.factors import (
    factor_attribution,
    factor_correlation_matrix,
    regime_map,
    rolling_factor_exposures,
)


def test_rolling_factor_exposures_returns_expected_columns() -> None:
    index = pd.date_range("2025-01-01", periods=80, freq="D")
    factor_df = pd.DataFrame(
        {
            "MKT": [0.001 + (idx % 5) * 0.0002 for idx in range(80)],
            "COMM": [0.0008 + (idx % 3) * 0.0003 for idx in range(80)],
        },
        index=index,
    )
    basket = pd.Series(
        [
            0.0002 + 1.5 * factor_df.iloc[idx]["MKT"] + 0.5 * factor_df.iloc[idx]["COMM"]
            for idx in range(80)
        ],
        index=index,
    )

    exposures = rolling_factor_exposures(
        basket_returns=basket,
        factor_returns_df=factor_df,
        window=30,
    )

    assert {"MKT", "COMM", "alpha", "r2"}.issubset(set(exposures.columns))
    assert len(exposures) == 51


def test_factor_attribution_contains_idiosyncratic_bucket() -> None:
    index = pd.date_range("2025-01-01", periods=70, freq="D")
    factor_df = pd.DataFrame(
        {
            "MKT": [0.001 + (idx % 4) * 0.0002 for idx in range(70)],
            "DEF": [0.0009 + (idx % 3) * 0.00015 for idx in range(70)],
        },
        index=index,
    )
    basket = pd.Series(
        [
            0.0001 + 1.2 * factor_df.iloc[idx]["MKT"] - 0.4 * factor_df.iloc[idx]["DEF"]
            for idx in range(70)
        ],
        index=index,
    )

    attribution = factor_attribution(basket_returns=basket, factor_returns_df=factor_df)

    assert "MKT" in attribution
    assert "DEF" in attribution
    assert "IDIO" in attribution


def test_regime_map_picks_dominant_factor() -> None:
    index = pd.date_range("2025-01-01", periods=3, freq="D")
    exposures = pd.DataFrame(
        {
            "MKT": [0.8, 0.1, 0.2],
            "COMM": [0.1, 0.9, 0.1],
            "DEF": [0.2, 0.3, 1.1],
            "alpha": [0.0, 0.0, 0.0],
            "r2": [0.8, 0.8, 0.8],
        },
        index=index,
    )

    regimes = regime_map(
        exposures_df=exposures,
        factor_to_regime={"MKT": "growth", "COMM": "inflation", "DEF": "risk-off"},
    )

    assert regimes.tolist() == ["growth", "inflation", "risk-off"]


def test_factor_correlation_matrix_shape() -> None:
    index = pd.date_range("2025-01-01", periods=40, freq="D")
    factor_df = pd.DataFrame(
        {
            "MKT": [0.001 + idx * 0.00001 for idx in range(40)],
            "COMM": [0.0005 + idx * 0.00002 for idx in range(40)],
        },
        index=index,
    )

    corr = factor_correlation_matrix(factor_returns_df=factor_df)

    assert list(corr.columns) == ["MKT", "COMM"]
    assert list(corr.index) == ["MKT", "COMM"]
