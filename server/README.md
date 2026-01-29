# Chronos Forecast Service

基于 Amazon Chronos-2 模型构建的高性能时间序列预测微服务。本项目不仅提供标准的 RESTful API，还集成了 **MCP (Model Context Protocol)**，可作为 LLM (如 Claude Desktop, Cursor) 的直接工具使用。

## ✨ 核心特性

- **基于 Chronos-2**: 利用预训练的大型时间序列模型，支持 Zero-shot (零样本) 预测、以及微调版本模型预测。
- **多模态协变量支持**: 支持传入**历史协变量** (如过去的价格) 和**未来协变量** (如未来的促销计划)。
- **多分位预测**: 支持配置预测分位数 (如 P10, P50, P90)，提供概率预测能力。
- **MCP 集成**: 内置 MCP Server，支持 LLM 直接调用工具读取文档、进行预测分析。
- **高性能架构**: 基于 FastAPI + Uvicorn，支持异步并发与线程池推理。
-
## 📌 指标与评估逻辑（当前实现）
- **WQL/WAPE**：由 AutoGluon evaluate 输出
- **IC/IR**：在历史数据中切分验证区间计算，需要至少 `2 * prediction_length` 的历史长度  
  - 训练区间：前 `n - m`  
  - 验证区间：最后 `m`  
  - 预测输出仍为未来 `n+1..n+m`（不受指标切分影响）

## 🛠️ 技术栈

- **Python**: 3.12+
- **Web 框架**: FastAPI
- **ML 框架**: AutoGluon TimeSeries（Chronos-2 接入）, PyTorch
- **数据处理**: Pandas, Polars
- **MCP**: FastMCP

## 🔧系统框架

### 核心层（core）
- **`config.py`**：全局配置文件，测试开发变量存储。
- **`exception_handle.py`**：FastAPI全局异常处理。

### 服务层（services）
- **`process.py`**:解析 Markdown（提取 ```json）、做输入校验与规模限制。
- **`zero_shot_forecast.py`**:Zero-shot 预测（AutoGluon Chronos2）。
- **`finetune_forecast.py`**:Fine-tune + 预测（AutoGluon Chronos2），可选保存 `model_id`。
- **`metrics_helpers.py`/`custom_metrics.py`**：IC/IR 计算与对齐逻辑。

### 接口层

#### API接口（api）
- **`/zeroshot`**：Zero-shot 预测（上传 Markdown 文件）。
- **`/finetune`**：微调 + 预测（上传 Markdown 文件）。
- **`health.py`**：（get：/）：健康检查接口

#### MCP服务（mcp）
- **`prompt.py`**：内置 `chronos_zeroshot_guide` / `chronos_finetune_guide`。
- **`resources.py`**：暴露 `chronos://sample_markdown` 输入模版。
- **`tools.py`**：注册 `chronos_zeroshot_forecast` / `chronos_finetune_forecast` 工具。

### 模型层
- `models/model_save/chronos_model`: Chronos-2 权重挂载目录（建议 volume 挂载）
- `models/model_save/finetuned_models`: 微调模型保存目录（`model_id` 子目录）

## 🚀 快速开始

### 1. 环境安装

推荐使用 Conda 或 pip：

```bash
# 安装依赖
pip install -r server/requirements.txt
```

### 2. 启动服务
```bash
uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
```
- 支持MCP服务和API服务一键启动（app.mount）
### 3. API文档
启动后访问：
- **Swagger UI** http://localhost:5001/docs
- **Redoc** http://localhost:5001/redoc

### 4.MCP服务
启动后访问
- **sse支持**：http://localhost:5001/mcp/sse

### 5.Docker
- Dockerfile：打包代码，创建挂载目录，下载环境依赖，暴露端口5001。
- docker-compose 一键编排创建容器，挂载模型权重的大文件目录。

## 🌐 Frontend（可选）
- 前端代码：`frontend/`（Vite + React + Ant Design + ECharts）
- 启动（本机）：`cd frontend && npm install && npm run dev`

## 🔗 相关文档
- API 说明：`server/app/api/README.md`
- 服务层说明：`server/app/services/README.md`
- MCP 说明：`server/app/mcp/README.md`
