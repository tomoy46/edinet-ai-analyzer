# 有価証券報告書AI分析ツール

日本株の証券コードを入力すると、EDINET API から直近の有価証券報告書を検索・取得し、OpenAI API で個人投資家向けに要約・分析する Next.js アプリです。

本アプリは投資助言ではなく、公開 IR 資料を整理するための学習・投資管理ツールです。分析結果には誤りが含まれる可能性があるため、投資判断は必ず公式 IR 資料を確認したうえで、ご自身の判断で行ってください。

## 主な機能

- 証券コードから EDINET の書類一覧 API を直近約 400 日分検索
- `docTypeCode` と `docDescription` を使って有価証券報告書を判定
- 訂正有価証券報告書より通常の有価証券報告書を優先
- EDINET の書類取得 API から CSV 変換済みデータ、XBRL、PDF 相当データの順で取得を試行
- 抽出したテキストを OpenAI API で JSON 分析
- 会社名、証券コード、EDINET コード、提出日、事業内容、業績、財務、リスク、確認すべき IR 資料などを画面表示

## 技術構成

- Next.js App Router
- TypeScript
- 通常の CSS（`app/globals.css`）
- API Route によるサーバー側処理
- EDINET API
- OpenAI API
- Vercel デプロイ想定

## 必要な環境変数

`.env.local` をプロジェクトルートに作成し、以下を設定してください。

```bash
EDINET_API_KEY=your_edinet_api_key
OPENAI_API_KEY=your_openai_api_key
```

- `EDINET_API_KEY`: EDINET API の API キーです。
- `OPENAI_API_KEY`: OpenAI API の API キーです。

どちらのキーも API Route のサーバー側でのみ利用され、フロントエンドには露出しません。

## ローカル起動方法

```bash
npm install
npm run dev
```

ブラウザで `http://localhost:3000` を開いてください。

## Vercel へのデプロイ方法

1. このリポジトリを GitHub などに push します。
2. Vercel で対象リポジトリを Import します。
3. Project Settings の Environment Variables に以下を登録します。
   - `EDINET_API_KEY`
   - `OPENAI_API_KEY`
4. Framework Preset が Next.js になっていることを確認します。
5. Deploy を実行します。

## 検証メモ

この Codex コンテナでは npm registry へのアクセスが HTTP 403 になるため、`npm install` と `npm run build` は未検証です。Vercel または通常のローカル環境で依存関係をインストールし、ビルドを確認してください。

## 注意事項

- 本サービスは公開 IR 資料をもとに情報を整理するものであり、特定銘柄の売買を推奨するものではありません。
- OpenAI の分析結果には誤りが含まれる可能性があります。
- 重要な数値や記述は、必ず EDINET や企業 IR の公式資料で確認してください。
- EDINET API のレスポンス形式や利用条件が変更された場合、取得処理の調整が必要になる可能性があります。
- 書類取得・テキスト抽出では CSV 変換済みデータを優先し、難しい場合は XBRL/PDF 相当の取得にフォールバックする構成です。
