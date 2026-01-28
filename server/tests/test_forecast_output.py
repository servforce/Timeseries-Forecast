from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))


from app.services.forecast_output import filter_prediction_df_quantiles  # noqa: E402


def test_filter_prediction_df_quantiles_keeps_only_requested():
    df = pd.DataFrame(
        [
            {
                "item_id": "store_A",
                "timestamp": "2024-01-12",
                "mean": 1.0,
                "0.1": 0.1,
                "0.2": 0.2,
                "0.3": 0.3,
                "0.4": 0.4,
                "0.5": 0.5,
                "0.6": 0.6,
                "0.7": 0.7,
                "0.8": 0.8,
                "0.9": 0.9,
            }
        ]
    )
    out = filter_prediction_df_quantiles(df, quantiles=[0.1, 0.5, 0.9], keep_mean=True)
    assert list(out.columns) == ["item_id", "timestamp", "mean", "0.1", "0.5", "0.9"]

