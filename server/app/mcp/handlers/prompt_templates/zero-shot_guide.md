# Chronos-2 Zero-shot Forecast 使用指南

## 你能做什么
- 将用户提供的时间序列数据（Markdown 中的 ```json 代码块）发送给服务的 zeroshot 预测能力
- 输出多分位预测结果（例如 P10/P50/P90）

## 输入要求（重要）
- 仅接受 **Markdown 文本**，并且必须包含一个 ```json 代码块
- JSON 必须包含：
  - `history_data`: 数组，每条至少 `timestamp`, `item_id`（或 `id`）, `target`
  - 推荐提供 `freq`（如 `D/H/W/M`），否则服务端可能无法推断
- 如需协变量预测（`with_cov=true`）：
  - 必须提供 `future_cov`（未来已知协变量）
  - 推荐提供 `known_covariates_names`（未来已知协变量列名）
  - `future_cov` 中每个 `item_id` 的行数必须等于 `prediction_length`

## 调用建议
- 先调用 `chronos_zeroshot_forecast` 做基线预测
- 再根据效果决定是否调用 `chronos_finetune_forecast` 进行微调
