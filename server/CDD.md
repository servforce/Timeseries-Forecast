# Chronos-2 时间序列预测引擎微服务任务书（AutoGluon 版）

## 1 项目结构
> 说明：目录与文件命名以 `CDD1.md` 为主线设计（便于团队协作与后续 K8s/工作流嵌入），实现时可在现有代码结构基础上逐步迁移，不要求一次性完全照搬。

```
forecast_server/
├── server/
│   ├── app/                                 # 应用层
│   │   ├── api/                             # 接口层（REST）
│   │   │   ├── routes/                      # 路由注册
│   │   │   │   ├── fintune_forecast.py      # POST /finetune（建议命名：finetune_forecast.py）
│   │   │   │   ├── zero-shot_forecast.py    # POST /zeroshot（建议命名：zero_shot_forecast.py）
│   │   │   │   └── health.py                # GET  /health
│   │   │   ├── __init__.py
│   │   │   ├── main.py                      # 路由聚合
│   │   │   └── README.md                    # API 文档（输入限制/示例/错误码）
│   │   ├── core/                            # 核心配置与异常处理层（保持现有逻辑）
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── exception_handlers.py
│   │   │   ├── exceptions.py
│   │   │   └── README.md
│   │   ├── mcp/                             # MCP 服务层（工作流/Agent 嵌入）
│   │   │   ├── handlers/                    # 工具 / 资源 / 提示词注册
│   │   │   │   ├── prompt_templates/        # 提示词模版
│   │   │   │   │   ├── zero-shot_guide.md
│   │   │   │   │   └── finetune_guide.md
│   │   │   │   ├── __init__.py
│   │   │   │   ├── prompt.py                # Prompts 注册
│   │   │   │   ├── resources.py             # Resources 注册（输入模版/说明）
│   │   │   │   └── tools.py                 # Tools 注册（zeroshot/finetune）
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── server.py                    # MCP Server 入口（可集成到 FastAPI）
│   │   ├── models/                          # 模型层（请求体/响应体/权重目录）
│   │   │   ├── model_save/
│   │   │   │   └── chronos_model/           # Chronos-2 权重（本地挂载/预置）
│   │   │   ├── __init__.py
│   │   │   ├── finetune_models.py           # Pydantic：微调接口请求/响应
│   │   │   ├── zero-shot_models.py          # Pydantic：zeroshot 接口请求/响应（建议命名：zero_shot_models.py）
│   │   │   └── README.md
│   │   └── services/                        # 业务逻辑服务层
│   │       ├── __init__.py
│   │       ├── finetune_forecast.py         # AutoGluon Chronos2 fine-tune & predict
│   │       ├── zero-shot_forecast.py        # AutoGluon Chronos2 zeroshot predict（建议命名：zero_shot_forecast.py）
│   │       ├── process.py                   # Markdown→JSON→TimeSeriesDataFrame
│   │       └── README.md
│   ├── main.py                              # 项目入口：挂载 API + MCP
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── .dockerignore
├── .gitignore
└── docker-compose.yml
```

## 2 任务需求
### 2.1 项目概述
- 本地保存 Chronos-2 权重（镜像外挂载），通过 **AutoGluon TimeSeries** 加载并构建 `TimeSeriesPredictor`。
- 提供两类预测接口（符合 RESTful）：`/zeroshot` 与 `/finetune`，分别对应零样本与在线微调 + 预测。
- **输入方式优化**：前端只允许上传 **Markdown 文档**（文档中包含 JSON 数据），避免用户在网页直接粘贴大 JSON 导致卡顿/崩溃。
- 提供 MCP Server（prompts/resources/tools），将 `/zeroshot`、`/finetune` 能力包装为可被 Agent/工作流调用的工具。
- 提供 Dockerfile 与 docker-compose，支持本地一键启动；并为 K8s/工作流嵌入预留部署形态（探针/挂载/资源）。

### 2.2 接口层设计（api/）
#### 2.2.1 路由层（routes/）
**`zero-shot_forecast.py`**：`POST /zeroshot`（建议模块名：`zero_shot_forecast.py`）
- 入参：`multipart/form-data`
  - `file`: 上传的 Markdown 文件（`.md`），包含 JSON 输入
  - `prediction_length`: 预测步长（Query 或 Form）
  - `quantiles`: 分位数（Query 或 Form，默认 `[0.1, 0.5, 0.9]`）
  - `freq`: 时间频率（可选，如 `D/H/W/M`，不传则由服务端推断/要求用户提供）
  - `device`: 推理设备（默认 `cuda`）
  - `with_cov`: 是否使用协变量（默认 `false`）
- 行为：解析 Markdown → 提取 JSON → 转换为 `TimeSeriesDataFrame` → `TimeSeriesPredictor.fit(fine_tune=False)` → `predictor.predict()` 输出结果。
- 输出：预测结果（含分位数）、输入校验信息、模型版本信息（用于排障/复现）。

**`fintune_forecast.py`**：`POST /finetune`（建议模块名：`finetune_forecast.py`）
- 入参：`multipart/form-data`
  - `file`: 上传的 Markdown 文件（`.md`），包含 JSON 输入
  - `prediction_length`
  - `quantiles`
  - `device`
  - `with_cov`
  - fine-tune 超参数（可设默认，允许用户覆盖）：
    - `finetune_num_steps`（默认 1000）
    - `finetune_learning_rate`（默认 `1e-4`）
    - `finetune_batch_size`（默认 32）
    - `context_length`（可选，默认按经验值）
- 行为：解析 Markdown → 构造训练数据 → `TimeSeriesPredictor.fit(fine_tune=True, ...)`（或同一次 fit 内包含 zero-shot/finetune 两个 suffix）→ 预测输出；必要时保存微调后的 predictor/权重到 `model_save/`。
- 输出：预测结果 +（可选）`model_id`（用于后续复用微调模型）。

**`health.py`**：`GET /health`
- 用于 K8s 存活/就绪探针（可加入模型是否已加载、GPU 可用性、磁盘挂载可读等信息）。

#### 2.2.2 主函数入口
**`main.py`**：完成路由聚合（`/zeroshot`、`/finetune`、`/health`）。

#### 2.2.3 说明文档
**`README.md`**：接口说明、输入限制、错误码、示例（Markdown 输入模版）。

### 2.3 核心及异常处理层设计（core/）
> 本层保持“现有异常处理逻辑”风格：统一错误码、统一错误响应结构、全局异常捕获。

**`config.py`**：全局配置
- 统一从环境变量读取（模型路径、默认 device、最大上传大小、最大序列/点数等）
- 提供默认值，方便本地开发“一键跑起来”
- 供 FastAPI / MCP / SDK / 服务层统一使用

**`exception_handlers.py`**：FastAPI 全局异常处理器
- 业务异常（BaseAppException）
- 请求参数验证异常（Pydantic）
- HTTP 标准异常（HTTPException）
- 未预期内部异常（Exception）

**`exceptions.py`**：统一异常与错误码定义
- 错误码体系（参数错误/数据错误/模型错误/系统错误）
- 结构化错误响应（`error_code/message/details/request_id`）

### 2.4 MCP 服务层设计（mcp/）
#### 2.4.1 MCP 工具、资源、提示词层（handlers/）
**`prompt.py`**：注册 prompts
- `chronos_zeroshot_guide`：指导 LLM 如何构造 Markdown 输入、如何选择参数
- `chronos_finetune_guide`：指导 LLM 进行微调任务的输入要求与安全边界

**`tools.py`**：注册 tools（与 API 一一对应）
- `chronos_zeroshot_forecast(file, prediction_length, quantiles, freq, with_cov, device)` → 调用 `POST /zeroshot`
- `chronos_finetune_forecast(file, prediction_length, quantiles, freq, with_cov, device, finetune_num_steps, finetune_learning_rate, finetune_batch_size, context_length)` → 调用 `POST /finetune`
- 可选：`chronos_health()` → 调用 `GET /health`

**`resources.py`**：注册 resources
- `chronos://overview`：服务说明（输入限制、字段含义、最佳实践）
- `chronos://sample_markdown`：标准 Markdown 输入模版（内含 JSON）
- `chronos://error_codes`：错误码与排障建议

#### 2.4.2 主函数入口
**`server.py`**：用 fastmcp 创建 MCP server，并可集成到 FastAPI（例如 `app.mount("/mcp", mcp_app)`）。

#### 2.4.3 说明文档
**`README.md`**：MCP 接入方式、tools/resources/prompts 列表、示例调用。

### 2.5 模型层设计（models/）——基于 AutoGluon
#### 2.5.1 模型权重（model_save/）
- `model_save/chronos_model/`：本地 Chronos-2 权重目录（`config.json`、`model.safetensors` 等）
- 原则：
  - 权重通过 volume 挂载到容器（避免镜像过大）
  - 生产环境建议“版本化目录 + 只读挂载”

#### 2.5.2 请求体/响应体（Pydantic）
> 注意：接口实际通过上传 Markdown 文件输入；Pydantic 用于**解析后 JSON 的校验**与**响应结构固定化**。

**`zero-shot_models.py`**（建议命名：`zero_shot_models.py`，建议包含）
- `ZeroShotForecastRequestParsed`：从 Markdown JSON 解析后的结构（`history_data / future_cov / prediction_length / quantiles / known_covariates_names / freq`）
- `ForecastResponse`：统一预测响应（预测结果、分位数、元信息）

**`finetune_models.py`**（建议包含）
- `FineTuneForecastRequestParsed`：在 zeroshot 的基础上，增加微调超参数字段（或作为 Query/Form 参数单独校验）
- `FineTuneForecastResponse`：返回 `model_id`（可选）+ 预测结果

### 2.6 服务层设计（services/）
**`process.py`**：解析与数据构造（Markdown → JSON → AutoGluon）
- 从 Markdown 中提取 JSON（推荐规则：提取第一个 ```json 代码块；或约定 `<!-- chronos-input -->` 区块）
- 将 `history_data` 转为 `TimeSeriesDataFrame`（至少包含：`item_id`、`timestamp`、`target`）
- 协变量处理：
  - `known_covariates_names`：显式从输入提供（或由 `future_cov` 的字段自动推断）
  - 历史中除基础列外的字段：
    - 若在 `known_covariates_names` 中，则作为 known covariates 的历史部分
    - 否则作为 past covariates
  - `future_cov` 必须覆盖 `known_covariates_names` 且每个 `item_id` 的长度等于 `prediction_length`
- 输入限制（关键，防止 OOM/卡死）：
  - Markdown 文件大小（例如 `MAX_UPLOAD_MB`）
  - 最大序列数（例如 `MAX_SERIES`）
  - 每条序列最大点数（例如 `MAX_POINTS_PER_SERIES`）
  - 预测步长上限（例如 `MAX_PRED_LEN`）

**`zero-shot_forecast.py`**：zeroshot 预测服务（AutoGluon，建议模块名：`zero_shot_forecast.py`）
- 通过 `TimeSeriesPredictor.fit(fine_tune=False)` 构建 predictor（可缓存）
- 调用 `predictor.predict(data, known_covariates=...)` 输出预测
- 输出分位数：使用 predictor 支持的分位数输出（或配置 `quantile_levels`）

**`finetune_forecast.py`**：微调 + 预测服务（AutoGluon）
- 通过 `TimeSeriesPredictor.fit(fine_tune=True, fine_tune_steps/ lr / batch_size...)`
- 保存微调模型（可选）：写入 `model_save/` 并返回 `model_id`
- 若同一次 fit 需要输出 zeroshot 与 finetuned 对比：使用 `ag_args.name_suffix` 组合训练（便于 A/B 评估）

### 2.7 主项目入口（main.py）
**`main.py`**：使用 `app.mount` 一键挂载 API 与 MCP，支持 `uvicorn` 启动，默认暴露端口 `5001`。

## 3 输入数据说明（Markdown 上传规范）
### 3.1 为什么要用 Markdown 上传
- 避免网页直接粘贴大 JSON 导致浏览器卡顿（DOM/编辑器渲染、复制粘贴开销大）。
- Markdown 既可读又可版本化（可存 Git、可做审阅），且天然适合被 MCP resources/prompts 引用。

### 3.2 Markdown 模版约定（推荐）
Markdown 中包含一个 `json` 代码块，结构如下（字段名以 `item_id` 为主；服务端可兼容 `id` 作为别名）：

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

### 3.3 字段与限制（服务端强校验）
- `history_data` 必填：每条至少包含 `timestamp、item_id、target`
- `future_cov`：
  - 当 `known_covariates_names` 非空或 `with_cov=true` 时必填
  - 每个 `item_id` 的未来行数必须等于 `prediction_length`
- `freq`：
  - 推荐必填（如 `D/H/W/M`），减少推断错误
- `known_covariates_names`：
  - 推荐必填：避免“哪些是未来已知协变量”歧义
  - 必须在 `history_data` 与 `future_cov` 中同时存在
- 数值类型：
  - `target` 与协变量必须为数值（float/int），缺失值允许但需明确策略（如前端填充/服务端丢弃/报错）

### 3.4 上传限制建议（防止卡死/炸显存）
- Markdown 文件大小上限：例如 2–10 MB（由 `MAX_UPLOAD_MB` 配置）
- 最大序列数：例如 1000
- 每条序列最大历史点数：例如 5000
- 最大预测步长：例如 365（按业务定）
- 超限返回明确错误码 + 修复建议（如“请抽样/分批预测/降低步长/减少序列数”）

## 4 模型构造示例（AutoGluon Chronos2）
> 以 AutoGluon 官方 Chronos2 用法为基准，服务端以“本地权重路径”作为 `model_path`。

```python
from autogluon.timeseries import TimeSeriesPredictor

predictor = TimeSeriesPredictor(
    prediction_length=HORIZON,
    target="target",
    eval_metric="WQL",
    known_covariates_names=known_covs,
    freq="D",
)

predictor.fit(
    train_data=ag_train,                 # TimeSeriesDataFrame
    enable_ensemble=False,
    hyperparameters={
        "Chronos2": [
            {
                "ag_args": {"name_suffix": "_ZeroShot"},
                "model_path": "/models/chronos_model",
                "fine_tune": False,
                "device": "cuda",
            },
            {
                "ag_args": {"name_suffix": "_Finetuned"},
                "model_path": "/models/chronos_model",
                "fine_tune": True,
                "device": "cuda",
                "fine_tune_steps": 3000,
                "fine_tune_lr": 3e-5,
                "fine_tune_batch_size": 32,
            },
        ]
    },
)

pred = predictor.predict(ag_train, known_covariates=known_covs_future)
```

## 5 容器部署（Docker / Compose / K8s）
### 5.1 Dockerfile
- 代码与依赖打包进镜像
- 模型权重目录以 volume 方式挂载（例如挂载到 `/models/chronos_model`）
- 暴露端口 `5001`

### 5.2 docker-compose（开发/演示）
- 一键启动服务
- 挂载模型目录与配置环境变量（device、默认 prediction_length 上限、上传大小限制等）

### 5.3 K8s（工作流嵌入的基础）
- 探针：`GET /health`
- GPU：通过 `resources.limits` + `nodeSelector/tolerations` 调度
- 模型挂载：PV/PVC 或 initContainer 拉取到 EmptyDir

## 6 前端交互设计规范

为配合 Markdown 输入模式并提供良好的用户体验，前端页面应包含以下核心模块与交互逻辑。

### 6.1 布局设计
* **左侧：配置与上传区**
    * **文件上传**：
        * 提供拖拽上传区域，仅限 `.md` 文件后缀。
        * **预检逻辑**：上传后前端应读取文件前 1KB 内容，简单扫描是否包含 ` ```json ` 关键字，若未发现立即提示用户“文档格式错误，未检测到 JSON 数据块”。
    * **参数配置表单**：
        * `Prediction Length` (步长): 数字输入框，默认 **28**，必填。
        * `Quantiles` (分位数): 多选标签或输入框，默认 `0.1, 0.5, 0.9`。
        * `Device`: 下拉选择 `CUDA` / `CPU`，默认 `CUDA`。
        * `With Covariates`: 开关（Boolean），默认关闭。开启后提示用户“确保 Markdown 中包含 future_cov”。
        * **Mode 切换**：
            * **Zero-shot**: 默认模式，仅展示基础参数。
            * **Finetune**: 选中后展开高级参数：
                * `Steps`: 默认 1000。
                * `Learning Rate`: 默认 1e-4。
                * `Batch Size`: 默认 32。
                * **Save Model**: 开关，默认开启（是否保存微调后模型）。

* **右侧：可视化结果区**
    * **状态展示**：
        * **Empty**: 提示“请上传数据并点击预测”。
        * **Loading**: 显示进度条或 Spinner（由于 Finetune 耗时较长，建议增加“预计耗时 x 分钟”的提示）。
        * **Success**: 渲染图表。
    * **图表组件** (推荐 ECharts / Recharts)：
        * **多序列切换**：顶部提供 Dropdown 或 Tabs 切换不同的 `item_id`。
        * **时间轴 (X轴)**：解析 `timestamp` 字段。
        * **数值轴 (Y轴)**：展示 `target`。
        * **图层**：
            * **历史数据**：黑色实线 (History)。
            * **预测中位数**：蓝色实线 (P50)。
            * **置信区间**：浅蓝色半透明填充区域 (P10 - P90)，直观展示不确定性。

### 6.2 交互流程
1. 用户设置 `Prediction Length` = 7。
2. 用户上传包含 JSON 的 Markdown 文件。
3. 点击“开始预测”按钮。
4. 前端构造 `multipart/form-data` 请求 POST `/zeroshot` 或 `/finetune`。
5. 接收后端返回的 JSON 数据：
   ```json
   {
     "predictions": [...],
     "quantiles": [0.1, 0.5, 0.9],
     "prediction_length": 7
   }
   ```
6. 前端按 `item_id` 分组，把历史段与预测段拼接渲染：
   - 历史段来自上传数据里的 `history_data`
   - 预测段来自返回的 `predictions`（包含 `mean` 与所选分位数列）

### 6.3 页面与路由（MVP）
- `/`：预测页（默认 Zero-shot）
  - Tab1：Zero-shot（调用 `/zeroshot/`）
  - Tab2：Finetune（调用 `/finetune/`）
- `/docs`（可选）：内置帮助页（展示 Markdown 模版、字段解释、错误码）

### 6.4 组件与状态管理
- **核心组件**
  - `MarkdownUploader`：拖拽/选择文件、预检、展示文件名/大小
  - `ParamsForm`：预测步长/分位数/device/with_cov/finetune 超参（Tab 控制显示）
  - `ResultChart`：折线 + 区间带（P10-P90），支持多 `item_id` 切换
  - `ResultTable`：表格展示预测明细，支持复制/分页/下载
  - `Toast/ErrorPanel`：统一错误提示（后端错误码 → 用户可读提示）
- **状态管理**
  - 简单场景：React state + `useReducer`
  - 多页面/复杂场景：Zustand / Redux（择一）
  - 请求层：`fetch` 或 `axios`，统一超时/重试/错误映射

### 6.5 文件上传与性能策略（避免“粘贴 JSON 卡顿”）
- 禁止在页面中直接编辑超大 JSON（默认只展示“摘要”）：
  - 展示解析到的 `item_id` 数量、每条序列长度、是否检测到 `future_cov`
  - 可选提供“预览前 N 行”
- 上传前端限制（与后端保持一致）：
  - 文件大小（例如 10MB）
  - 预测步长上限（例如 365）
- 解析策略：
  - 前端仅做轻量预检（是否包含 ```json）
  - 复杂解析与校验统一交给后端（保证一致性）

### 6.6 错误提示规范（建议按错误码映射）
- `DATA_FORMAT_ERROR`：提示“Markdown 中 JSON 无法解析，请检查 ```json 代码块”
- `DATA_MISSING_COLUMNS`：提示“缺少必要字段：timestamp/item_id/target …”
- `FUTURE_COV_MISMATCH`：提示“future_cov 每个 item_id 行数需等于 prediction_length”
- `MODEL_NOT_READY`：提示“服务缺少依赖或模型未配置（CHRONOS_MODEL_PATH）”

### 6.7 技术栈建议（前端）
- 框架：Next.js / Vite + React（二选一）
- UI：Ant Design / MUI（二选一）
- 图表：ECharts（推荐，区间带实现简单）
- 表格：AntD Table / TanStack Table
- 文件上传：原生 `<input type="file">` + 拖拽增强
