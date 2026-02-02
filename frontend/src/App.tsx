import { useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Drawer,
  Layout,
  Row,
  Space,
  Tabs,
  Typography,
  message,
} from "antd";
import type { TabsProps } from "antd";

import { forecastApi } from "./api/client";
import MarkdownUploader, { MarkdownFileState } from "./components/MarkdownUploader";
import ParamsForm, { ForecastMode, ForecastParams } from "./components/ParamsForm";
import ResultChart from "./components/ResultChart";
import ResultTable from "./components/ResultTable";
import MetricsCard from "./components/MetricsCard";
import TutorialDrawer from "./components/TutorialDrawer";
import { buildSeriesView, tryParseMarkdownPayloadSummary } from "./utils/data";
import { sampleMarkdown } from "./utils/markdown";

const { Header, Content } = Layout;
const { Title, Text } = Typography;

export default function App() {
  const [mode, setMode] = useState<ForecastMode>("zeroshot");
  const [fileState, setFileState] = useState<MarkdownFileState | null>(null);
  const [params, setParams] = useState<ForecastParams>({
    predictionLength: 28,
    quantiles: [0.1, 0.5, 0.9],
    metrics: ["WQL", "WAPE"],
    withCov: false,
    freq: undefined,
    finetuneNumSteps: 1000,
    finetuneLearningRate: 1e-4,
    finetuneBatchSize: 32,
    contextLength: 512,
    saveModel: true,
    modelId: undefined,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const [tutorialOpen, setTutorialOpen] = useState(false);
  const [lastModelId, setLastModelId] = useState<string | null>(null);

  const summary = useMemo(() => {
    if (!fileState?.text) return null;
    return tryParseMarkdownPayloadSummary(fileState.text);
  }, [fileState?.text]);

  const view = useMemo(() => {
    if (!fileState?.text || !result?.predictions) return null;
    return buildSeriesView({
      markdownText: fileState.text,
      predictions: result.predictions,
      quantiles: result.quantiles ?? params.quantiles,
      predictionLength: result.prediction_length ?? params.predictionLength,
    });
  }, [fileState?.text, result, params.quantiles]);

  const tabs: TabsProps["items"] = [
    { key: "zeroshot", label: "Zero-shot" },
    { key: "finetune", label: "Finetune" },
  ];

  async function onRun() {
    setError(null);
    setResult(null);

    if (!fileState?.file) {
      setError("请先上传 Markdown 文件（.md），并确保包含 ```json 代码块。");
      return;
    }

    setLoading(true);
    try {
      const apiParams = {
        predictionLength: params.predictionLength,
        quantiles: params.quantiles.length ? params.quantiles : [0.1, 0.5, 0.9],
        metrics: params.metrics ?? [],
        freq: params.freq,
        withCov: params.withCov,
        contextLength: params.contextLength,
      };

      let resp: any;
      if (mode === "zeroshot") {
        resp = await forecastApi.zeroshot(fileState.file, apiParams);
      } else {
        resp = await forecastApi.finetune(fileState.file, {
          ...apiParams,
          finetuneNumSteps: params.finetuneNumSteps,
          finetuneLearningRate: params.finetuneLearningRate,
          finetuneBatchSize: params.finetuneBatchSize,
          contextLength: params.contextLength,
          saveModel: params.saveModel,
          modelId: params.modelId?.trim() ? params.modelId.trim() : undefined,
        });
      }

      setResult(resp);
      if (resp?.model_id) {
        setLastModelId(resp.model_id);
        message.success(`微调完成，model_id=${resp.model_id}`);
      } else {
        message.success("预测完成");
      }
    } catch (e: any) {
      const msg = e?.message || "请求失败";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Layout className="app-shell" style={{ height: "100%" }}>
      <Header className="app-header" style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <Title level={4} className="brand-title" style={{ color: "#fff", margin: 0 }}>
          Timeseries Forecast
        </Title>
        <Text className="brand-subtitle">
          基于Chronos-2的zeroshot和finetune预测服务
        </Text>
        <div style={{ flex: 1 }} />
        <Space>
          <Button className="ghost-button" onClick={() => setHelpOpen(true)}>输入模版</Button>
          <Button className="ghost-button" onClick={() => setTutorialOpen(true)}>使用教程</Button>
        </Space>
      </Header>

      <Content className="content-wrap">
        <Row gutter={[16, 16]} style={{ minHeight: "calc(100vh - 64px - 48px)" }}>
          <Col xs={24} lg={8} style={{ height: "100%" }}>
            <Card className="panel panel-left" style={{ height: "100%" }} bodyStyle={{ height: "100%" }} styles={{ body: { height: "100%", padding: 20 } }}>
              <Space className="section-stack" direction="vertical" style={{ width: "100%" }} size="middle">
                <Tabs
                  items={tabs}
                  activeKey={mode}
                  onChange={(k) => setMode(k as ForecastMode)}
                />

                <MarkdownUploader value={fileState} onChange={setFileState} />

                {summary && (
                  <Alert
                    type="info"
                    showIcon
                    message="输入摘要"
                    description={
                      <div>
                        <div>series: {summary.seriesCount}</div>
                        <div>history_rows: {summary.historyRows}</div>
                        <div>has_covariates: {String(summary.hasCovariates)}</div>
                        <div>known_covariates: {summary.knownCovariatesCount}</div>
                        <div>
                          series_len(min/max): {summary.minSeriesLength}/{summary.maxSeriesLength}
                        </div>
                      </div>
                    }
                  />
                )}

                {summary && summary.minSeriesLength > 0 && params.predictionLength > summary.minSeriesLength && (
                  <Alert
                    type="warning"
                    showIcon
                    message="参数提示"
                    description={
                      <div>
                        当前最短序列长度为 {summary.minSeriesLength}，但 prediction_length=
                        {params.predictionLength}。若后端报“time series too short”，请增加历史长度或降低 prediction_length。
                      </div>
                    }
                  />
                )}

                <ParamsForm mode={mode} value={params} onChange={setParams} lastModelId={lastModelId} />

                {error && <Alert type="error" showIcon message={error} />}

                <Button
                  type="primary"
                  block
                  className="primary-action"
                  loading={loading}
                  onClick={onRun}
                  disabled={!fileState?.file}
                >
                  {mode === "zeroshot" ? "开始预测（Zero-shot）" : "开始微调并预测（Finetune）"}
                </Button>
              </Space>
            </Card>
          </Col>

          <Col xs={24} lg={16} style={{ height: "100%" }}>
            <Card className="panel panel-right" style={{ height: "100%" }} bodyStyle={{ height: "100%" }} styles={{ body: { height: "100%", padding: 20 } }}>
              {!result && !loading && (
                <Alert
                  type="info"
                  showIcon
                  message="请上传数据并点击预测"
                  description="建议使用右上角“输入模版”生成 Markdown 输入。"
                />
              )}

              {view && (
                <Space direction="vertical" style={{ width: "100%" }} size="large">
                  {result?.model_id && (
                    <Alert
                      type="success"
                      showIcon
                      message="微调模型已保存"
                      description={
                        <Space direction="vertical" size="small" style={{ width: "100%" }}>
                          <Text>
                            model_id：<Text code copyable>{String(result.model_id)}</Text>
                          </Text>
                          <Button
                            size="small"
                            onClick={() => {
                              setMode("finetune");
                              setParams((prev) => ({ ...prev, modelId: String(result.model_id) }));
                              message.success("已填入 model_id，可直接复用预测");
                            }}
                          >
                            一键复用本次 model_id
                          </Button>
                          <Button
                            size="small"
                            onClick={() => {
                              setParams((prev) => ({ ...prev, modelId: undefined }));
                              message.success("已取消复用，可重新微调");
                            }}
                          >
                            取消复用
                          </Button>
                        </Space>
                      }
                    />
                  )}
                  <MetricsCard metrics={result?.metrics} />
                  <ResultChart view={view} />
                  <ResultTable
                    predictions={result?.predictions ?? []}
                    quantiles={result?.quantiles ?? params.quantiles}
                  />
                </Space>
              )}
            </Card>
          </Col>
        </Row>
      </Content>

      <Drawer
        title="Markdown 输入模版"
        placement="right"
        onClose={() => setHelpOpen(false)}
        open={helpOpen}
        width={520}
      >
        <Alert
          type="info"
          showIcon
          message="建议"
          description="将 数据JSON格式化后放到markdown文档的 ```json 代码块里上传，详见下面示例"
          style={{ marginBottom: 12 }}
        />
        <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f6", padding: 12 }}>
          {sampleMarkdown}
        </pre>
      </Drawer>

      <TutorialDrawer open={tutorialOpen} onClose={() => setTutorialOpen(false)} />
    </Layout>
  );
}
