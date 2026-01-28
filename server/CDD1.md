# Chronos时间序列预测引擎预测微服务任务书

## 1 项目结构
```
forecast_server/
├── server/
│   ├── app/                             # 应用层
│   │   ├── api/                         # 接口层
│   │   │   ├── routes/                  # 注册路由
│   │   │   │   ├── fintune_forecast.py
│   │   │   │   ├── zero-shot_forecast.py
│   │   │   │   └── health.py
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   └── README.md
│   │   ├── core/                           # 核心配置与异常处理层
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── exception_handlers.py
│   │   │   ├── exceptions.py
│   │   │   └── README.md
│   │   ├── mcp/                            #mcp服务层
│   │   │   ├── handlers/                   #工具、提示词、资源注册
│   │   │   │   ├── prompt_templates/    #提示词模版
│   │   │   │   │   ├── zero-shot_guide.md
│   │   │   │   │   ├── finetune_guide.md
│   │   │   │   ├── __init__.py
│   │   │   │   ├── prompt.py
│   │   │   │   ├── resources.py
│   │   │   │   └──  tools.py
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── server.py
│   │   ├── models/                         #模型层
│   │   │   ├── model_save/
│   │   │   │   ├── chronos_model/          #保存模型权重
│   │   │   ├── __init__.py
│   │   │   ├── finetune_models.py
│   │   │   ├── zero-shot_models.py
│   │   │   └──README.md
│   │   └── services/                       # 业务逻辑服务层
│   │   │   ├── __init__.py
│   │   │   ├── finetune_forecast.py
│   │   │   ├── zero-shot_forecast.py
│   │   │   ├── process.py
│   │   │   └──  README.md
│   │   ├── main.py                         # 项目入口
│   │   ├── __init__.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── .dockerignore
├── .gitignore
├── docker-compese.yml
```

## 2 任务需求
### 2.1项目概述
- 本地保存Chronos-2模型，通过autogluon加载并构建predictor。设计API接口（符合RESTFul协议），分别设计zeroshot接口和finetune接口，将用户上传的markdown文档里的json数据构建成chronos-2需要的timeseries形式，完成预测任务。同时设计mcp接口，包括提示词、资源、工具，对应API接口，提供SDK供agent调用。给出Dockerfile封装预测服务，同时给出dockercompose支持一键编排，给出gitignore支持github开源。

### 2.2 接口层设计（api/）
#### 2.2.1 路由层（routes/）
**`zero-shot_forecast.py`** :POST（/zeroshot），调用服务层脚本，解析用户在前端界面上传的markdown文档中的json格式的数据，转换为autogluon的predictor需要的timeseries格式。fit接口“finetune”参数设置为false，使用zeroshot预测输出结果。支持单变量或协变量预测，默认设备“cuda”，支持预测步长手动输入。

**`finetune_forecast.py`**：POST（/finetune），调用服务层脚本，解析用户在前端界面上传的markdown文档中的json格式的数据，转换为autogluon的predictor需要的timeseries格式。fit接口“finetune”参数设置为True，使用finetune预测输出结果。支持单变量或协变量预测，默认设备“cuda”，支持预测步长手动输入。

#### 2.2.2 主函数入口
**`main.py`**：完成各接口的路由聚合。

#### 2.2.3 说明文档
**`README.md`**：对接口层的设计说明。

### 2.3 核心及异常处理层设计（core/）
**`config.py`**： 全局配置：
- 统一从环境变量读取
- 提供合理的默认值，方便本地开发“一键跑起来”
- 供 FastAPI、MCP、SDK、服务端代码统一使用

**`exception_handlers.py`**：FastAPI 全局异常处理器
目标：
- 为 Chronos 时间序列预测服务提供统一的异常处理和错误响应格式
- 参考行业最佳实践，支持：
  - 业务异常（BaseAppException）
  - 请求参数验证异常（Pydantic）
  - HTTP 标准异常（Starlette HTTPException）
  - 未预期的内部异常（Exception）

**`exceptions.py`**：应用统一异常与错误码定义，参考行业最佳实践，为 Chronos 时间序列预测服务提供：
- 统一的错误码体系
- 统一的业务异常基类
- 结构化错误响应的数据结构

### 2.4 MCP服务层设计（mcp/）
#### 2.4.1 MCP工具、资源、提示词层（handlers/）
**`prompt.py`**:@mcp.prompt注册提示词，读取提示词模版（单独的markdown文档设计）。

**`tools.py`**：@mcp.tools注册zeroshot和finetune预测工具。

**`prompt.py`**：@mcp.resources注册 MCP 资源（提供文档、说明、示例输入等），供 LLM 读取。

#### 2.4.2 主函数入口
**`main.py`**:用fastmcp完成MCP服务器实现（集成工具、提示词、资源），创建MCP服务器实例并集成到FastAPI。

#### 2.4.3 说明文档
**`README.md`**：MCP服务层的说明文档。

### 2.5 模型层设计（models/）

#### 2.5.1 模型权重（model_save/）
- 保存模型权重（pkl，safetensors、config.json等文件）

#### 2.5.2 请求体
**`finetune_models.py`**:使用pydantic定义finetune预测接口请求体。

**`zero-shot_models.py`**：使用pydantic定义zeroshot预测接口请求体。

### 2.6 服务层设计（services/）
**`process.py`**:完成对markdown文档中json数据的解析，转化为GluonTS格式。（TimeSeriesDataFrame ：item_id,timestamp,target,covarites）

**`zero-shot_forecast.py`**：加载模型并使用TimeSeriesPredictor.fit（finetune=False）构建预测器。调用predict接口完成预测。

**`finetune_forecast.py`**：加载模型并使用TimeSeriesPredictor.fit（finetune=True）构建预测器。调用predict接口完成预测。

### 2.7 主项目入口（main.py）
**`main.py`**:使用app.mount 一键挂载mcp和api接口，支持uvicorn一键启动API和mcp，暴露端口5001。

## 3 输入数据说明
- json格式的markdown文档，包括id列（每条时间序列的唯一识别标识，要求用户定义为item_id），timestamp列（连续频率的时间列，要求用户定义列名为timestamp，target列（要预测的目标列，要求用户定义为target），covarites列（多个协变量列，可以分为已知协变量和过去协变量，已知协变量需要提供预测步长时间段内的数据，过去协变量仅需要过去数据）。下面给出具体实例：
```
{
  "history_data": [
    {
      "timestamp": "2022-09-24",
      "item_id": "item_1",
      "target": 10.0,
      "price": 1.20,
      "promo_flag": 0,
      "weekday": 6
    },
    {
      "timestamp": "2022-09-25",
      "item_id": "item_1",
      "target": 11.0,
      "price": 1.22,
      "promo_flag": 0,
      "weekday": 0
    },...
    ...
    {
      "timestamp": "2022-09-29",
      "item_id": "item_2",
      "target": 9.8,
      "price": 1.02,
      "promo_flag": 0,
      "weekday": 4
    },
    {
      "timestamp": "2022-09-30",
      "item_id": "item_2",
      "target": 10.0,
      "price": 1.05,
      "promo_flag": 1,
      "weekday": 5
    }
  ],
  "future_cov": [
    {
      "timestamp": "2022-10-01",
      "item_id": "item_1",
      "price": 1.36,
      "promo_flag": 0,
      "weekday": 6
    },
    {
      "timestamp": "2022-10-02",
      "item_id": "item_1",
      "price": 1.37,
      "promo_flag": 0,
      "weekday": 0
    },
    ...
    {
      "timestamp": "2022-10-01",
      "item_id": "item_2",
      "price": 1.06,
      "promo_flag": 0,
      "weekday": 6
    },
    {
      "timestamp": "2022-10-02",
      "item_id": "item_2",
      "price": 1.07,
      "promo_flag": 0,
      "weekday": 0
    },
    ...]
}
```
- 在请求体中定义预测步长（prediction_length）和分位数输出（quantiles），均设置默认值，推理设备默认设置为cuda。

- 根据autogluon要求，需要提供未来已知协变量的名字字段，即要求用户传完json文件，还需要传入协变量列名，输入给predictor作为know_covarites传入。

- 微调接口设置默认超参数，finetune_num_steps设置为1000，finetune_batch_size设置为32，finetune_learning_rate设置为1e-4，支持用户自行调整。

## 4 模型构造示例
```
Chronos-2（模型参数量约为120M）:完成zeroshot和微调预测，包括单变量预测和协变量预测。调用示例（详见autogluon:https://auto.gluon.ai/stable/tutorials/timeseries/forecasting-chronos.html）

predictor = TimeSeriesPredictor(
    prediction_length=HORIZON,
    target="Target",
    eval_metric='WQL',
    known_covariates_names=known_covs_ag, # 显式指定 Known，剩下的会自动识别为 Past
    freq='D'
)

predictor.fit(
    train_data=ag_train,
    enable_ensemble=False,
    hyperparameters={
        "Chronos2": [
            {
                "ag_args": {"name_suffix": "_ZeroShot"},
                "model_path": '/root/autodl-tmp/store/chronos2_model',
                "fine_tune": False,
                "context_length": CONTEXT_LEN,
                "batch_size": BATCH,
                "device": 'cuda',
            },
            {
                "ag_args": {"name_suffix": "_Finetuned"},
                "model_path": '/root/autodl-tmp/store/chronos2_model',
                "fine_tune": True,
                "context_length": CONTEXT_LEN,
                "batch_size": BATCH,
                "device": 'cuda', 
                "fine_tune_steps": 3000,
                "fine_tune_lr": 3e-5,   
                "fine_tune_batch_size": 32,
                "cross_learning": False,
            }
        ]
    }
)
pred = predictor.predict(ag_train,prediction_length)
```

## 5 容器部署
- Dockerfile：挂载model的模型权重文件路径，其他文件打包进容器，命名为timeseries_forecast。












