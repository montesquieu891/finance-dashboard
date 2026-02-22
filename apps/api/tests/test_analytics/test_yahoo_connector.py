from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from app.ingestion.yahoo import YahooFinanceConnector


def _raw_frame() -> pd.DataFrame:
    index = pd.to_datetime([datetime(2025, 1, 2), datetime(2025, 1, 3)])
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.5],
            "Adj Close": [101.0, 102.5],
            "Volume": [1_000_000, 1_100_000],
        },
        index=index,
    )


def test_normalize_maps_columns() -> None:
    connector = YahooFinanceConnector()
    normalized = connector.normalize(_raw_frame())

    assert list(normalized.columns) == [
        "date",
        "px_open",
        "px_high",
        "px_low",
        "px_close",
        "px_adj_close",
        "volume",
    ]
    assert len(normalized) == 2
    assert normalized.iloc[0]["px_close"] == 101.0


def test_validate_accepts_valid_frame() -> None:
    connector = YahooFinanceConnector()
    normalized = connector.normalize(_raw_frame())

    connector.validate(normalized)


def test_validate_rejects_missing_close() -> None:
    connector = YahooFinanceConnector()
    invalid = connector.normalize(_raw_frame()).drop(columns=["px_close"])

    with pytest.raises(ValueError, match="Missing required columns"):
        connector.validate(invalid)
