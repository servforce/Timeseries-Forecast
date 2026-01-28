# app/mcp/handlers/resources.py

from typing import Any, Dict
from app.core.config import settings


def register_resources(mcp) -> None:
    """
    注册 MCP 资源（提供文档、说明、示例输入等），供 LLM 读取。
    """

    # -------------------------------------------------------
    # 1. 服务总览说明
    # -------------------------------------------------------
    @mcp.resource("chronos://overview")
    async def chronos_overview() -> Dict[str, Any]:
        """
        Chronos 时间序列预测服务的说明文档（供 LLM 阅读）。
        """
        return {
            "app_name": settings.APP_NAME,
            "description": (
                "这是一个基于 Amazon Chronos-2（AutoGluon TimeSeries 接入）的时间序列预测服务 MCP。\n"
                "建议以 Markdown（包含 ```json 代码块）作为输入，避免复制大 JSON 导致卡顿。\n"
                "工具拆分为 zeroshot 与 finetune 两类。"
            ),
            "capabilities": [
                "多 id 时间序列预测",
                "多步预测（prediction_length 可配置）",
                "多分位预测（quantiles 可配置）",
                "支持历史/未来协变量",
                "可选择是否使用微调模型（use_finetuned）",
            ],
            "recommended_tools": ["chronos_zeroshot_forecast", "chronos_finetune_forecast"],
            "use_cases": [
                "按 SKU + 仓库预测未来 7 天销量",
                "在给定价格/促销计划下估计未来需求",
                "库存与补货优化",
            ],
        }

    # -------------------------------------------------------
    # 2. 示例输入模板
    # -------------------------------------------------------
    @mcp.resource("chronos://sample_markdown")
    async def chronos_sample_markdown() -> Dict[str, Any]:
        """
        提供标准 Markdown 输入模板（内含 JSON）。
        """
        return {
            "description": "标准 Markdown 输入模版（包含 ```json 代码块）。",
            "markdown": (
                "# Chronos Forecast Input\n\n"
                "```json\n"
                "{\n"
                "  \"freq\": \"D\",\n"
                "  \"known_covariates_names\": [\"price\", \"promo_flag\", \"weekday\"],\n"
                "  \"history_data\": [\n"
                "    {\"timestamp\": \"2022-09-24\", \"item_id\": \"item_1\", \"target\": 10.0, \"price\": 1.20, \"promo_flag\": 0, \"weekday\": 6},\n"
                "    {\"timestamp\": \"2022-09-25\", \"item_id\": \"item_1\", \"target\": 11.0, \"price\": 1.22, \"promo_flag\": 0, \"weekday\": 0}\n"
                "  ],\n"
                "  \"future_cov\": [\n"
                "    {\"timestamp\": \"2022-10-01\", \"item_id\": \"item_1\", \"price\": 1.36, \"promo_flag\": 0, \"weekday\": 6},\n"
                "    {\"timestamp\": \"2022-10-02\", \"item_id\": \"item_1\", \"price\": 1.37, \"promo_flag\": 0, \"weekday\": 0}\n"
                "  ]\n"
                "}\n"
                "```\n"
            ),
        }

    @mcp.resource("chronos://error_codes")
    async def chronos_error_codes() -> Dict[str, Any]:
        """
        常见错误码与排障建议。
        """
        return {
            "DATA_FORMAT_ERROR": "Markdown 中 JSON 不可解析：请使用 ```json 代码块包裹。",
            "DATA_MISSING_COLUMNS": "缺少必要字段：history_data 至少要有 timestamp/item_id/target；future_cov 至少要有 timestamp/item_id。",
            "FUTURE_COV_MISMATCH": "future_cov 每个 item_id 的行数必须等于 prediction_length。",
            "MODEL_NOT_READY": "AutoGluon 未安装或模型不可用：请确认已安装依赖并配置 CHRONOS_MODEL_PATH。",
        }
