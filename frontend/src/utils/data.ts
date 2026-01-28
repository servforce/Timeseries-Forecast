import { extractJsonFromMarkdown } from "./markdown";

export type PayloadSummary = {
  seriesCount: number;
  historyRows: number;
  hasFutureCov: boolean;
  knownCovariatesCount: number;
  minSeriesLength: number;
  maxSeriesLength: number;
};

export function tryParseMarkdownPayloadSummary(markdownText: string): PayloadSummary | null {
  try {
    const payload = extractJsonFromMarkdown(markdownText);
    const history = Array.isArray(payload?.history_data) ? payload.history_data : [];
    const ids = new Set<string>();
    const counts: Record<string, number> = {};
    for (const r of history) {
      const id = r?.item_id ?? r?.id;
      if (id) {
        const sid = String(id);
        ids.add(sid);
        counts[sid] = (counts[sid] ?? 0) + 1;
      }
    }
    const known = Array.isArray(payload?.known_covariates_names) ? payload.known_covariates_names : [];
    const futureCov = Array.isArray(payload?.future_cov) ? payload.future_cov : [];
    const lens = Object.values(counts);
    const minSeriesLength = lens.length ? Math.min(...lens) : 0;
    const maxSeriesLength = lens.length ? Math.max(...lens) : 0;
    return {
      seriesCount: ids.size,
      historyRows: history.length,
      hasFutureCov: futureCov.length > 0,
      knownCovariatesCount: known.length,
      minSeriesLength,
      maxSeriesLength,
    };
  } catch {
    return null;
  }
}

type HistoryPoint = { timestamp: string; target: number };
type PredPoint = { timestamp: string; mean?: number | null } & Record<string, any>;

export type SeriesView = {
  itemIds: string[];
  byItemId: Record<
    string,
    {
      history: HistoryPoint[];
      predictions: PredPoint[];
      band?: { lowKey: string; highKey: string };
    }
  >;
};

export function buildSeriesView(args: {
  markdownText: string;
  predictions: any[];
  quantiles: number[];
  predictionLength: number;
  historyMultiplier?: number;
}): SeriesView {
  const payload = extractJsonFromMarkdown(args.markdownText);
  const historyRows: any[] = Array.isArray(payload?.history_data) ? payload.history_data : [];

  const historyByIdAll: Record<string, HistoryPoint[]> = {};
  for (const r of historyRows) {
    const itemId = String(r?.item_id ?? r?.id ?? "");
    if (!itemId) continue;
    const ts = String(r.timestamp);
    const y = Number(r.target);
    if (!Number.isFinite(y)) continue;
    historyByIdAll[itemId] ??= [];
    historyByIdAll[itemId].push({ timestamp: ts, target: y });
  }
  for (const id of Object.keys(historyByIdAll)) {
    historyByIdAll[id].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  }

  const historyById: Record<string, HistoryPoint[]> = {};
  const mult = args.historyMultiplier ?? 4;
  const windowSize = Math.max(1, Math.floor(args.predictionLength * mult));
  for (const id of Object.keys(historyByIdAll)) {
    const arr = historyByIdAll[id];
    historyById[id] = arr.length > windowSize ? arr.slice(arr.length - windowSize) : arr;
  }

  const predById: Record<string, PredPoint[]> = {};
  for (const r of args.predictions ?? []) {
    const itemId = String(r?.item_id ?? r?.id ?? "");
    if (!itemId) continue;
    predById[itemId] ??= [];
    predById[itemId].push(r as PredPoint);
  }
  for (const id of Object.keys(predById)) {
    predById[id].sort((a, b) => String(a.timestamp).localeCompare(String(b.timestamp)));
  }

  const itemIds = Array.from(new Set([...Object.keys(historyById), ...Object.keys(predById)])).sort();

  const byItemId: SeriesView["byItemId"] = {};
  for (const id of itemIds) {
    const preds = predById[id] ?? [];
    // Visualization requirement: prefer P10-P90 band if exists.
    let band: { lowKey: string; highKey: string } | undefined;
    if (preds.length > 0) {
      const first = preds[0] as any;
      if ("0.1" in first && "0.9" in first) {
        band = { lowKey: "0.1", highKey: "0.9" };
      } else {
        // fallback: use min/max available quantile columns
        const qCols = Object.keys(first)
          .filter((k) => /^0\.\d+$/.test(k))
          .map((k) => Number(k))
          .filter((n) => Number.isFinite(n))
          .sort((a, b) => a - b);
        if (qCols.length >= 2) {
          band = { lowKey: String(qCols[0]), highKey: String(qCols[qCols.length - 1]) };
        }
      }
    }
    byItemId[id] = {
      history: historyById[id] ?? [],
      predictions: preds,
      band,
    };
  }

  return { itemIds, byItemId };
}

export function downloadAsJson(obj: any, filename: string) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadAsCsv(rows: any[], filename: string) {
  if (!rows || rows.length === 0) {
    downloadAsJson([], filename.replace(/\.csv$/i, ".json"));
    return;
  }
  const keys = Array.from(
    rows.reduce((s, r) => {
      Object.keys(r || {}).forEach((k) => s.add(k));
      return s;
    }, new Set<string>()),
  );
  const escape = (v: any) => {
    const s = v === null || v === undefined ? "" : String(v);
    if (/[",\n]/.test(s)) return `"${s.replaceAll('"', '""')}"`;
    return s;
  };
  const lines = [
    keys.join(","),
    ...rows.map((r) => keys.map((k) => escape((r as any)[k])).join(",")),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
