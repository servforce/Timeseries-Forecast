from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


def _as_float(value: Any) -> Optional[float]:
    try:
        f = float(value)
    except Exception:
        return None
    if pd.isna(f):
        return None
    return f


def normalize_evaluate_result(evaluate_result: Any) -> Dict[str, Any]:
    """
    Normalize AutoGluon TimeSeriesPredictor.evaluate outputs into a JSON-friendly dict.

    AutoGluon versions may return:
    - dict of metrics
    - pandas Series
    - pandas DataFrame (per item_id)
    """
    if evaluate_result is None:
        return {}

    if isinstance(evaluate_result, dict):
        return evaluate_result

    if isinstance(evaluate_result, pd.Series):
        return evaluate_result.to_dict()

    if isinstance(evaluate_result, pd.DataFrame):
        # If it's a single row, flatten to dict; otherwise keep both overall mean and per-series.
        if evaluate_result.shape[0] == 1:
            return evaluate_result.iloc[0].to_dict()

        means = evaluate_result.mean(numeric_only=True).to_dict()
        return {
            "mean": means,
            "by_series": evaluate_result.to_dict(orient="index"),
        }

    # Fallback: best-effort string conversion
    return {"raw": str(evaluate_result)}

