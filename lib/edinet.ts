import type { FilingReference } from "@/types/analysis";

const EDINET_BASE_URL = "https://api.edinet-fsa.go.jp/api/v2";
const SEARCH_DAYS = 400;

type EdinetDocument = {
  seqNumber?: number;
  docID: string;
  edinetCode?: string;
  secCode?: string;
  JCN?: string;
  filerName?: string;
  fundCode?: string | null;
  ordinanceCode?: string;
  formCode?: string;
  docTypeCode?: string;
  periodStart?: string;
  periodEnd?: string;
  submitDateTime?: string;
  docDescription?: string;
  issuerEdinetCode?: string | null;
  subjectEdinetCode?: string | null;
  subsidiaryEdinetCode?: string | null;
  currentReportReason?: string | null;
  parentDocID?: string | null;
  opeDateTime?: string | null;
  withdrawalStatus?: string;
  docInfoEditStatus?: string;
  disclosureStatus?: string;
  xbrlFlag?: string;
  pdfFlag?: string;
  attachDocFlag?: string;
  englishDocFlag?: string;
};

type DocumentsResponse = {
  metadata?: { status?: string; message?: string };
  results?: EdinetDocument[];
};

export function normalizeSecCode(input: string) {
  return input.replace(/[^0-9]/g, "").slice(0, 5);
}

function getApiKey() {
  const key = process.env.EDINET_API_KEY;
  if (!key) throw new Error("EDINET_API_KEY が設定されていません。.env.local を確認してください。");
  return key;
}

function formatDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function edinetParams(params: Record<string, string>) {
  return new URLSearchParams({ ...params, "Subscription-Key": getApiKey() });
}

export function documentDownloadUrl(docId: string, type: "1" | "2" | "5" = "5") {
  return `${EDINET_BASE_URL}/documents/${docId}?${edinetParams({ type }).toString()}`;
}

export function officialDocumentPageUrl(docId: string) {
  return `https://disclosure2.edinet-fsa.go.jp/WEEK0010.aspx?docID=${encodeURIComponent(docId)}`;
}

function isAnnualSecuritiesReport(doc: EdinetDocument) {
  const description = doc.docDescription ?? "";
  const normalAnnual = description.includes("有価証券報告書") && !description.includes("訂正");
  return doc.docTypeCode === "120" || normalAnnual;
}

function isCorrection(doc: EdinetDocument) {
  return (doc.docDescription ?? "").includes("訂正") || doc.docTypeCode === "130";
}

function matchesSecCode(doc: EdinetDocument, secCode: string) {
  const normalizedDocCode = (doc.secCode ?? "").replace(/[^0-9]/g, "");
  return normalizedDocCode === secCode || normalizedDocCode === `${secCode}0`;
}

async function fetchDocumentsByDate(date: string) {
  const url = `${EDINET_BASE_URL}/documents.json?${edinetParams({ date, type: "2" }).toString()}`;
  const response = await fetch(url, { next: { revalidate: 60 * 60 } });
  if (!response.ok) throw new Error(`EDINET書類一覧APIの取得に失敗しました（${date}: ${response.status}）。`);
  const json = (await response.json()) as DocumentsResponse;
  return json.results ?? [];
}

export async function findLatestAnnualReport(secCodeInput: string): Promise<FilingReference> {
  const secCode = normalizeSecCode(secCodeInput);
  if (!/^\d{4}$/.test(secCode)) throw new Error("証券コードは4桁の数字で入力してください。");

  const today = new Date();
  const candidates: EdinetDocument[] = [];

  for (let offset = 0; offset < SEARCH_DAYS; offset += 1) {
    const date = new Date(today);
    date.setUTCDate(today.getUTCDate() - offset);
    const docs = await fetchDocumentsByDate(formatDate(date));
    candidates.push(...docs.filter((doc) => matchesSecCode(doc, secCode) && isAnnualSecuritiesReport(doc)));
    if (candidates.some((doc) => !isCorrection(doc))) break;
  }

  const sorted = candidates.sort((a, b) => {
    const correctionPriority = Number(isCorrection(a)) - Number(isCorrection(b));
    if (correctionPriority !== 0) return correctionPriority;
    return (b.submitDateTime ?? "").localeCompare(a.submitDateTime ?? "");
  });
  const doc = sorted[0];
  if (!doc) throw new Error(`直近${SEARCH_DAYS}日以内に証券コード ${secCode} の有価証券報告書が見つかりませんでした。`);

  return {
    docId: doc.docID,
    edinetCode: doc.edinetCode ?? "不明",
    secCode,
    companyName: doc.filerName ?? "不明",
    docDescription: doc.docDescription ?? "有価証券報告書",
    submitDateTime: doc.submitDateTime ?? "不明",
    periodStart: doc.periodStart,
    periodEnd: doc.periodEnd,
    ordinanceCode: doc.ordinanceCode,
    formCode: doc.formCode,
    docTypeCode: doc.docTypeCode,
    sourceUrl: officialDocumentPageUrl(doc.docID),
    extractionMethod: "metadata",
  };
}

export async function downloadDocument(docId: string, type: "1" | "2" | "5") {
  const response = await fetch(documentDownloadUrl(docId, type));
  if (!response.ok) throw new Error(`EDINET書類取得APIの取得に失敗しました（type=${type}: ${response.status}）。`);
  return Buffer.from(await response.arrayBuffer());
}
