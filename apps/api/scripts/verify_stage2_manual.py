from __future__ import annotations

import pandas as pd

from app.analytics.returns import basket_returns
from app.analytics.risk import compute_risk_metrics


def main() -> None:
    index = pd.date_range("2025-01-01", periods=5, freq="D")
    returns_df = pd.DataFrame(
        {
            "SPY": [0.01, 0.02, -0.01, 0.005, 0.00],
            "GLD": [0.005, -0.01, 0.015, 0.0, -0.005],
        },
        index=index,
    )
    legs = [
        {"symbol": "SPY", "side": "long", "currency": "USD"},
        {"symbol": "GLD", "side": "short", "currency": "USD"},
    ]
    weights = {"SPY": 1.0, "GLD": 1.0}

    basket = basket_returns(legs=legs, weights=weights, returns_df=returns_df)
    metrics = compute_risk_metrics(
        returns=basket,
        signed_weights={"SPY": 1.0, "GLD": -1.0},
        benchmark_returns=returns_df["SPY"],
    )

    hand_returns = [0.005, 0.03, -0.025, 0.005, 0.005]
    hand_total_return = (1.005 * 1.03 * 0.975 * 1.005 * 1.005) - 1.0
    hand_max_drawdown = 0.025

    assert [round(x, 6) for x in basket.tolist()] == [round(x, 6) for x in hand_returns]
    assert round(metrics["total_return"], 12) == round(hand_total_return, 12)
    assert round(metrics["max_drawdown"], 12) == round(hand_max_drawdown, 12)
    assert isinstance(metrics["sharpe"], float)

    print("Stage 2 manual verification passed")
    print(f"total_return={metrics['total_return']:.8f}")
    print(f"sharpe={metrics['sharpe']:.8f}")
    print(f"max_drawdown={metrics['max_drawdown']:.8f}")


if __name__ == "__main__":
    main()