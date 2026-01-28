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
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const [tutorialOpen, setTutorialOpen] = useState(false);

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
        });
      }

      setResult(resp);
      if (resp?.model_id) {
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
    <Layout style={{ height: "100%" }}>
      <Header style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <Title level={4} style={{ color: "#fff", margin: 0 }}>
          Timeseries Forecast
        </Title>
        <Text style={{ color: "rgba(255,255,255,0.75)" }}>
          基于Chronos-2的zeroshot和finetune预测服务
        </Text>
        <div style={{ flex: 1 }} />
        <Space>
          <Button onClick={() => setHelpOpen(true)}>输入模版</Button>
          <Button onClick={() => setTutorialOpen(true)}>使用教程</Button>
        </Space>
      </Header>

      <Content style={{ padding: 16 }}>
        <Row gutter={16} style={{ height: "calc(100vh - 64px - 32px)" }}>
          <Col span={8} style={{ height: "100%" }}>
            <Card style={{ height: "100%" }} bodyStyle={{ height: "100%" }}>
              <Space direction="vertical" style={{ width: "100%" }} size="middle">
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
                        <div>has_future_cov: {String(summary.hasFutureCov)}</div>
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

                <ParamsForm mode={mode} value={params} onChange={setParams} />

                {error && <Alert type="error" showIcon message={error} />}

                <Button
                  type="primary"
                  block
                  loading={loading}
                  onClick={onRun}
                  disabled={!fileState?.file}
                >
                  {mode === "zeroshot" ? "开始预测（Zero-shot）" : "开始微调并预测（Finetune）"}
                </Button>
              </Space>
            </Card>
          </Col>

          <Col span={16} style={{ height: "100%" }}>
            <Card style={{ height: "100%" }} bodyStyle={{ height: "100%" }}>
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
          description="将 JSON 放到 ```json 代码块里上传，避免直接粘贴大 JSON 导致网页卡顿。"
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
