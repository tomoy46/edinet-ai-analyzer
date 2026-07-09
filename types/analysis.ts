export type AnalysisSections = {
  businessSummary: string;
  revenueSources: string;
  businessModel: string;
  performanceOverview: string;
  segmentCharacteristics: string;
  profitability: string;
  financialHealth: string;
  cashFlow: string;
  interestBearingDebt: string;
  shareholderReturns: string;
  importantRisks: string;
  strengths: string[];
  weaknesses: string[];
  investmentCautions: string[];
  nextIrMaterials: string[];
};

export type FilingReference = {
  docId: string;
  edinetCode: string;
  secCode: string;
  companyName: string;
  docDescription: string;
  submitDateTime: string;
  periodStart?: string;
  periodEnd?: string;
  ordinanceCode?: string;
  formCode?: string;
  docTypeCode?: string;
  sourceUrl: string;
  extractionMethod: "csv" | "xbrl" | "pdf" | "metadata";
};

export type AnalysisResult = AnalysisSections & {
  companyName: string;
  secCode: string;
  edinetCode: string;
  documentName: string;
  submittedAt: string;
  officialReference: FilingReference;
};

export type AnalyzeApiResponse =
  | { ok: true; result: AnalysisResult }
  | { ok: false; error: string };
