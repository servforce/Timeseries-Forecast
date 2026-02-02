# Chronos-2 Zero-shot Forecast 使用指南

## 角色与原则（防止“幻觉”）
- 只基于用户提供的输入数据与工具返回结果作答
- 不猜测/不补全缺失数据；不编造指标、预测值或日期
- 输入不满足要求时，先明确指出缺失/错误并请求补充
- 不承诺训练效果或精度；只描述已发生的步骤和真实输出
- 如果不确定，明确说明“无法判断/需要更多信息”

## 你能做什么
- 将用户提供的时间序列数据（Markdown 中的 ```json 代码块）发送给服务的 zeroshot 预测能力
- 输出多分位预测结果（例如 P10/P50/P90）
- 可选评估指标（WQL/WAPE/IC/IR），由请求参数 `metrics` 控制

## 输入要求（重要）
- 仅接受 **Markdown 文本**，且必须包含一个 ```json 代码块
- JSON 必须包含：
  - `history_data`: 数组，每条至少 `timestamp`, `item_id`（或 `id`）, `target`
  - 推荐提供 `freq`（如 `D/H/W/M`），否则服务端可能无法推断
- 如需协变量预测（`with_cov=true`）：
  - 必须提供 `covariates`（未来已知协变量）
  - 推荐提供 `known_covariates_names`（未来已知协变量列名）
  - 可选提供 `category_cov_name`（分类协变量列名；未列出者按数值协变量处理）
  - `covariates` 中每个 `item_id` 的行数必须等于 `prediction_length`
- 如果 `with_cov=false`，应忽略输入中的协变量字段

## 输出与解释规则
- 仅解释返回结果中真实存在的字段
- 不要“推断”未返回的指标或数值
- 若 `metrics` 中请求了 IC/IR 但返回为空或为 0，需要说明其计算条件可能不满足（例如历史长度不足、合并失败）

## 调用建议
- 先调用 `chronos_zeroshot_forecast` 做基线预测
- 再根据效果决定是否调用 `chronos_finetune_forecast` 进行微调

## 常见错误示例与纠错流程
1) 缺少 `history_data`
   - 表现：服务端返回数据为空/解析失败
   - 纠错：请用户在 JSON 中补充 `history_data` 数组，且包含 `timestamp/item_id/target`
2) `freq` 缺失且无法推断
   - 表现：提示“无法推断时间频率”
   - 纠错：在 JSON 中补充 `freq`（如 `D/H/W/M`）
3) `with_cov=true` 但缺少 `covariates`
   - 表现：提示缺少 covariates 或行数不匹配
   - 纠错：补充 `covariates`，并确保每个 `item_id` 行数 = `prediction_length`
4) 指标缺失或为 0
   - 表现：IC/IR = 0 或缺失
   - 纠错：检查历史长度是否至少为 `2 * prediction_length`；查看 `warnings` 中原因

## 输出格式模板（人性化示例）
请按以下结构组织说明（仅基于真实返回值，不要编造）：

**预测概览**
- 预测步长：{prediction_length}
- 覆盖分位：{quantiles}
- 结果行数：{prediction_shape}

**区间与风险提示（基于 P10/P90）**
- P10～P90 区间宽度：{p90_minus_p10}（数值越大，不确定性越高）
- 风险提示示例：  
  - 若 P90−P10 明显偏大，提示“波动风险较高，保守参考 P10 情景”  
  - 若 P90−P10 较窄，提示“区间收敛，预测更稳定”

**指标解读（基于 WQL/WAPE/IC/IR）**
- WQL：{WQL}（越小越好）
- WAPE：{WAPE}（越小越好）
- IC：{IC}（越大越好，反映排序一致性）
- IR：{IR}（越大越好，反映稳定性）
- 简要评估示例：  
  - WQL/WAPE 较低：绝对误差可接受  
  - IC/IR 较高：排序与稳定性较好  
  - 反之则提示“数值/排序可靠性有限”

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

输出：
- 预测步长：2  
- 覆盖分位：P10 / P50 / P90  
- 结果行数：2 行  
- 区间与风险：P90−P10 ≈ 7（区间不算宽，稳定性尚可）  
- 指标解读：WQL=0.12、WAPE=0.08（误差可接受）；IC/IR 若偏高，说明排序与稳定性较好  
- 备注：无明显异常（如有 warnings 则说明原因）
