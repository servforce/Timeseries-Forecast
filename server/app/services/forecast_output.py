from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pandas as pd


def _quantile_to_candidate_colnames(q: float) -> List[str]:
    """
    AutoGluon 输出的分位数字段通常是字符串形式，例如 "0.1"。
    这里做一层容错：不同浮点表示（0.1 / 0.10 / 0.1000000001）尽量匹配到实际列名。
    """
    candidates = []

    # 原始字符串（FastAPI Query 传入常见是 float -> str）
    candidates.append(str(q))

    # g-format（0.100000 -> 0.1）
    candidates.append(f"{q:g}")

    # 常见 1~3 位小数
    for decimals in (1, 2, 3, 6):
        fixed = f"{q:.{decimals}f}"
        candidates.append(fixed)  # keep trailing zeros variant, e.g. "0.10"

        stripped = fixed
        if "." in stripped:
            stripped = stripped.rstrip("0").rstrip(".")
        candidates.append(stripped)

    # 去重保持顺序
    seen = set()
    ordered: List[str] = []
    for s in candidates:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered


def _canonical_quantile_name(q: float) -> str:
    # Canonicalize to match typical API requests (and frontend string keys):
    # 0.1 -> "0.1", 0.05 -> "0.05"
    return f"{q:g}"


def resolve_quantile_columns(
    pred_df: pd.DataFrame,
    *,
    quantiles: List[float],
) -> Tuple[Dict[float, str], List[float]]:
    """
    Resolve requested quantiles to actual column names in pred_df.

    Returns:
      - mapping: q -> column_name (only for found)
      - missing: list of q that cannot be found in pred_df columns
    """
    mapping: Dict[float, str] = {}
    missing: List[float] = []

    for q in quantiles:
        # Some implementations may use float column names (rare, but handle it).
        if q in pred_df.columns:
            mapping[q] = q  # type: ignore[assignment]
            continue

        found = None
        for name in _quantile_to_candidate_colnames(q):
            if name in pred_df.columns:
                found = name
                break

        if found is None:
            missing.append(q)
        else:
            mapping[q] = found

    return mapping, missing


def filter_prediction_df_quantiles(
    pred_df: pd.DataFrame,
    *,
    quantiles: List[float],
    keep_mean: bool = True,
    strict: bool = False,
) -> pd.DataFrame:
    """
    将预测结果裁剪为「基础列 + mean(可选) + 指定 quantiles」。

    解决问题：即使 API 只传了 [0.1,0.5,0.9]，某些版本/配置的 AutoGluon 可能仍返回 0.1~0.9 全量分位数。
    """
    df = pred_df.copy()

    # 兼容输出列名：id -> item_id
    if "item_id" not in df.columns and "id" in df.columns:
        df = df.rename(columns={"id": "item_id"})

    base_cols: List[str] = []
    for col in ("item_id", "timestamp"):
        if col in df.columns:
            base_cols.append(col)

    keep_cols: List[str] = [*base_cols]
    if keep_mean and "mean" in df.columns:
        keep_cols.append("mean")

    mapping, missing = resolve_quantile_columns(df, quantiles=quantiles)
    if strict and missing:
        raise ValueError(f"Missing quantile columns: {missing}")

    selected_quantile_cols: List[str] = [mapping[q] for q in quantiles if q in mapping]

    keep_cols.extend(selected_quantile_cols)

    # 若缺少基础列，保持原样返回（避免 KeyError）
    missing_keep = [c for c in keep_cols if c not in df.columns]
    if missing_keep:
        return df

    out = df[keep_cols].copy()

    # Normalize quantile column names to canonical strings so that
    # "0.10"/0.1 inconsistencies don't break the frontend.
    rename_map = {}
    for q, col in mapping.items():
        canonical = _canonical_quantile_name(q)
        if col != canonical:
            rename_map[col] = canonical
    if rename_map:
        out = out.rename(columns=rename_map)

    return out
