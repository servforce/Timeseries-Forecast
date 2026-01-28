import { Card, Descriptions, Empty, Typography } from "antd";

const { Text } = Typography;

export default function MetricsCard(props: { metrics?: any }) {
  const metrics = props.metrics;

  const wqlRaw =
    metrics?.WQL ??
    metrics?.mean?.WQL ??
    metrics?.["mean"]?.["WQL"];
  const wapeRaw =
    metrics?.WAPE ??
    metrics?.mean?.WAPE ??
    metrics?.["mean"]?.["WAPE"];
  const icRaw =
    metrics?.IC ??
    metrics?.mean?.IC ??
    metrics?.["mean"]?.["IC"];
  const irRaw =
    metrics?.IR ??
    metrics?.mean?.IR ??
    metrics?.["mean"]?.["IR"];

  const wql = typeof wqlRaw === "number" ? Math.abs(wqlRaw) : wqlRaw;
  const wape = typeof wapeRaw === "number" ? Math.abs(wapeRaw) : wapeRaw;
  const ic = icRaw;
  const ir = irRaw;

  if (metrics == null) {
    return (
      <Card size="small" title="评估指标（WQL / WAPE / IC / IR）">
        <Empty
          description=""
        />
      </Card>
    );
  }

  if (metrics?.skipped) {
    return (
      <Card size="small" title="评估指标（WQL / WAPE / IC / IR）">
        <Empty description={`评估已跳过：${metrics.reason ?? "unknown"}`} />
      </Card>
    );
  }

  return (
    <Card size="small" title="评估指标（WQL / WAPE / IC / IR）">
      <Descriptions size="small" column={1}>
        <Descriptions.Item label="WQL">
          {typeof wql === "number" ? `${wql.toFixed(6)}（加权分位损失，越小越好）` : String(wql ?? "-")}
        </Descriptions.Item>
        <Descriptions.Item label="WAPE">
          {typeof wape === "number" ? `${wape.toFixed(6)}（加权绝对百分比误差，越小越好）` : String(wape ?? "-")}
        </Descriptions.Item>
        <Descriptions.Item label="IC">
          {typeof ic === "number" ? `${ic.toFixed(6)}（信息系数，越大越好）` : String(ic ?? "-")}
        </Descriptions.Item>
        <Descriptions.Item label="IR">
          {typeof ir === "number" ? `${ir.toFixed(6)}（信息比率，越大越好）` : String(ir ?? "-")}
        </Descriptions.Item>
        {Array.isArray(metrics?.warnings) && metrics.warnings.length > 0 && (
          <Descriptions.Item label="Warnings">
            <Text type="secondary">
              {metrics.warnings
                .map((w: any) => {
                  const metric = w?.metric ? `[${w.metric}]` : "";
                  const reason = w?.reason ? String(w.reason) : "unknown";
                  const detail = w?.detail ? ` detail=${String(w.detail)}` : "";
                  const minLen =
                    w?.min_series_length !== undefined ? ` min_series_length=${String(w.min_series_length)}` : "";
                  const reqLen =
                    w?.required_min_length !== undefined
                      ? ` required_min_length=${String(w.required_min_length)}`
                      : "";
                  return `${metric}${reason}${detail}${minLen}${reqLen}`;
                })
                .join("；")}
            </Text>
          </Descriptions.Item>
        )}
      </Descriptions>
    </Card>
  );
}
