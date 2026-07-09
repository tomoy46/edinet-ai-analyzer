import type { AnalysisResult as AnalysisResultType } from "@/types/analysis";

const fields: Array<[keyof AnalysisResultType, string]> = [
  ["businessSummary", "事業内容の要約"],
  ["performanceOverview", "業績の概要"],
  ["profitability", "収益性"],
  ["financialHealth", "財務健全性"],
  ["cashFlow", "キャッシュフロー"],
  ["shareholderReturns", "配当・株主還元"],
  ["importantRisks", "重要なリスク"],
];

function ListSection({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="card">
      <h3 className="section-title">{title}</h3>
      {items.length > 0 ? (
        <ul className="list">
          {items.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="section-body">資料から確認できません</p>
      )}
    </section>
  );
}

export default function AnalysisResult({ result }: { result: AnalysisResultType }) {
  return (
    <div className="result-stack">
      <section className="result-card">
        <h2 className="company-name">{result.companyName}</h2>
        <dl className="meta-grid">
          <div><dt>証券コード</dt><dd>{result.secCode}</dd></div>
          <div><dt>EDINETコード</dt><dd>{result.edinetCode}</dd></div>
          <div><dt>対象書類名</dt><dd>{result.documentName}</dd></div>
          <div><dt>提出日</dt><dd>{result.submittedAt}</dd></div>
        </dl>
      </section>

      <div className="result-stack">
        {fields.map(([key, label]) => (
          <section key={key} className="card">
            <h3 className="section-title">{label}</h3>
            <p className="section-body">{String(result[key])}</p>
          </section>
        ))}
        <ListSection title="良い点" items={result.strengths} />
        <ListSection title="悪い点" items={result.weaknesses} />
        <ListSection title="投資判断上の注意点" items={result.investmentCautions} />
        <ListSection title="次に確認すべきIR資料" items={result.nextIrMaterials} />
      </div>

      <section className="card reference">
        <h3 className="section-title">公式資料への参照情報</h3>
        <p>docID: {result.officialReference.docId}</p>
        <p>抽出方法: {result.officialReference.extractionMethod}</p>
        <a className="reference-link" href={result.officialReference.sourceUrl} target="_blank" rel="noreferrer">
          EDINET公式ページを開く
        </a>
      </section>
    </div>
  );
}
