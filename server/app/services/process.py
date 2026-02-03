import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from app.core.exceptions import DataException, ErrorCode


_JSON_FENCE_RE = re.compile(r"```json\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class ParsedMarkdownInput:
    history_df: pd.DataFrame
    future_cov_df: Optional[pd.DataFrame]
    test_df: Optional[pd.DataFrame]
    freq: str
    known_covariates_names: List[str]
    category_covariates_names: List[str]


def extract_json_from_markdown(markdown_text: str) -> Dict[str, Any]:
    """
    Extract JSON payload from a markdown text.

    Priority:
    1) First fenced ```json ... ``` block
    2) If markdown itself is JSON
    """
    match = _JSON_FENCE_RE.search(markdown_text)
    if match:
        raw = match.group(1).strip()
    else:
        raw = markdown_text.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataException(
            error_code=ErrorCode.DATA_FORMAT_ERROR,
            message="Markdown 中未找到可解析的 JSON（请使用 ```json 代码块包裹输入）",
            details={"reason": str(exc)},
        ) from exc


def _normalize_id_key(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize id key: accept `item_id` or `id`, and store into `item_id`.
    """
    normalized: List[Dict[str, Any]] = []
    for rec in records:
        if "item_id" not in rec and "id" in rec:
            rec = dict(rec)
            rec["item_id"] = rec.pop("id")
        normalized.append(rec)
    return normalized


def _require_columns(df: pd.DataFrame, required: Sequence[str], *, where: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataException(
            error_code=ErrorCode.DATA_MISSING_COLUMNS,
            message=f"{where} 缺少必要字段: {missing}",
            details={"missing_columns": missing, "where": where},
        )


def _parse_timestamp_column(df: pd.DataFrame, *, where: str) -> pd.DataFrame:
    df = df.copy()
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)
    except Exception as exc:
        raise DataException(
            error_code=ErrorCode.DATA_FORMAT_ERROR,
            message=f"{where}.timestamp 无法解析为时间类型",
            details={"reason": str(exc)},
        ) from exc
    return df


def _infer_freq_per_item(history_df: pd.DataFrame) -> Optional[str]:
    freqs: set[str] = set()
    for _, group in history_df.groupby("item_id", sort=False):
        ts = group.sort_values("timestamp")["timestamp"]
        if len(ts) < 3:
            continue
        inferred = pd.infer_freq(ts)
        if inferred:
            freqs.add(str(inferred))
    if not freqs:
        return None
    if len(freqs) > 1:
        return None
    return next(iter(freqs))


def parse_markdown_payload(
    payload: Dict[str, Any],
    *,
    prediction_length: int,
    with_cov: bool,
    freq_override: Optional[str],
    max_series: int,
    max_points_per_series: int,
    max_prediction_length: int,
) -> ParsedMarkdownInput:
    """
    Validate and normalize JSON payload (extracted from markdown) into DataFrames.

    Returns DataFrames with normalized columns:
    - history_df: timestamp, item_id, target, + covariates (optional)
    - covariates_df: timestamp, item_id, + known covariates (optional)
    """
    if prediction_length <= 0:
        raise DataException(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="prediction_length 必须为正整数",
            details={"prediction_length": prediction_length},
        )
    if prediction_length > max_prediction_length:
        raise DataException(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="prediction_length 超过服务限制",
            details={"prediction_length": prediction_length, "max_prediction_length": max_prediction_length},
        )

    history_data = payload.get("history_data")
    if not isinstance(history_data, list) or not history_data:
        raise DataException(
            error_code=ErrorCode.DATA_EMPTY,
            message="history_data 不能为空（请在 Markdown 的 JSON 中提供 history_data 数组）",
        )

    history_data = _normalize_id_key(history_data)
    history_df = pd.DataFrame(history_data)
    _require_columns(history_df, ["timestamp", "item_id", "target"], where="history_data")
    history_df = _parse_timestamp_column(history_df, where="history_data")

    history_df = history_df.sort_values(["item_id", "timestamp"]).reset_index(drop=True)
    if history_df["item_id"].nunique() > max_series:
        raise DataException(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="序列数量超过服务限制",
            details={"max_series": max_series, "series": int(history_df["item_id"].nunique())},
        )
    counts = history_df.groupby("item_id").size()
    too_long = counts[counts > max_points_per_series]
    if not too_long.empty:
        raise DataException(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="单条序列历史点数超过服务限制",
            details={"max_points_per_series": max_points_per_series, "violations": too_long.to_dict()},
        )

    # freq: prefer override > payload > infer
    freq = (freq_override or payload.get("freq") or "").strip()
    if not freq:
        inferred = _infer_freq_per_item(history_df)
        if not inferred:
            raise DataException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="无法推断时间频率，请在输入中提供 freq（例如 D/H/W/M）",
            )
        freq = inferred

    future_cov_df: Optional[pd.DataFrame] = None
    known_covariates_names: List[str] = []
    test_df: Optional[pd.DataFrame] = None
    category_covariates_names: List[str] = []

    # Optional test_data: if provided, can be concatenated to history_data for evaluation.
    # This is NOT required. If omitted, metrics can still be computed on history_data by holding out
    # the last prediction_length time steps (note this can be optimistic since model may see the holdout).
    test_data = payload.get("test_data")
    if isinstance(test_data, list) and test_data:
        test_data = _normalize_id_key(test_data)
        test_df = pd.DataFrame(test_data)
        _require_columns(test_df, ["timestamp", "item_id", "target"], where="test_data")
        test_df = _parse_timestamp_column(test_df, where="test_data")
        test_df = test_df.sort_values(["item_id", "timestamp"]).reset_index(drop=True)

        group_counts = test_df.groupby("item_id").size()
        mismatch = group_counts[group_counts != prediction_length]
        if not mismatch.empty:
            raise DataException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="test_data 每个 item_id 的行数必须等于 prediction_length（用于 evaluate 评估）",
                details={"group_counts": group_counts.to_dict(), "prediction_length": prediction_length},
            )

    def _read_name_list(keys: Sequence[str]) -> List[str]:
        names: List[str] = []
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                names.extend([str(x).strip() for x in value if str(x).strip()])
            elif isinstance(value, str):
                names.extend([x.strip() for x in value.split(",") if x.strip()])
        deduped: List[str] = []
        seen = set()
        for name in names:
            if name not in seen:
                seen.add(name)
                deduped.append(name)
        return deduped

    category_covariates_names = _read_name_list(["category_cov_name", "category_name"])

    if with_cov:
        # known cov names: payload or infer from covariates keys
        known_covariates_names = _read_name_list(["known_covariates_names", "know_cov_name"])

        covariates = payload.get("covariates")
        if not isinstance(covariates, list) or not covariates:
            raise DataException(
                error_code=ErrorCode.DATA_FORMAT_ERROR,
                message="with_cov=true 时必须提供 covariates（未来已知协变量）",
            )
        covariates = _normalize_id_key(covariates)
        future_cov_df = pd.DataFrame(covariates)
        _require_columns(future_cov_df, ["timestamp", "item_id"], where="covariates")
        future_cov_df = _parse_timestamp_column(future_cov_df, where="covariates")
        future_cov_df = future_cov_df.sort_values(["item_id", "timestamp"]).reset_index(drop=True)

        if not known_covariates_names:
            known_covariates_names = [
                c for c in future_cov_df.columns if c not in {"timestamp", "item_id"}
            ]
        if not known_covariates_names:
            raise DataException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="无法确定 known_covariates_names（请在输入提供 known_covariates_names 或在 covariates 中提供协变量列）",
            )

        # Validate: known covs exist in history and future
        for col in known_covariates_names:
            if col not in history_df.columns:
                raise DataException(
                    error_code=ErrorCode.DATA_MISSING_COLUMNS,
                    message="history_data 缺少已知协变量列",
                    details={"missing_column": col, "where": "history_data"},
                )
            if col not in future_cov_df.columns:
                raise DataException(
                    error_code=ErrorCode.DATA_MISSING_COLUMNS,
                    message="covariates 缺少已知协变量列",
                    details={"missing_column": col, "where": "covariates"},
                )

        covariate_cols = [c for c in history_df.columns if c not in {"timestamp", "item_id", "target"}]
        missing_categories = [c for c in category_covariates_names if c not in covariate_cols]
        if missing_categories:
            raise DataException(
                error_code=ErrorCode.DATA_MISSING_COLUMNS,
                message="category_cov_name 包含不存在的协变量列",
                details={"missing_columns": missing_categories, "where": "history_data"},
            )

        def _encode_category_columns(
            history: pd.DataFrame,
            future: Optional[pd.DataFrame],
            cols: Sequence[str],
        ) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
            for col in cols:
                history_series = history[col]
                future_series = future[col] if future is not None and col in future.columns else None
                combined = pd.concat(
                    [s for s in [history_series, future_series] if s is not None], ignore_index=True
                )
                non_null = combined[combined.notna()]
                numeric = pd.to_numeric(non_null, errors="coerce")
                is_numeric = numeric.notna().sum() == non_null.shape[0]

                if is_numeric:
                    cats = pd.Series(numeric.unique()).sort_values()
                    cat_type = pd.CategoricalDtype(categories=cats, ordered=False)
                    history_num = pd.to_numeric(history_series, errors="coerce")
                    history[col] = history_num.astype(cat_type)
                    if future is not None and col in future.columns:
                        future_num = pd.to_numeric(future_series, errors="coerce")
                        future[col] = future_num.astype(cat_type)
                else:
                    cats = pd.Series(non_null.astype(str).unique())
                    cat_type = pd.CategoricalDtype(categories=cats, ordered=False)
                    history_codes = pd.Categorical(history_series.astype(str), dtype=cat_type).codes
                    history_codes = pd.Series(history_codes).replace(-1, pd.NA)
                    history[col] = history_codes.astype("category")
                    if future is not None and col in future.columns:
                        future_codes = pd.Categorical(future_series.astype(str), dtype=cat_type).codes
                        future_codes = pd.Series(future_codes).replace(-1, pd.NA)
                        future[col] = future_codes.astype("category")
            return history, future

        if covariate_cols:
            history_df, future_cov_df = _encode_category_columns(
                history_df, future_cov_df, category_covariates_names
            )
            numeric_covs = [c for c in covariate_cols if c not in category_covariates_names]
            for col in numeric_covs:
                try:
                    history_df[col] = pd.to_numeric(history_df[col], errors="raise").astype(float)
                except Exception as exc:
                    raise DataException(
                        error_code=ErrorCode.DATA_FORMAT_ERROR,
                        message="协变量列必须为数值类型或放入 category_cov_name",
                        details={"column": col, "where": "history_data", "reason": str(exc)},
                    ) from exc

        # Validate future length per item_id == prediction_length
        group_counts = future_cov_df.groupby("item_id").size()
        mismatch = group_counts[group_counts != prediction_length]
        if not mismatch.empty:
            raise DataException(
                error_code=ErrorCode.FUTURE_COV_MISMATCH,
                message="covariates 每个 item_id 的行数必须等于 prediction_length",
                details={"group_counts": group_counts.to_dict(), "prediction_length": prediction_length},
            )

        last_hist = history_df.groupby("item_id")["timestamp"].max()
        future_groups = future_cov_df.groupby("item_id")["timestamp"]
        invalid_items: Dict[str, List[str]] = {}
        for item_id, last_ts in last_hist.items():
            try:
                future_ts = future_groups.get_group(item_id).sort_values()
            except Exception:
                invalid_items[str(item_id)] = ["missing_future_covariates"]
                continue
            expected = pd.date_range(start=last_ts, periods=prediction_length + 1, freq=freq)[1:]
            if len(future_ts) != len(expected) or not future_ts.reset_index(drop=True).equals(
                pd.Series(expected).reset_index(drop=True)
            ):
                invalid_items[str(item_id)] = ["future_covariates_not_cover_prediction_window"]
        if invalid_items:
            raise DataException(
                error_code=ErrorCode.FUTURE_COV_MISMATCH,
                message="covariates 未覆盖预测区间（需从最后历史时间开始连续覆盖 prediction_length）",
                details={"items": invalid_items, "prediction_length": prediction_length, "freq": freq},
            )

        # Keep only known cov columns + id/timestamp for known cov df
        future_cov_df = future_cov_df[["item_id", "timestamp", *known_covariates_names]].copy()
        numeric_known = [c for c in known_covariates_names if c not in category_covariates_names]
        for col in numeric_known:
            try:
                future_cov_df[col] = pd.to_numeric(future_cov_df[col], errors="raise").astype(float)
            except Exception as exc:
                raise DataException(
                    error_code=ErrorCode.DATA_FORMAT_ERROR,
                    message="协变量列必须为数值类型或放入 category_cov_name",
                    details={"column": col, "where": "covariates", "reason": str(exc)},
                ) from exc
    else:
        # Explicitly ignore any covariate columns if with_cov is false.
        history_df = history_df[["timestamp", "item_id", "target"]].copy()
        future_cov_df = None
        known_covariates_names = []
        category_covariates_names = []

    return ParsedMarkdownInput(
        history_df=history_df,
        future_cov_df=future_cov_df,
        test_df=test_df,
        freq=freq,
        known_covariates_names=known_covariates_names,
        category_covariates_names=category_covariates_names,
    )
