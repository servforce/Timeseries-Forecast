import { Card, Select, Space } from "antd";
import ReactECharts from "echarts-for-react";
import { useMemo, useState } from "react";
import type { SeriesView } from "../utils/data";

export default function ResultChart(props: { view: SeriesView }) {
  const itemIds = props.view.itemIds;
  const [selectedId, setSelectedId] = useState(itemIds[0]);

  const option = useMemo(() => {
    const data = props.view.byItemId[selectedId];
    if (!data) return {};

    const historyX = data.history.map((p) => p.timestamp);
    const historyY = data.history.map((p) => p.target);
    const predX = data.predictions.map((p) => p.timestamp);
    // Requirement: show P50 (0.5) as main forecast line, fallback to mean if 0.5 missing.
    const p50Y = data.predictions.map((p) => {
      const q50 = (p as any)["0.5"];
      if (typeof q50 === "number") return q50;
      const m = p.mean;
      return typeof m === "number" ? m : null;
    });

    const categories = Array.from(new Set([...historyX, ...predX])).sort((a, b) => a.localeCompare(b));

    const band = data.band; // {lowKey, highKey} optional
    const qLow = band ? data.predictions.map((p) => (p as any)[band.lowKey] ?? null) : [];
    const qHigh = band ? data.predictions.map((p) => (p as any)[band.highKey] ?? null) : [];

    const bandUpperMinusLower =
      band
        ? qHigh.map((v, i) => {
            const hi = typeof v === "number" ? v : null;
            const lo = typeof qLow[i] === "number" ? (qLow[i] as number) : null;
            if (hi === null || lo === null) return null;
            return hi - lo;
          })
        : [];

    return {
      tooltip: { trigger: "axis" },
      legend: { data: ["History", "P50", band ? `${band.lowKey}-${band.highKey}` : undefined].filter(Boolean) },
      grid: { left: 48, right: 18, top: 40, bottom: 40 },
      xAxis: { type: "category", boundaryGap: false, data: categories },
      yAxis: { type: "value" },
      series: [
        {
          name: "History",
          type: "line",
          data: historyY.map((y, i) => [historyX[i], y]),
          showSymbol: false,
          lineStyle: { width: 2, color: "#111827" },
        },
        ...(band
          ? [
              // lower line (stack base)
              {
                name: `${band.lowKey}-${band.highKey}`,
                type: "line",
                data: qLow.map((y, i) => [predX[i], y]),
                stack: "confidence",
                showSymbol: false,
                lineStyle: { opacity: 0 },
                areaStyle: { opacity: 0 },
              },
              // upper-minus-lower as area band
              {
                name: `${band.lowKey}-${band.highKey}`,
                type: "line",
                data: bandUpperMinusLower.map((y, i) => [predX[i], y]),
                stack: "confidence",
                showSymbol: false,
                lineStyle: { opacity: 0 },
                areaStyle: { color: "rgba(59,130,246,0.18)" },
              },
            ]
          : []),
        {
          name: "P50",
          type: "line",
          data: p50Y.map((y, i) => [predX[i], y]),
          showSymbol: false,
          lineStyle: { width: 2, color: "#2563eb" },
        },
      ],
    };
  }, [props.view, selectedId]);

  return (
    <Card
      size="small"
      title="预测可视化"
      extra={
        <Space>
          <span>item_id</span>
          <Select
            value={selectedId}
            onChange={setSelectedId}
            options={itemIds.map((id) => ({ label: id, value: id }))}
            style={{ width: 220 }}
          />
        </Space>
      }
    >
      <ReactECharts option={option} style={{ height: 420, width: "100%" }} />
    </Card>
  );
}
