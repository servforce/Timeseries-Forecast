import logging
import tempfile
from typing import Any, Dict, List, Optional

import pandas as pd
import re

from app.core.config import settings
from app.core.exceptions import DataException, ErrorCode, ModelException
from app.services.forecast_output import filter_prediction_df_quantiles, resolve_quantile_columns
from app.services.evaluate_metrics import normalize_evaluate_result
from app.services.metrics_helpers import (
    filter_metric_result,
    normalize_metrics_request,
    merge_holdout_predictions,
    replace_pred_timestamps_with_future,
    replace_pred_timestamps_with_holdout,
    select_prediction_column,
    split_holdout_frame,
)
from app.services.custom_metrics import compute_ic_ir
from app.services.process import extract_json_from_markdown, parse_markdown_payload
from app.services.device import choose_device


logger = logging.getLogger(__name__)

_MIN_OBS_RE = re.compile(r">=\\s*(\\d+)\\s+observations", re.IGNORECASE)


def _validate_quantiles(quantiles: List[float]) -> List[float]:
    if not quantiles:
        raise DataException(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="quantiles 不能为空",
        )
    normalized: List[float] = []
    for q in quantiles:
        try:
            qf = float(q)
        except Exception as exc:
            raise DataException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="quantiles 必须为 0~1 的浮点数",
                details={"bad_value": q},
            ) from exc
        if not (0.0 < qf < 1.0):
            raise DataException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="quantiles 必须在 (0, 1) 区间内",
                details={"bad_value": qf},
            )
        normalized.append(qf)
    return sorted(set(normalized))


def _lazy_import_autogluon():
    try:
        from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor  # type: ignore
    except Exception as exc:
        raise ModelException(
            error_code=ErrorCode.MODEL_NOT_READY,
            message="AutoGluon 未安装或不可用，请先安装 requirements.txt 后重试",
            details={"reason": str(exc)},
        ) from exc
    return TimeSeriesDataFrame, TimeSeriesPredictor


def zeroshot_forecast_from_markdown_bytes(
    markdown_bytes: bytes,
    *,
    prediction_length: int,
    quantiles: List[float],
    metrics: List[str],
    with_cov: bool,
    device: str | None = None,
    freq: Optional[str] = None,
    context_length: int = 512,
) -> Dict[str, Any]:
    if len(markdown_bytes) > settings.MAX_UPLOAD_BYTES:
        raise DataException(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="上传文件超过大小限制",
            details={"max_upload_bytes": settings.MAX_UPLOAD_BYTES},
        )

    try:
        markdown_text = markdown_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DataException(
            error_code=ErrorCode.DATA_FORMAT_ERROR,
            message="Markdown 文件编码错误，请使用 UTF-8 编码",
        ) from exc

    payload = extract_json_from_markdown(markdown_text)
    parsed = parse_markdown_payload(
        payload,
        prediction_length=prediction_length,
        with_cov=with_cov,
        freq_override=freq,
        max_series=settings.MAX_SERIES,
        max_points_per_series=settings.MAX_POINTS_PER_SERIES,
        max_prediction_length=settings.max_prediction_length,
    )

    quantiles = _validate_quantiles(quantiles)
    metrics = normalize_metrics_request(metrics)

    selected_device = device if device in {"cpu", "cuda"} else None
    if selected_device is None:
        selected_device = choose_device(prefer_cuda=True)

    TimeSeriesDataFrame, TimeSeriesPredictor = _lazy_import_autogluon()

    train_data = TimeSeriesDataFrame.from_data_frame(
        parsed.history_df,
        id_column="item_id",
        timestamp_column="timestamp",
    )

    known_covariates = None
    if with_cov and parsed.future_cov_df is not None:
        known_covariates = TimeSeriesDataFrame.from_data_frame(
            parsed.future_cov_df,
            id_column="item_id",
            timestamp_column="timestamp",
        )

    temp_dir_ctx = tempfile.TemporaryDirectory(prefix="ag-zeroshot-")
    predictor_path = temp_dir_ctx.name
    # Some AutoGluon versions determine quantile outputs from predictor.quantile_levels.
    # Prefer configuring quantile_levels at predictor construction to ensure requested quantiles are produced.
    try:
        predictor = TimeSeriesPredictor(
            prediction_length=prediction_length,
            target="target",
            eval_metric="WQL",
            known_covariates_names=parsed.known_covariates_names or None,
            freq=parsed.freq,
            quantile_levels=quantiles,
            path=predictor_path,
        )
    except TypeError:
        predictor = TimeSeriesPredictor(
            prediction_length=prediction_length,
            target="target",
            eval_metric="WQL",
            known_covariates_names=parsed.known_covariates_names or None,
            freq=parsed.freq,
        )
        if hasattr(predictor, "path"):
            predictor.path = predictor_path  # type: ignore[attr-defined]
        if hasattr(predictor, "quantile_levels"):
            predictor.quantile_levels = quantiles  # type: ignore[attr-defined]

    model_path = settings.CHRONOS_MODEL_PATH
    if not model_path:
        raise ModelException(
            error_code=ErrorCode.MODEL_LOAD_FAILED,
            message="未配置 Chronos-2 模型路径（CHRONOS_MODEL_PATH）",
        )

    min_series_len = int(parsed.history_df.groupby("item_id").size().min())
    # 自适应上下文长度：不超过最短序列长度，避免因 context_length 过大导致训练窗口构造失败
    context_length = min(int(context_length), min_series_len)

    last_fit_exc: Optional[Exception] = None

    for model_name in [settings.AG_CHRONOS_MODEL_NAME, "Chronos2", "Chronos"]:
        if not model_name:
            continue
        hyperparameters = {
            model_name: [
                {
                    "ag_args": {"name_suffix": "_ZeroShot"},
                    "model_path": model_path,
                    "fine_tune": False,
                    "device": selected_device,
                    "context_length": int(context_length),
                }
            ]
        }
        try:
            try:
                predictor.fit(
                    train_data=train_data,
                    enable_ensemble=False,
                    hyperparameters=hyperparameters,
                    num_val_windows=1,
                )
            except TypeError:
                # Older AutoGluon may not accept num_val_windows; fallback.
                predictor.fit(
                    train_data=train_data,
                    enable_ensemble=False,
                    hyperparameters=hyperparameters,
                )
            break
        except Exception as exc:
            last_fit_exc = exc
            logger.warning("AutoGluon fit 失败，尝试下一个模型名: %s, reason=%s", model_name, exc)
            continue
    else:
        # 尝试把“序列过短”的典型错误转为 400，提示用户修数据/参数
        m = _MIN_OBS_RE.search(str(last_fit_exc)) if last_fit_exc else None
        if m:
            required = int(m.group(1))
            raise DataException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=(
                    "时间序列过短，无法用于当前 prediction_length 的模型窗口构造；"
                    "请提供更长的 history_data，或降低 prediction_length。"
                ),
                details={
                    "required_min_observations": required,
                    "min_series_length": min_series_len,
                    "prediction_length": prediction_length,
                },
            )

        raise ModelException(
            error_code=ErrorCode.MODEL_LOAD_FAILED,
            message="AutoGluon Chronos 模型初始化失败（请检查 autogluon 版本与模型权重路径）",
            details={"model_path": model_path, "reason": str(last_fit_exc) if last_fit_exc else None},
        )

    try:
        pred = predictor.predict(
            data=train_data,
            known_covariates=known_covariates,
        )
    except Exception as exc:
        raise ModelException(
            error_code=ErrorCode.MODEL_PREDICT_FAILED,
            message="模型预测失败",
            details={"reason": str(exc)},
        ) from exc

    output_pred_df = pred.reset_index()
    output_pred_df = replace_pred_timestamps_with_future(
        output_pred_df,
        parsed.history_df,
        prediction_length=prediction_length,
        freq=parsed.freq,
    )
    # Ensure output matches requested quantiles exactly; if model didn't output them, raise.
    _, missing = resolve_quantile_columns(output_pred_df, quantiles=quantiles)
    if missing:
        raise ModelException(
            error_code=ErrorCode.MODEL_PREDICT_FAILED,
            message="模型未返回部分请求分位数，请调整 quantiles 或检查 AutoGluon/模型版本是否支持",
            details={
                "missing_quantiles": missing,
                "available_columns": list(output_pred_df.columns),
            },
        )
    output_pred_df = filter_prediction_df_quantiles(
        output_pred_df, quantiles=quantiles, keep_mean=True, strict=True
    )
    # make timestamp JSON-serializable
    if "timestamp" in output_pred_df.columns:
        output_pred_df["timestamp"] = output_pred_df["timestamp"].astype(str)

    metrics_obj: Optional[Dict[str, Any]] = None
    requested = set(metrics)
    if not requested:
        metrics_obj = {"skipped": True, "reason": "no_metrics_requested"}
    else:
        metrics_out: Dict[str, Any] = {}
        warnings: List[Dict[str, Any]] = []

        # AutoGluon evaluate can hold out last prediction_length steps automatically.
        # If user provides test_data, concatenate to history_data for a more faithful evaluation.
        eval_df = parsed.history_df
        if parsed.test_df is not None and not parsed.test_df.empty:
            eval_df = pd.concat([parsed.history_df, parsed.test_df], ignore_index=True)
            eval_df = eval_df.sort_values(["item_id", "timestamp"]).reset_index(drop=True)

        series_lengths = eval_df.groupby("item_id").size()
        has_enough_length = (series_lengths >= (prediction_length + 1)).all()

        # WQL / WAPE
        eval_metrics_requested = requested.intersection({"WQL", "WAPE"})
        if eval_metrics_requested and has_enough_length:
            try:
                eval_tsdf = TimeSeriesDataFrame.from_data_frame(
                    eval_df,
                    id_column="item_id",
                    timestamp_column="timestamp",
                )
                try:
                    eval_res = predictor.evaluate(
                        eval_tsdf,
                        metrics=sorted(eval_metrics_requested),
                    )
                except TypeError:
                    eval_res = predictor.evaluate(eval_tsdf)
                metrics_out.update(filter_metric_result(normalize_evaluate_result(eval_res), eval_metrics_requested))
            except Exception as exc:
                warnings.append({"metric": "WQL/WAPE", "reason": "evaluate_failed", "detail": str(exc)})
        elif eval_metrics_requested and not has_enough_length:
            warnings.append(
                {
                    "metric": "WQL/WAPE",
                    "reason": "time_series_too_short_for_evaluate",
                    "min_series_length": int(series_lengths.min()) if not series_lengths.empty else 0,
                    "required_min_length": int(prediction_length + 1),
                }
            )

        # IC / IR (custom holdout split on history_data only)
        custom_requested = requested.intersection({"IC", "IR"})
        history_lengths = parsed.history_df.groupby("item_id").size()
        required_len = int(prediction_length * 2)
        eligible_items = history_lengths[history_lengths >= required_len].index.tolist()
        if custom_requested and eligible_items:
            dropped_items = set(history_lengths.index.tolist()) - set(eligible_items)
            if dropped_items:
                warnings.append(
                    {
                        "metric": "IC/IR",
                        "reason": "series_too_short_dropped",
                        "items": list(dropped_items),
                        "required_min_length": required_len,
                    }
                )
            try:
                history_for_metrics = parsed.history_df[parsed.history_df["item_id"].isin(eligible_items)].copy()
                train_df, holdout_df = split_holdout_frame(history_for_metrics, prediction_length)
                if train_df.empty or holdout_df.empty:
                    warnings.append({"metric": "IC/IR", "reason": "holdout_split_empty"})
                else:
                    train_tsdf = TimeSeriesDataFrame.from_data_frame(
                        train_df,
                        id_column="item_id",
                        timestamp_column="timestamp",
                    )

                    holdout_df = holdout_df.copy()
                    holdout_df["timestamp"] = pd.to_datetime(holdout_df["timestamp"], errors="coerce")
                    holdout_df = holdout_df.dropna(subset=["timestamp"])
                    holdout_df["item_id"] = holdout_df["item_id"].astype(str)

                    known_covariates_eval = None
                    if with_cov and parsed.known_covariates_names:
                        missing = [c for c in parsed.known_covariates_names if c not in holdout_df.columns]
                        if missing:
                            warnings.append(
                                {"metric": "IC/IR", "reason": "holdout_missing_covariates", "missing": missing}
                            )
                        else:
                            cov_df = holdout_df[["item_id", "timestamp", *parsed.known_covariates_names]].copy()
                            if cov_df[parsed.known_covariates_names].isna().any().any():
                                warnings.append({"metric": "IC/IR", "reason": "holdout_covariates_has_nan"})
                            else:
                                known_covariates_eval = TimeSeriesDataFrame.from_data_frame(
                                    cov_df,
                                    id_column="item_id",
                                    timestamp_column="timestamp",
                                )

                    if with_cov and parsed.known_covariates_names and known_covariates_eval is None:
                        pass
                    else:
                        holdout_pred = predictor.predict(
                            data=train_tsdf,
                            known_covariates=known_covariates_eval,
                        )
                        holdout_pred_df = holdout_pred.reset_index()
                        holdout_pred_df = replace_pred_timestamps_with_holdout(holdout_pred_df, holdout_df)
                        holdout_pred_df["timestamp"] = pd.to_datetime(
                            holdout_pred_df["timestamp"], errors="coerce"
                        )
                        holdout_pred_df = holdout_pred_df.dropna(subset=["timestamp"])
                        holdout_pred_df["item_id"] = holdout_pred_df["item_id"].astype(str)
                        pred_col = select_prediction_column(holdout_pred_df)

                        if pred_col is None:
                            warnings.append({"metric": "IC/IR", "reason": "prediction_column_missing"})
                        else:
                            merged = merge_holdout_predictions(holdout_df, holdout_pred_df, pred_col)
                            if merged.empty:
                                warnings.append({"metric": "IC/IR", "reason": "holdout_merge_empty"})
                            else:
                                ic_ir = compute_ic_ir(
                                    df=merged,
                                    y_true_col="target",
                                    y_pred_col=pred_col,
                                )
                                if "IC" in custom_requested:
                                    metrics_out["IC"] = ic_ir.ic if ic_ir.ic is not None else 0.0
                                    if ic_ir.ic is None:
                                        warnings.append({"metric": "IC", "reason": "ic_undefined_set_zero"})
                                if "IR" in custom_requested:
                                    metrics_out["IR"] = ic_ir.ir if ic_ir.ir is not None else 0.0
                                    if ic_ir.ir is None:
                                        warnings.append({"metric": "IR", "reason": "ir_undefined_set_zero"})
            except Exception as exc:
                warnings.append({"metric": "IC/IR", "reason": "evaluate_failed", "detail": str(exc)})
        elif custom_requested and not eligible_items:
            warnings.append(
                {
                    "metric": "IC/IR",
                    "reason": "time_series_too_short_for_evaluate",
                    "min_series_length": int(history_lengths.min()) if not history_lengths.empty else 0,
                    "required_min_length": required_len,
                }
            )
            metrics_out["IC"] = 0.0
            metrics_out["IR"] = 0.0

        if custom_requested:
            if "IC" in custom_requested and "IC" not in metrics_out:
                metrics_out["IC"] = 0.0
                warnings.append({"metric": "IC", "reason": "ic_missing_set_zero"})
            if "IR" in custom_requested and "IR" not in metrics_out:
                metrics_out["IR"] = 0.0
                warnings.append({"metric": "IR", "reason": "ir_missing_set_zero"})

        if metrics_out:
            if warnings:
                metrics_out["warnings"] = warnings
            metrics_obj = metrics_out
        else:
            metrics_obj = {
                "skipped": True,
                "reason": "metrics_unavailable",
                "detail": warnings,
            }

    result: Dict[str, Any] = {
        "predictions": output_pred_df.to_dict(orient="records"),
        "prediction_shape": list(output_pred_df.shape),
        "prediction_length": prediction_length,
        "quantiles": quantiles,
        "metrics": metrics_obj,
        "model_used": "autogluon-chronos2-zeroshot",
        "generated_at": pd.Timestamp.now().isoformat(),
    }
    if temp_dir_ctx is not None:
        temp_dir_ctx.cleanup()
    return result
