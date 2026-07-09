import { NextResponse } from "next/server";
import { findLatestAnnualReport } from "@/lib/edinet";
import { extractReportText } from "@/lib/extract";
import { analyzeReport } from "@/lib/openai";
import type { AnalyzeApiResponse } from "@/types/analysis";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as { secCode?: unknown };
    const secCode = typeof body.secCode === "string" ? body.secCode : "";

    const filing = await findLatestAnnualReport(secCode);
    const extracted = await extractReportText(filing);
    const reference = { ...filing, extractionMethod: extracted.extractionMethod };
    const result = await analyzeReport(reference, extracted.text);

    return NextResponse.json<AnalyzeApiResponse>({ ok: true, result });
  } catch (error) {
    const message = error instanceof Error ? error.message : "分析中に予期しないエラーが発生しました。";
    return NextResponse.json<AnalyzeApiResponse>({ ok: false, error: message }, { status: 400 });
  }
}
