from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def _safe_spearman(x: np.ndarray, y: np.ndarray) -> Optional[float]:
    if len(x) < 2:
        return None
    # rank transform
    xr = pd.Series(x).rank(method="average").to_numpy()
    yr = pd.Series(y).rank(method="average").to_numpy()
    if np.all(xr == xr[0]) or np.all(yr == yr[0]):
        return None
    corr = np.corrcoef(xr, yr)[0, 1]
    if np.isnan(corr):
        return None
    return float(corr)


@dataclass(frozen=True)
class IcIrResult:
    ic: Optional[float]
    ir: Optional[float]
    ic_by_timestamp: List[float]
    method: str


def compute_ic_ir(
    *,
    df: pd.DataFrame,
    y_true_col: str,
    y_pred_col: str,
    timestamp_col: str = "timestamp",
    item_id_col: str = "item_id",
) -> IcIrResult:
    """
    Compute IC (Information Coefficient) and IR (Information Ratio) for holdout horizon.

    We use a standard finance-style definition:
    - IC_t: cross-sectional Spearman correlation between y_pred and y_true across item_id at each timestamp t
    - IC: mean(IC_t) over timestamps where correlation is defined
    - IR: mean(IC_t) / std(IC_t) over timestamps (std with ddof=1)

    Fallback: if cross-sectional IC cannot be computed (e.g., only 1 series), compute overall Spearman across all points.
    """
    work = df[[timestamp_col, item_id_col, y_true_col, y_pred_col]].copy()
    work = work.dropna(subset=[y_true_col, y_pred_col])
    if work.empty:
        return IcIrResult(ic=None, ir=None, ic_by_timestamp=[], method="empty")

    # Ensure timestamp is comparable for grouping
    work[timestamp_col] = pd.to_datetime(work[timestamp_col], errors="coerce")
    work = work.dropna(subset=[timestamp_col])
    if work.empty:
        return IcIrResult(ic=None, ir=None, ic_by_timestamp=[], method="empty")

    ic_list: List[float] = []
    for _, g in work.groupby(timestamp_col, sort=True):
        if g[item_id_col].nunique() < 2:
            continue
        corr = _safe_spearman(g[y_pred_col].to_numpy(), g[y_true_col].to_numpy())
        if corr is not None:
            ic_list.append(corr)

    if ic_list:
        ic = float(np.mean(ic_list))
        if len(ic_list) >= 2:
            std = float(np.std(ic_list, ddof=1))
            ir = ic / std if std > 0 else None
        else:
            ir = None
        return IcIrResult(ic=ic, ir=ir, ic_by_timestamp=ic_list, method="cross_sectional_by_timestamp")

    # Fallback: overall Spearman across all points
    corr_all = _safe_spearman(work[y_pred_col].to_numpy(), work[y_true_col].to_numpy())
    return IcIrResult(ic=corr_all, ir=None, ic_by_timestamp=[], method="overall_spearman_fallback")

