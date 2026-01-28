from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    timestamp: datetime = Field(..., description="时间戳，例如 '2022-10-18'")
    item_id: str = Field(..., description="序列 ID（建议字段名 item_id；兼容 id）")
    target: float = Field(..., description="目标值")

    class Config:
        extra = "allow"


class FutureCovItem(BaseModel):
    timestamp: datetime = Field(..., description="未来时间步时间戳")
    item_id: str = Field(..., description="序列 ID（建议字段名 item_id；兼容 id）")

    class Config:
        extra = "allow"


class MarkdownPayload(BaseModel):
    """
    Markdown 中 JSON 解析后的结构（供服务端校验用）。
    """

    freq: Optional[str] = Field(default=None, description="时间频率（推荐必填），如 D/H/W/M")
    known_covariates_names: Optional[List[str]] = Field(
        default=None,
        description="未来已知协变量列名（推荐必填）",
    )
    history_data: List[HistoryItem] = Field(..., description="历史数据列表")
    future_cov: Optional[List[FutureCovItem]] = Field(
        default=None,
        description="未来已知协变量列表（with_cov=true 时必填）",
    )


class ForecastResponse(BaseModel):
    predictions: List[Dict[str, Any]] = Field(..., description="预测结果（行记录）")
    prediction_shape: List[int] = Field(..., description="预测结果 DataFrame 形状")
    prediction_length: int = Field(..., description="预测步长")
    quantiles: List[float] = Field(..., description="输出分位数")
    metrics: Optional[Dict[str, Any]] = Field(default=None, description="评估指标（需提供 test_data）")
    model_used: str = Field(..., description="使用的模型标识")
    generated_at: str = Field(..., description="生成时间 ISO 字符串")
