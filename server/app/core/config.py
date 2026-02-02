# app/core/config.py

# app/core/config.py

import os
from pathlib import Path



class Settings:
    """
    全局配置：
    - 统一从环境变量读取
    - 提供合理的默认值，方便本地开发“一键跑起来”
    - 供 FastAPI、MCP、SDK、服务端代码统一使用
    """

    # ========= 基本应用信息 =========
    # 当前运行环境：dev / staging / prod 等
    ENV: str = os.getenv("ENVIRONMENT", "dev")

    # 是否开启调试模式（影响日志、异常返回等）
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 日志级别：debug / info / warning / error
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").upper()

    # 应用名称 & 版本（给 FastAPI、MCP、日志用）
    APP_NAME: str = os.getenv("APP_NAME", "Chronos_forecast")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")

    # ========= API 基础配置 =========
    # 统一的 API 前缀，方便将来扩展 /api/v1 等版本管理
    API_PREFIX: str = os.getenv("API_PREFIX", "/api")

    # 文档路径，可用于自定义（例如关闭外网文档）
    DOCS_URL: str = os.getenv("DOCS_URL", "/docs")
    OPENAPI_URL: str = os.getenv("OPENAPI_URL", "/openapi.json")

    # CORS 配置
    BACKEND_CORS_ORIGINS: list[str] = ["*"]


    # ========= Chronos 模型路径配置 =========
    # AutoGluon Chronos-2 本地权重路径（容器建议以 volume 挂载）
    # - 设计文档默认：server/app/models/model_save/chronos_model
    _server_dir: Path = Path(__file__).resolve().parents[2]
    CHRONOS_MODEL_PATH: str = os.getenv(
        "CHRONOS_MODEL_PATH",
        str(_server_dir / "app" / "models" / "model_save" / "chronos_model"),
    )

    # AutoGluon Chronos 模型名（不同版本可能为 Chronos2 / Chronos）
    AG_CHRONOS_MODEL_NAME: str = os.getenv("AG_CHRONOS_MODEL_NAME", "Chronos2")

    # 微调后模型保存目录（predictor.save 目录）
    FINETUNED_MODELS_DIR: str = os.getenv(
        "FINETUNED_MODELS_DIR",
        str(_server_dir / "app" / "models" / "model_save" / "finetuned_models"),
    )

    # 微调模型保留天数（到期自动清理）
    FINETUNED_MODEL_RETENTION_DAYS: int = int(os.getenv("FINETUNED_MODEL_RETENTION_DAYS", "14"))

    # 微调模型清理周期（小时）
    FINETUNED_MODEL_CLEANUP_INTERVAL_HOURS: int = int(
        os.getenv("FINETUNED_MODEL_CLEANUP_INTERVAL_HOURS", "24")
    )

    # ========= 预测默认参数配置 =========
    # 默认分位数（如果请求里没传，可以用这个）
    default_quantiles: tuple[float, ...] = (0.1, 0.5, 0.9)

    # 默认预测步长（如果请求没说清楚，可以用这个）
    default_prediction_length: int = int(
        os.getenv("DEFAULT_PREDICTION_LENGTH", "28")
    )

    # 最大允许预测步长（业务安全限制）
    max_prediction_length: int = int(
        os.getenv("MAX_PREDICTION_LENGTH", "365")
    )

    # ========= 输入限制（上传 Markdown） =========
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
    MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024
    MAX_SERIES: int = int(os.getenv("MAX_SERIES", "1000"))
    MAX_POINTS_PER_SERIES: int = int(os.getenv("MAX_POINTS_PER_SERIES", "5000"))

    # ========= 微调限制 =========
    MAX_FINETUNE_STEPS: int = int(os.getenv("MAX_FINETUNE_STEPS", "5000"))

    # ========= 模型上下文长度（AutoGluon Chronos2） =========
    # 若用户未显式传入 context_length，服务端会根据最短序列长度做自适应：
    #   context_length = min(DEFAULT_CONTEXT_LENGTH, min_series_length)
    DEFAULT_CONTEXT_LENGTH: int = int(os.getenv("DEFAULT_CONTEXT_LENGTH", "512"))

    # ========= MCP / Agent 相关配置 =========
    # 是否启用 MCP 服务能力（将来可以用来开关 MCP）
    ENABLE_MCP: bool = os.getenv("ENABLE_MCP", "true").lower() == "true"

     # MCP 端点路径
    MCP_PATH: str = "/mcp"
    
    # MCP 协议版本
    MCP_VERSION: str = "2025-11-15"

    # ========= 帮助属性 =========
    @property
    def is_prod(self) -> bool:
        """是否为生产环境"""
        return self.ENV.lower() == "prod"

    @property
    def is_debug(self) -> bool:
        """是否为调试模式"""
        return self.DEBUG


# 单例配置对象，项目其他地方直接：
# from app.core.config import settings
settings = Settings()
