import axios from "axios";

type BaseParams = {
  predictionLength: number;
  quantiles: number[];
  metrics: string[];
  freq?: string;
  withCov: boolean;
  contextLength?: number;
};

type FineTuneParams = BaseParams & {
  finetuneNumSteps: number;
  finetuneLearningRate: number;
  finetuneBatchSize: number;
  contextLength?: number;
  saveModel: boolean;
};

function getApiBaseUrl() {
  return (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:5001";
}

function errorToMessage(e: any): string {
  const resp = e?.response;
  if (resp?.data) {
    const code = resp.data.error_code ?? resp.data.code;
    const msg = resp.data.message ?? resp.data.detail ?? "请求失败";
    const hints: Record<string, string> = {
      DATA_FORMAT_ERROR: "请确认 Markdown 中包含 ```json 代码块，且 JSON 可解析。",
      DATA_MISSING_COLUMNS: "请确认 history_data 至少包含 timestamp/item_id/target。",
      FUTURE_COV_MISMATCH: "请确认 future_cov 每个 item_id 的行数等于 prediction_length。",
      VALIDATION_ERROR: "请检查参数范围（prediction_length/quantiles 等）。",
      MODEL_NOT_READY: "服务依赖或模型未就绪：检查后端依赖与 CHRONOS_MODEL_PATH。",
      MODEL_LOAD_FAILED: "模型加载失败：检查模型目录是否包含 config.json/model.safetensors。",
    };
    const hint = code && hints[String(code)] ? `\n建议：${hints[String(code)]}` : "";
    return code ? `[${code}] ${msg}${hint}` : msg;
  }
  return e?.message ?? "请求失败";
}

function buildQuantileQuery(params: URLSearchParams, quantiles: number[]) {
  for (const q of quantiles) params.append("quantiles", String(q));
}

function buildMetricsQuery(params: URLSearchParams, metrics: string[]) {
  if (!metrics || metrics.length === 0) {
    params.append("metrics", "");
    return;
  }
  for (const m of metrics) params.append("metrics", String(m));
}

export const forecastApi = {
  async zeroshot(file: File, p: BaseParams) {
    const base = getApiBaseUrl();
    const url = new URL("/zeroshot/", base);
    url.searchParams.set("prediction_length", String(p.predictionLength));
    url.searchParams.set("with_cov", String(p.withCov));
    if (p.freq) url.searchParams.set("freq", p.freq);
    if (p.contextLength) url.searchParams.set("context_length", String(p.contextLength));
    buildQuantileQuery(url.searchParams, p.quantiles);
    buildMetricsQuery(url.searchParams, p.metrics);

    const form = new FormData();
    form.append("file", file);

    try {
      const resp = await axios.post(url.toString(), form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 10 * 60 * 1000,
      });
      return resp.data;
    } catch (e: any) {
      throw new Error(errorToMessage(e));
    }
  },

  async finetune(file: File, p: FineTuneParams) {
    const base = getApiBaseUrl();
    const url = new URL("/finetune/", base);
    url.searchParams.set("prediction_length", String(p.predictionLength));
    url.searchParams.set("with_cov", String(p.withCov));
    url.searchParams.set("finetune_num_steps", String(p.finetuneNumSteps));
    url.searchParams.set("finetune_learning_rate", String(p.finetuneLearningRate));
    url.searchParams.set("finetune_batch_size", String(p.finetuneBatchSize));
    url.searchParams.set("save_model", String(p.saveModel));
    if (p.contextLength) url.searchParams.set("context_length", String(p.contextLength));
    if (p.freq) url.searchParams.set("freq", p.freq);
    buildQuantileQuery(url.searchParams, p.quantiles);
    buildMetricsQuery(url.searchParams, p.metrics);

    const form = new FormData();
    form.append("file", file);

    try {
      const resp = await axios.post(url.toString(), form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 30 * 60 * 1000,
      });
      return resp.data;
    } catch (e: any) {
      throw new Error(errorToMessage(e));
    }
  },
};
