export const JSON_FENCE_RE = /```json\s*([\s\S]*?)\s*```/i;

export const sampleMarkdown = `# Chronos Forecast Input

\`\`\`json
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
  ],
}
\`\`\`
`;

export async function readFileText(file: File): Promise<string> {
  return await file.text();
}

export async function precheckMarkdownHasJsonFence(
  file: File,
  bytes = 8192,
): Promise<{ ok: boolean; message: string }> {
  const blob = file.slice(0, bytes);
  const text = await blob.text();
  const ok = text.includes("```json") || JSON_FENCE_RE.test(text);
  return ok
    ? { ok: true, message: "已检测到 ```json 代码块（预检通过）" }
    : { ok: false, message: "未检测到 ```json 代码块：请按模版填写后上传" };
}

export function extractJsonFromMarkdown(markdownText: string): any {
  const m = markdownText.match(JSON_FENCE_RE);
  const raw = (m?.[1] ?? markdownText).trim();
  return JSON.parse(raw);
}
