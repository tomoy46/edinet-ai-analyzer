"use client";

import { FormEvent, useState } from "react";
import AnalysisResult from "@/components/AnalysisResult";
import type { AnalysisResult as AnalysisResultType, AnalyzeApiResponse } from "@/types/analysis";

const disclaimer = "本サービスは公開IR資料をもとに情報を整理するものであり、特定銘柄の売買を推奨するものではありません。分析結果には誤りが含まれる可能性があります。投資判断は必ず公式IR資料を確認したうえで、ご自身の判断で行ってください。";

export default function Home() {
  const [secCode, setSecCode] = useState("");
  const [result, setResult] = useState<AnalysisResultType | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ secCode }),
      });
      const data = (await response.json()) as AnalyzeApiResponse;
      if (!data.ok) throw new Error(data.error);
      setResult(data.result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "分析に失敗しました。時間を置いて再度お試しください。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">EDINET × OpenAI</p>
        <h1 className="title">有価証券報告書AI分析ツール</h1>
        <p className="lead">
          日本株の証券コードを入力すると、EDINET APIから直近の有価証券報告書を取得し、公開資料の内容を個人投資家向けに整理します。
        </p>

        <form onSubmit={handleSubmit} className="form">
          <input
            value={secCode}
            onChange={(event) => setSecCode(event.target.value)}
            inputMode="numeric"
            pattern="[0-9]{4}"
            maxLength={4}
            placeholder="例：7203"
            className="input"
            aria-label="証券コード"
            required
          />
          <button
            type="submit"
            disabled={loading}
            className="button"
          >
            {loading ? "分析中..." : "分析開始"}
          </button>
        </form>

        <p className="disclaimer">{disclaimer}</p>
      </section>

      {error && <div className="alert">{error}</div>}
      {loading && <div className="loading">EDINETから書類を検索し、AI分析を実行しています。数十秒かかる場合があります。</div>}
      {result && <AnalysisResult result={result} />}
    </main>
  );
}
