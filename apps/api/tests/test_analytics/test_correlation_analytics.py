import pandas as pd

from app.analytics.correlation import pairwise_correlation


def test_pairwise_correlation_returns_square_matrix() -> None:
    index = pd.date_range("2025-01-01", periods=5, freq="D")
    returns_df = pd.DataFrame(
        {
            "A": [0.01, 0.02, -0.01, 0.0, 0.03],
            "B": [0.005, 0.01, -0.004, 0.001, 0.02],
            "C": [0.02, -0.01, 0.015, -0.005, 0.01],
        },
        index=index,
    )

    matrix = pairwise_correlation(returns_df, lookback=4)

    assert matrix.shape == (3, 3)
    assert matrix.index.tolist() == ["A", "B", "C"]
    assert matrix.columns.tolist() == ["A", "B", "C"]
    assert float(matrix.loc["A", "A"]) == 1.0
