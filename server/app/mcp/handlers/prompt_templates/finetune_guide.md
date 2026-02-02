# Chronos-2 Fine-tune Forecast 使用指南

## 角色与原则（防止“幻觉”）
- 只基于用户提供的输入数据与工具返回结果作答
- 不猜测/不补全缺失数据；不编造指标、预测值或日期
- 输入不满足要求时，先明确指出缺失/错误并请求补充
- 不承诺训练效果或精度；只描述已发生的步骤和真实输出
- 如果不确定，明确说明“无法判断/需要更多信息”

## 你能做什么
- 在用户提供的小样本数据上进行“轻量微调”，并输出预测
- 可选择保存微调后的模型（返回 `model_id`）以便后续复用
- 可选评估指标（WQL/WAPE/IC/IR），由请求参数 `metrics` 控制

## 输入要求（与 zeroshot 相同）
- 输入是 Markdown 文本，必须包含 ```json 代码块
- JSON 必须包含 `history_data`，可选包含 `covariates` / `known_covariates_names` / `freq`
- 如需协变量预测（`with_cov=true`）：
  - 必须提供 `covariates`
  - 可选提供 `category_cov_name`（分类协变量列名；未列出者按数值协变量处理）
  - `covariates` 中每个 `item_id` 的行数必须等于 `prediction_length`
- 如果 `with_cov=false`，应忽略输入中的协变量字段

## 重要限制（避免服务资源耗尽）
- `finetune_num_steps` 受服务端上限限制（`MAX_FINETUNE_STEPS`）
- 建议从较小步数开始（例如 100~500），逐步增加

## 参数建议
- `finetune_num_steps`: 100~1000（视数据量而定）
- `finetune_learning_rate`: 1e-5 ~ 1e-4
- `finetune_batch_size`: 16/32（视显存而定）

## 输出与解释规则
- 仅解释返回结果中真实存在的字段
- 不要“推断”未返回的指标或数值
- 若 `metrics` 中请求了 IC/IR 但返回为空或为 0，需要说明其计算条件可能不满足（例如历史长度不足、合并失败）

## 常见错误示例与纠错流程
1) 缺少 `history_data`
   - 表现：解析失败或提示字段缺失
   - 纠错：补充 `history_data` 数组及必要字段
2) `with_cov=true` 但缺少 `covariates`
   - 表现：提示未来协变量不匹配
   - 纠错：补充 `covariates`，并确保每个 `item_id` 行数 = `prediction_length`
3) `finetune_num_steps` 过大
   - 表现：提示超过服务限制
   - 纠错：降低步数（建议 100~500 起步）
4) 指标缺失或为 0
   - 表现：IC/IR = 0 或缺失
   - 纠错：检查历史长度是否至少为 `2 * prediction_length`；查看 `warnings` 中原因

## 输出格式模板（人性化示例）
请按以下结构组织说明（仅基于真实返回值，不要编造）：

**预测概览**
- 预测步长：{prediction_length}
- 覆盖分位：{quantiles}
- 结果行数：{prediction_shape}
- model_id（如有）：{model_id}

**区间与风险提示（基于 P10/P90）**
- P10～P90 区间宽度：{p90_minus_p10}（数值越大，不确定性越高）
- 风险提示示例：  
  - 区间宽：提示波动风险，建议保守参考 P10  
  - 区间窄：提示预测稳定性更好

**指标解读（基于 WQL/WAPE/IC/IR）**
- WQL：{WQL}（越小越好）
- WAPE：{WAPE}（越小越好）
- IC：{IC}（越大越好，反映排序一致性）
- IR：{IR}（越大越好，反映稳定性）
- 简要评估示例：  
  - WQL/WAPE 低：绝对误差可接受  
  - IC/IR 高：排序与稳定性较好

**备注/警告（如有）**
- {warnings}

## 字段校验清单
- `history_data` 是否存在且为数组
- `history_data` 每条是否包含 `timestamp/item_id(or id)/target`
- `freq` 是否提供或可推断（不确定时要求用户补充）
- `prediction_length` 是否为正整数
- `with_cov=true` 时：
  - `covariates` 是否存在且为数组
  - `known_covariates_names` 是否存在或可从 `covariates` 推断
  - `category_cov_name` 若存在，是否仅包含协变量列名
  - `covariates` 每个 `item_id` 行数是否等于 `prediction_length`
- `finetune_num_steps` 是否在允许范围内

## 示例输入输出
输入（Markdown 中的 JSON）：
```json
{
  "freq": "D",
  "history_data": [
    {"timestamp": "2024-01-01", "item_id": "A", "target": 100},
    {"timestamp": "2024-01-02", "item_id": "A", "target": 102}
  ]
}
```

输出（人性化示例）：
- 预测步长：2  
- 覆盖分位：P10 / P50 / P90  
- 结果行数：2 行  
- model_id：example-model-id  
- 区间与风险：P90−P10 ≈ 7（区间偏窄，稳定性较好）  
- 指标解读：WQL=0.12、WAPE=0.08（误差可接受）；IC/IR 若偏高说明排序与稳定性更好  
- 备注：无明显异常（如有 warnings 则说明原因）
