import { Button, Card, Space, Table } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useMemo } from "react";
import { downloadAsCsv, downloadAsJson } from "../utils/data";

export default function ResultTable(props: { predictions: any[]; quantiles?: number[] }) {
  const columns = useMemo<ColumnsType<any>>(() => {
    const keys = new Set<string>();
    for (const row of props.predictions ?? []) {
      Object.keys(row || {}).forEach((k) => keys.add(k));
    }

    const quantileKeys =
      (props.quantiles ?? [])
        .map((q) => String(q))
        .filter((k) => keys.has(k));

    const other = Array.from(keys).filter(
      (k) => !["item_id", "timestamp", "mean", ...quantileKeys].includes(k),
    );

    const ordered = ["item_id", "timestamp", "mean", ...quantileKeys, ...other];
    return ordered
      .filter((k) => keys.has(k))
      .map((k) => ({
        title: k,
        dataIndex: k,
        key: k,
        width: k === "timestamp" ? 160 : undefined,
      }));
  }, [props.predictions, props.quantiles]);

  return (
    <Card
      size="small"
      title="预测明细"
      extra={
        <Space>
          <Button onClick={() => downloadAsJson(props.predictions, "predictions.json")}>
            下载 JSON
          </Button>
          <Button onClick={() => downloadAsCsv(props.predictions, "predictions.csv")}>
            下载 CSV
          </Button>
        </Space>
      }
    >
      <Table
        size="small"
        rowKey={(_, idx) => String(idx)}
        columns={columns}
        dataSource={props.predictions}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        scroll={{ x: true, y: 360 }}
      />
    </Card>
  );
}
