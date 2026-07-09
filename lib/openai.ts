import OpenAI from "openai";
import type { AnalysisResult, AnalysisSections, FilingReference } from "@/types/analysis";

const defaultSections: AnalysisSections = {
  businessSummary: "資料から確認できません",
  revenueSources: "資料から確認できません",
  businessModel: "資料から確認できません",
  performanceOverview: "資料から確認できません",
  segmentCharacteristics: "資料から確認できません",
  profitability: "資料から確認できません",
  financialHealth: "資料から確認できません",
  cashFlow: "資料から確認できません",
  interestBearingDebt: "資料から確認できません",
  shareholderReturns: "資料から確認できません",
  importantRisks: "資料から確認できません",
  strengths: [],
  weaknesses: [],
  investmentCautions: [],
  nextIrMaterials: [],
};

function client() {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY が設定されていません。.env.local を確認してください。");
  return new OpenAI({ apiKey });
}

function toResult(reference: FilingReference, sections: Partial<AnalysisSections>): AnalysisResult {
  return {
    ...defaultSections,
    ...sections,
    companyName: reference.companyName,
    secCode: reference.secCode,
    edinetCode: reference.edinetCode,
    documentName: reference.docDescription,
    submittedAt: reference.submitDateTime,
    officialReference: reference,
  };
}

export async function analyzeReport(reference: FilingReference, reportText: string): Promise<AnalysisResult> {
  const response = await client().responses.create({
    model: "gpt-4.1-mini",
    input: [
      {
        role: "system",
        content:
          "あなたは公開IR資料を整理する日本語アナリストです。投資助言、買い・売り・推奨の断定は禁止です。資料から確認できない数字は推測せず『資料から確認できません』と書いてください。必ずJSONのみを返してください。",
      },
      {
        role: "user",
        content: JSON.stringify({
          instruction: "有価証券報告書の抽出テキストを個人投資家向けの学習・投資管理用に整理してください。",
          requiredKeys: Object.keys(defaultSections),
          filing: reference,
          reportText,
        }),
      },
    ],
    text: {
      format: {
        type: "json_schema",
        name: "edinet_analysis",
        strict: true,
        schema: {
          type: "object",
          additionalProperties: false,
          properties: Object.fromEntries(
            Object.entries(defaultSections).map(([key, value]) => [
              key,
              Array.isArray(value) ? { type: "array", items: { type: "string" } } : { type: "string" },
            ]),
          ),
          required: Object.keys(defaultSections),
        },
      },
    },
  });

  const parsed = JSON.parse(response.output_text) as AnalysisSections;
  return toResult(reference, parsed);
}
