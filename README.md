# Timeseries Forecast（Chronos-2）

Timeseries Forecast 是一个基于 Amazon Chronos-2 的时间序列预测系统，提供：
- Zero-shot / Finetune 预测
- 多分位输出（P10/P50/P90 等）
- 指标评估（WQL/WAPE/IC/IR）
- MCP（Model Context Protocol）工具接入，支持 LLM 调用

## 目录导航
- 前端说明：[frontend/README.md](frontend/README.md)
- 后端说明：[server/README.md](server/README.md)
- API 说明：[server/app/api/README.md](server/app/api/README.md)
- 服务层说明：[server/app/services/README.md](server/app/services/README.md)
- MCP 说明：[server/app/mcp/README.md](server/app/mcp/README.md)
- 模型与数据结构：[server/app/models/README.md](server/app/models/README.md)
- 核心配置/异常：[server/app/core/README.md](server/app/core/README.md)

## 快速开始
### 1) 后端
```bash
pip install -r server/requirements.txt
export CHRONOS_MODEL_PATH=/path/to/chronos_model
uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
```

### 2) 前端
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```
前端默认地址：`http://localhost:5173`

### 3) 一键启动（可选）
```bash
bash scripts/dev.sh
```

## 数据输入要点
- 输入为 Markdown，必须包含 ```json 代码块
- 必填字段：`history_data`（含 `timestamp/item_id(or id)/target`）
- 推荐提供 `freq`（如 D/H/W/M）
- 若开启协变量：必须提供 `future_cov`，且长度 = `prediction_length`

## 指标说明（WQL/WAPE/IC/IR）
- WQL/WAPE：由 AutoGluon evaluate 输出
- IC/IR：在历史数据上切分验证区间计算（需要至少 `2 * prediction_length` 的历史长度）
- 预测输出保持未来区间 n+1…n+m，不受指标切分影响

## MCP / Ollama 说明
后端启动后 MCP SSE 地址：`http://localhost:5001/mcp/sse`  
可用 `ollama_client.py` 连接并调用工具。
