# 📂 API 服务接口说明（Markdown 上传版）

## Zero-shot 预测（/zeroshot）
- `POST /zeroshot/`
- 入参：`multipart/form-data`
  - `file`：Markdown 文件（`.md`），必须包含一个 ```json 代码块
- Query 参数：
  - `prediction_length`：预测步长（必填）
  - `quantiles`：分位数（默认 `[0.1,0.5,0.9]`，可重复传参）
  - `metrics`：评估指标（默认 `WQL,WAPE`，可选 `IC/IR`）
  - `freq`：时间频率（如 `D/H/W/M`；不填则尝试推断）
  - `with_cov`：是否使用协变量（默认 `false`）
  - `context_length`：上下文长度（默认 512）
  - `device`：`cuda/cpu`（默认 `cuda`，MCP 工具专用）

## Fine-tune + 预测（/finetune）
- `POST /finetune/`
- 入参同 `/zeroshot/`
- 额外 Query 参数（微调超参数）：
  - `finetune_num_steps`（默认 1000）
  - `finetune_learning_rate`（默认 `1e-4`）
  - `finetune_batch_size`（默认 32）
  - `context_length`（可选）
  - `save_model`：是否保存微调模型并返回 `model_id`（默认 `true`）

## Markdown JSON 输入格式
Markdown 中包含一个 `json` 代码块，结构示例：

```json
{
  "freq": "D",
  "known_covariates_names": ["price", "promo_flag", "weekday"],
  "history_data": [
    {"timestamp": "2022-09-24", "item_id": "item_1", "target": 10.0, "price": 1.20, "promo_flag": 0, "weekday": 6},
    {"timestamp": "2022-09-25", "item_id": "item_1", "target": 11.0, "price": 1.22, "promo_flag": 0, "weekday": 0}
  ],
  "future_cov": [
    {"timestamp": "2022-10-01", "item_id": "item_1", "price": 1.36, "promo_flag": 0, "weekday": 6},
    {"timestamp": "2022-10-02", "item_id": "item_1", "price": 1.37, "promo_flag": 0, "weekday": 0}
  ]
}
```

字段说明：
- `history_data`：必填，每条至少包含 `timestamp、item_id(或id)、target`
- `freq`：推荐必填（减少推断失败）
- `with_cov=true` 时：
  - 必须提供 `future_cov`
  - 推荐提供 `known_covariates_names`
  - `future_cov` 中每个 `item_id` 的行数必须等于 `prediction_length`

指标说明：
- WQL/WAPE：由 AutoGluon evaluate 输出
- IC/IR：历史数据切分计算，需要至少 `2 * prediction_length` 的历史长度

## 健康检查（/health）
- `GET /health`
- 用于 K8s 存活/就绪探针
