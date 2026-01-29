# 数据模型（Pydantic）

该目录包含 API 请求/响应的 Pydantic 模型定义，用于：
- 输入字段校验
- OpenAPI/Swagger 文档生成

主要文件：
- `zero_shot_models.py`：Zero-shot 请求/响应结构
- `finetune_models.py`：Fine-tune 请求/响应结构（包含 `model_id`）
