import { Card, Col, Form, InputNumber, Row, Select, Switch } from "antd";
import { useEffect } from "react";

export type ForecastMode = "zeroshot" | "finetune";

export type ForecastParams = {
  predictionLength: number;
  quantiles: number[];
  metrics: string[];
  withCov: boolean;
  freq?: string;
  finetuneNumSteps: number;
  finetuneLearningRate: number;
  finetuneBatchSize: number;
  contextLength?: number;
  saveModel: boolean;
};

type ForecastFormValues = Omit<ForecastParams, "quantiles"> & {
  quantiles: Array<number | string>;
};

const freqOptions = ["D", "H", "W", "M"].map((v) => ({ label: v, value: v }));
const quantileOptions = Array.from({ length: 19 }, (_, i) => Number(((i + 1) * 0.05).toFixed(2))).map((q) => ({
  label: q.toFixed(2),
  value: q,
}));
const metricOptions = [
  { label: "WQL", value: "WQL" },
  { label: "WAPE", value: "WAPE" },
  { label: "IC", value: "IC" },
  { label: "IR", value: "IR" },
];

export default function ParamsForm(props: {
  mode: ForecastMode;
  value: ForecastParams;
  onChange: (v: ForecastParams) => void;
}) {
  const [form] = Form.useForm<ForecastFormValues>();

  useEffect(() => {
    form.setFieldsValue(props.value as unknown as ForecastFormValues);
  }, [props.value, form]);

  function emit() {
    const v = form.getFieldsValue(true);
    const qRaw = (v.quantiles ?? []) as Array<number | string>;
    const q = qRaw
      .map((x) => (typeof x === "number" ? x : Number(String(x).trim())))
      .filter((n) => Number.isFinite(n))
      .map((n) => Number(n))
      .filter((n) => n > 0 && n < 1);
    const mRaw = (v.metrics ?? []) as Array<string | number>;
    const m = mRaw
      .map((x) => String(x).trim().toUpperCase())
      .filter((x) => Boolean(x));
    props.onChange({ ...(v as unknown as ForecastParams), quantiles: q, metrics: m });
  }

  return (
    <Card size="small" title="参数配置">
      <Form
        form={form}
        layout="vertical"
        initialValues={props.value}
        onValuesChange={emit}
      >
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item label="Prediction Length" name="predictionLength" rules={[{ required: true }]}>
              <InputNumber min={1} max={365} style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col span={12} />
        </Row>

        <Row gutter={12}>
          <Col span={12}>
            <Form.Item label="Freq（可选）" name="freq">
              <Select allowClear placeholder="自动推断" options={freqOptions} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="With Covariates" name="withCov" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={12}>
          <Col span={12}>
            <Form.Item label="Context Length" name="contextLength">
              <InputNumber min={1} max={100000} style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col span={12} />
        </Row>

        <Form.Item label="Quantiles（多选）" name="quantiles">
          <Select
            mode="multiple"
            showSearch
            optionFilterProp="label"
            placeholder="请选择分位数（0.05~0.95，步长 0.05）"
            options={quantileOptions}
          />
        </Form.Item>

        <Form.Item label="Metrics（多选）" name="metrics">
          <Select
            mode="multiple"
            showSearch
            optionFilterProp="label"
            placeholder="请选择评估指标（WQL/WAPE/IC/IR）"
            options={metricOptions}
          />
        </Form.Item>

        {props.mode === "finetune" && (
          <Card size="small" title="Finetune 参数" style={{ marginTop: 8 }}>
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item label="Steps" name="finetuneNumSteps">
                  <InputNumber min={1} max={5000} style={{ width: "100%" }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Batch Size" name="finetuneBatchSize">
                  <InputNumber min={1} max={512} style={{ width: "100%" }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item label="Learning Rate" name="finetuneLearningRate">
                  <InputNumber
                    min={1e-8}
                    max={1}
                    step={1e-5}
                    style={{ width: "100%" }}
                  />
                </Form.Item>
              </Col>
              <Col span={12} />
            </Row>
            <Form.Item label="Save Model" name="saveModel" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Card>
        )}
      </Form>
    </Card>
  );
}
