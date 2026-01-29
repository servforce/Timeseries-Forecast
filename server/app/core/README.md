# Core 模块说明

本目录包含全局配置、异常与应用级通用逻辑。

主要文件：
- `config.py`：环境变量与运行配置（如 `CHRONOS_MODEL_PATH`、`ENABLE_MCP`、预测步长上限等）
- `exceptions.py` / `exception_handlers.py`：统一错误码与异常处理逻辑
