# Chronos-2 Fine-tune Forecast 使用指南

## 你能做什么
- 在用户提供的小样本数据上进行“轻量微调”，并输出预测
- 可选择保存微调后的模型（返回 `model_id`）以便后续复用

## 输入要求（与 zeroshot 相同）
- 输入是 Markdown 文本，必须包含 ```json 代码块
- JSON 必须包含 `history_data`，可选包含 `future_cov` / `known_covariates_names` / `freq`

## 重要限制（避免服务资源耗尽）
- `finetune_num_steps` 受服务端上限限制（`MAX_FINETUNE_STEPS`）
- 建议从较小步数开始（例如 100~500），逐步增加

## 参数建议
- `finetune_num_steps`: 100~1000（视数据量而定）
- `finetune_learning_rate`: 1e-5 ~ 1e-4
- `finetune_batch_size`: 16/32（视显存而定）
