# 业务逻辑的核心实现

- **`process.py`**：
  - 解析用户上传的 Markdown（提取 ```json 代码块）
  - JSON 结构校验、字段归一（`id`→`item_id`）、规模限制（序列数/点数/步长）
  - 构造用于 AutoGluon 的标准化 DataFrame（历史与未来已知协变量）
  - `with_cov=false` 时忽略协变量字段

- **`zero_shot_forecast.py`**：
  - 基于 AutoGluon TimeSeries 的 Chronos2 Zero-shot 预测实现

- **`finetune_forecast.py`**：
  - 基于 AutoGluon TimeSeries 的 Chronos2 Fine-tune + 预测实现
  - 可选保存微调后的 predictor（返回 `model_id`）

- **`custom_metrics.py`**：
  - IC/IR 计算（Spearman 排名相关）

- **`metrics_helpers.py`**：
  - 预测时间戳对齐（未来区间 / holdout 区间）
  - IC/IR 合并逻辑（timestamp 或位置对齐）
  
