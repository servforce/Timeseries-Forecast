from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.zero_shot_models import ForecastResponse, MarkdownPayload


class FineTuneResponse(ForecastResponse):
    model_id: Optional[str] = Field(default=None, description="微调模型 ID（可选）")
    model_saved_at: Optional[str] = Field(default=None, description="微调模型保存时间（ISO）")
    model_retention_days_left: Optional[int] = Field(default=None, description="微调模型剩余保留天数")


class FineTuneRequestParsed(MarkdownPayload):
    """
    微调接口：Markdown JSON 解析后的结构（除数据外，微调超参数通常来自 Query/Form）。
    """

    # 预留扩展：如果未来希望把超参数也写进 Markdown JSON，可在此补充字段并做校验。
    pass
