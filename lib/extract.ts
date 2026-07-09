import AdmZip from "adm-zip";
import { downloadDocument } from "./edinet";
import type { FilingReference } from "@/types/analysis";

const MAX_ANALYSIS_CHARS = 70_000;
const IMPORTANT_KEYWORDS = [
  "事業の内容",
  "経営成績",
  "財政状態",
  "キャッシュ・フロー",
  "配当",
  "株主還元",
  "リスク",
  "セグメント",
  "売上高",
  "営業利益",
  "経常利益",
  "親会社株主",
  "有利子負債",
];

function decodeCsv(buffer: Buffer) {
  if (buffer[0] === 0xff && buffer[1] === 0xfe) return buffer.toString("utf16le");
  return buffer.toString("utf8");
}

function compactText(value: string) {
  return value
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;|&#160;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();
}

function pickUsefulLines(text: string) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => compactText(line))
    .filter((line) => line.length > 8);

  const useful = lines.filter((line) => IMPORTANT_KEYWORDS.some((keyword) => line.includes(keyword)));
  const selected = useful.length > 50 ? useful : lines.slice(0, 1200);
  return selected.join("\n").slice(0, MAX_ANALYSIS_CHARS);
}

function extractCsvText(zipBuffer: Buffer) {
  const zip = new AdmZip(zipBuffer);
  const csvEntries = zip
    .getEntries()
    .filter((entry) => !entry.isDirectory && entry.entryName.toLowerCase().endsWith(".csv"));

  const chunks = csvEntries.map((entry) => decodeCsv(entry.getData()));
  return pickUsefulLines(chunks.join("\n"));
}

function extractXmlText(zipBuffer: Buffer) {
  const zip = new AdmZip(zipBuffer);
  const entries = zip
    .getEntries()
    .filter((entry) => !entry.isDirectory && /\.(xbrl|xml|htm|html)$/i.test(entry.entryName));

  const chunks = entries.map((entry) => compactText(entry.getData().toString("utf8")));
  return pickUsefulLines(chunks.join("\n"));
}

export async function extractReportText(reference: FilingReference) {
  const attempts: Array<{ type: "5" | "1" | "2"; method: FilingReference["extractionMethod"] }> = [
    { type: "5", method: "csv" },
    { type: "1", method: "xbrl" },
    { type: "2", method: "pdf" },
  ];
  const errors: string[] = [];

  for (const attempt of attempts) {
    try {
      const buffer = await downloadDocument(reference.docId, attempt.type);
      const text = attempt.method === "csv" ? extractCsvText(buffer) : extractXmlText(buffer);
      if (text.length > 500) return { text, extractionMethod: attempt.method };
      errors.push(`${attempt.method}: 抽出テキストが短すぎます`);
    } catch (error) {
      errors.push(`${attempt.method}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  const fallback = [
    reference.companyName,
    reference.docDescription,
    reference.submitDateTime,
    reference.periodStart && reference.periodEnd ? `${reference.periodStart}〜${reference.periodEnd}` : "",
  ]
    .filter(Boolean)
    .join("\n");

  if (!fallback) throw new Error(`書類本文を抽出できませんでした。${errors.join(" / ")}`);
  return { text: fallback, extractionMethod: "metadata" as const };
}
