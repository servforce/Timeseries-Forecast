import logging
import json
from typing import Any, Dict, List, Optional

from app.services.finetune_forecast import finetune_forecast_from_markdown_bytes
from app.services.zero_shot_forecast import zeroshot_forecast_from_markdown_bytes

logger = logging.getLogger(__name__)

def register_tools(mcp) -> None :
    '''
    注册MCP工具到服务器
    '''

    @mcp.tool()
    async def chronos_zeroshot_forecast(
        markdown: str,
        prediction_length: int,
        quantiles: List[float],
        metrics: Optional[List[str]] = None,
        with_cov: bool = False,
        freq: Optional[str] = None,
        device: str = "cuda",
    ) -> str:
        """
        Zero-shot 预测工具（AutoGluon Chronos2）。

        入参为 Markdown 文本（需包含 ```json 代码块），避免直接传大 JSON 造成编辑器卡顿。
        """
        logger.info(
            "MCP zeroshot 调用: prediction_length=%d, with_cov=%s, device=%s",
            prediction_length,
            with_cov,
            device,
        )

        result = zeroshot_forecast_from_markdown_bytes(
            markdown.encode("utf-8"),
            prediction_length=prediction_length,
            quantiles=quantiles,
            metrics=metrics or ["WQL", "WAPE"],
            with_cov=with_cov,
            device=device,
            freq=freq,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def chronos_finetune_forecast(
        markdown: str,
        prediction_length: int,
        quantiles: List[float],
        metrics: Optional[List[str]] = None,
        with_cov: bool = False,
        freq: Optional[str] = None,
        device: str = "cuda",
        finetune_num_steps: int = 1000,
        finetune_learning_rate: float = 1e-4,
        finetune_batch_size: int = 32,
        context_length: Optional[int] = None,
        save_model: bool = True,
    ) -> str:
        """
        Fine-tune + 预测工具（AutoGluon Chronos2）。
        """
        logger.info(
            "MCP finetune 调用: prediction_length=%d, steps=%d, device=%s, save_model=%s",
            prediction_length,
            finetune_num_steps,
            device,
            save_model,
        )

        result = finetune_forecast_from_markdown_bytes(
            markdown.encode("utf-8"),
            prediction_length=prediction_length,
            quantiles=quantiles,
            metrics=metrics or ["WQL", "WAPE"],
            with_cov=with_cov,
            device=device,
            freq=freq,
            finetune_num_steps=finetune_num_steps,
            finetune_learning_rate=finetune_learning_rate,
            finetune_batch_size=finetune_batch_size,
            context_length=context_length,
            save_model=save_model,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
