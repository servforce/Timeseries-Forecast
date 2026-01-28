from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import re
import pandas as pd

from app.core.exceptions import DataException, ErrorCode


ALLOWED_METRICS = {"WQL", "WAPE", "IC", "IR"}
DEFAULT_METRICS = ["WQL", "WAPE"]


def normalize_metrics_request(metrics: Optional[Sequence[str]]) -> List[str]:
    if metrics is None:
        return list(DEFAULT_METRICS)

    normalized: List[str] = []
    for raw in metrics:
        if raw is None:
            continue
        key = str(raw).strip().upper()
        if not key:
            continue
        if key not in ALLOWED_METRICS:
            raise DataException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="metrics 仅支持 WQL/WAPE/IC/IR",
                details={"bad_value": raw, "allowed": sorted(ALLOWED_METRICS)},
            )
        if key not in normalized:
            normalized.append(key)
    return normalized


def filter_metric_result(metrics_obj: Dict[str, Any], allowed: Iterable[str]) -> Dict[str, Any]:
    allowed_set = {str(x).upper() for x in allowed}
    filtered: Dict[str, Any] = {}
    for key, value in (metrics_obj or {}).items():
        key_upper = str(key).upper()
        if key in {"mean", "by_series"} and isinstance(value, dict):
            sub = {k: v for k, v in value.items() if str(k).upper() in allowed_set}
            if sub:
                filtered[key] = sub
            continue
        if key_upper in allowed_set:
            filtered[key] = value
    return filtered


def split_holdout_frame(
    df: pd.DataFrame,
    prediction_length: int,
    *,
    item_id_col: str = "item_id",
    timestamp_col: str = "timestamp",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    work = df.sort_values([item_id_col, timestamp_col]).reset_index(drop=True)
    group_sizes = work.groupby(item_id_col)[timestamp_col].transform("size")
    order = work.groupby(item_id_col).cumcount()
    cutoff = group_sizes - int(prediction_length)
    train_df = work[order < cutoff].copy()
    holdout_df = work[order >= cutoff].copy()
    return train_df, holdout_df


def replace_pred_timestamps_with_future(
    pred_df: pd.DataFrame,
    history_df: pd.DataFrame,
    *,
    prediction_length: int,
    freq: str,
    item_id_col: str = "item_id",
    timestamp_col: str = "timestamp",
) -> pd.DataFrame:
    pred_df = pd.DataFrame(pred_df)
    history_df = pd.DataFrame(history_df)
    if timestamp_col not in pred_df.columns or item_id_col not in pred_df.columns:
        return pred_df
    if prediction_length <= 0:
        return pred_df

    try:
        hist = history_df[[item_id_col, timestamp_col]].copy()
        hist[timestamp_col] = pd.to_datetime(hist[timestamp_col], errors="coerce")
        hist = hist.dropna(subset=[timestamp_col])
        last_ts = hist.groupby(item_id_col)[timestamp_col].max()
        if last_ts.empty:
            return pred_df

        future_map: Dict[str, List[pd.Timestamp]] = {}
        for item_id, ts in last_ts.items():
            if pd.isna(ts):
                continue
            future = pd.date_range(start=ts, periods=int(prediction_length) + 1, freq=freq)[1:]
            future_map[str(item_id)] = list(future)

        work = pred_df.copy()
        work[timestamp_col] = pd.to_datetime(work[timestamp_col], errors="coerce")
        work = work.sort_values([item_id_col, timestamp_col])
        work["_pos"] = work.groupby(item_id_col).cumcount()
        work = work[work["_pos"] < int(prediction_length)].copy()

        def _assign_future(row: pd.Series) -> pd.Timestamp:
            key = str(row[item_id_col])
            seq = future_map.get(key)
            if not seq:
                return row[timestamp_col]
            pos = int(row["_pos"])
            if pos < len(seq):
                return seq[pos]
            return row[timestamp_col]

        work[timestamp_col] = work.apply(_assign_future, axis=1)
        return work.drop(columns=["_pos"])
    except Exception:
        return pred_df


def replace_pred_timestamps_with_holdout(
    pred_df: pd.DataFrame,
    holdout_df: pd.DataFrame,
    *,
    item_id_col: str = "item_id",
    timestamp_col: str = "timestamp",
) -> pd.DataFrame:
    pred_df = pd.DataFrame(pred_df)
    holdout_df = pd.DataFrame(holdout_df)
    if timestamp_col not in pred_df.columns or item_id_col not in pred_df.columns:
        return pred_df

    try:
        holdout = holdout_df[[item_id_col, timestamp_col]].copy()
        holdout[timestamp_col] = pd.to_datetime(holdout[timestamp_col], errors="coerce")
        holdout = holdout.dropna(subset=[timestamp_col]).sort_values([item_id_col, timestamp_col])
        holdout_map_raw = holdout.groupby(item_id_col)[timestamp_col].apply(list).to_dict()
        holdout_map = {str(k): v for k, v in holdout_map_raw.items()}
        if not holdout_map:
            return pred_df

        work = pred_df.copy()
        work[timestamp_col] = pd.to_datetime(work[timestamp_col], errors="coerce")
        work = work.sort_values([item_id_col, timestamp_col])
        work["_pos"] = work.groupby(item_id_col).cumcount()
        work["_limit"] = work[item_id_col].map(lambda x: len(holdout_map.get(str(x), [])))
        work = work[work["_pos"] < work["_limit"]].copy()

        def _assign_holdout(row: pd.Series) -> pd.Timestamp:
            key = str(row[item_id_col])
            seq = holdout_map.get(key)
            if not seq:
                return row[timestamp_col]
            pos = int(row["_pos"])
            if pos < len(seq):
                return seq[pos]
            return row[timestamp_col]

        work[timestamp_col] = work.apply(_assign_holdout, axis=1)
        return work.drop(columns=["_pos", "_limit"])
    except Exception:
        return pred_df


def select_prediction_column(pred_df: pd.DataFrame) -> Optional[str | float]:
    if "mean" in pred_df.columns:
        return "mean"
    if "0.5" in pred_df.columns:
        return "0.5"
    if 0.5 in pred_df.columns:
        return 0.5

    quantile_cols: List[str | float] = []
    for col in pred_df.columns:
        if isinstance(col, str) and re.match(r"^0\.\d+$", col):
            quantile_cols.append(col)
        elif isinstance(col, (int, float)) and 0 < float(col) < 1:
            quantile_cols.append(col)

    return quantile_cols[0] if quantile_cols else None


def merge_holdout_predictions(
    holdout_df: pd.DataFrame,
    pred_df: pd.DataFrame,
    pred_col: str | float,
    *,
    item_id_col: str = "item_id",
    timestamp_col: str = "timestamp",
) -> pd.DataFrame:
    holdout_df = pd.DataFrame(holdout_df)
    pred_df = pd.DataFrame(pred_df)
    if holdout_df.empty or pred_df.empty:
        return pd.DataFrame()

    holdout = holdout_df[[item_id_col, timestamp_col, "target"]].copy()
    pred = pred_df[[item_id_col, timestamp_col, pred_col]].copy()

    holdout[item_id_col] = holdout[item_id_col].astype(str)
    pred[item_id_col] = pred[item_id_col].astype(str)

    holdout[timestamp_col] = pd.to_datetime(holdout[timestamp_col], errors="coerce")
    pred[timestamp_col] = pd.to_datetime(pred[timestamp_col], errors="coerce")

    holdout = holdout.dropna(subset=[timestamp_col])
    pred = pred.dropna(subset=[timestamp_col])

    merged = holdout.merge(pred, on=[item_id_col, timestamp_col], how="inner")
    if not merged.empty:
        return merged

    holdout = holdout.sort_values([item_id_col, timestamp_col])
    pred = pred.sort_values([item_id_col, timestamp_col])
    holdout["_pos"] = holdout.groupby(item_id_col).cumcount()
    pred["_pos"] = pred.groupby(item_id_col).cumcount()

    merged = holdout.merge(
        pred.drop(columns=[timestamp_col]),
        on=[item_id_col, "_pos"],
        how="inner",
    )
    if "_pos" in merged.columns:
        merged = merged.drop(columns=["_pos"])
    return merged
