import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Query, UploadFile, status

from app.core.exceptions import DataException, ErrorCode, ModelException
from app.models.zero_shot_models import ForecastResponse
from app.services.zero_shot_forecast import zeroshot_forecast_from_markdown_bytes
from app.services.job_queue import job_queue, job_record_to_dict


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Zero-shot Forecast"])


@router.post("/", response_model=ForecastResponse)
async def zeroshot_forecast(
    file: UploadFile = File(..., description="Markdown 文件（包含 ```json ... ``` 输入）"),
    prediction_length: int = Query(..., gt=0, description="预测步长"),
    quantiles: List[float] = Query(default=[0.1, 0.5, 0.9], description="输出分位数"),
    metrics: List[str] = Query(default=["WQL", "WAPE"], description="评估指标（可选：WQL,WAPE,IC,IR）"),
    freq: Optional[str] = Query(default=None, description="时间频率（如 D/H/W/M；不填则尝试推断）"),
    with_cov: bool = Query(default=False, description="是否使用协变量（covariates + known_covariates_names）"),
    context_length: int = Query(default=512, gt=0, description="上下文长度（默认 512，会自动按最短序列长度截断）"),
) -> Dict[str, Any]:
    if not file.filename.lower().endswith(".md"):
        raise DataException(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="仅支持上传 .md Markdown 文件",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"filename": file.filename},
        )

    content = await file.read()
    try:
        result = zeroshot_forecast_from_markdown_bytes(
            content,
            prediction_length=prediction_length,
            quantiles=quantiles,
            metrics=metrics,
            with_cov=with_cov,
            freq=freq,
            context_length=context_length,
        )
        return result
    except (DataException, ModelException):
        raise
    except Exception as exc:
        logger.exception("zeroshot 预测失败")
        raise ModelException(
            error_code=ErrorCode.MODEL_PREDICT_FAILED,
            message="zeroshot 预测失败",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"reason": str(exc)},
        ) from exc


@router.post("/async")
async def zeroshot_forecast_async(
    file: UploadFile = File(..., description="Markdown 文件（包含 ```json ... ``` 输入）"),
    prediction_length: int = Query(..., gt=0, description="预测步长"),
    quantiles: List[float] = Query(default=[0.1, 0.5, 0.9], description="输出分位数"),
    metrics: List[str] = Query(default=["WQL", "WAPE"], description="评估指标（可选：WQL,WAPE,IC,IR）"),
    freq: Optional[str] = Query(default=None, description="时间频率（如 D/H/W/M；不填则尝试推断）"),
    with_cov: bool = Query(default=False, description="是否使用协变量（covariates + known_covariates_names）"),
    context_length: int = Query(default=512, gt=0, description="上下文长度（默认 512，会自动按最短序列长度截断）"),
) -> Dict[str, Any]:
    if not file.filename.lower().endswith(".md"):
        raise DataException(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="仅支持上传 .md Markdown 文件",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"filename": file.filename},
        )

    content = await file.read()
    record = job_queue.submit(
        "zeroshot",
        zeroshot_forecast_from_markdown_bytes,
        content,
        prediction_length=prediction_length,
        quantiles=quantiles,
        metrics=metrics,
        with_cov=with_cov,
        freq=freq,
        context_length=context_length,
        params={
            "prediction_length": prediction_length,
            "with_cov": with_cov,
            "quantiles": quantiles,
            "metrics": metrics,
        },
    )
    result = job_record_to_dict(record)
    result["status_url"] = f"/jobs/{record.job_id}"
    return result
