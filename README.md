# KABU DAILY — GitHub Pages版（第1段階）

PCを起動していなくても、iPhone・iPad・PCから見られる日本株適時開示ダッシュボードです。表示はGitHub Pages、データ更新とGemini APIによる対象開示のAI要約はGitHub Actionsで行います。APIキーはGitHub ActionsのSecretのみに保存します。

## 構成

- `docs/`：GitHub Pagesで公開するHTML・CSS・JavaScript・PWAファイル
- `docs/data/disclosures.json`：最大180日間の適時開示（同じPDFは重複保存しません）
- `docs/data/status.json`：直近の取得成否と取得件数
- `scripts/fetch_tdnet.py`：TDnet公開ページを低頻度で確認してJSONを作るPython処理
- `.github/workflows/schedule-disclosures.yml`：平日9:07、12:07、15:37、17:37（日本時間）の自動更新入口
- `.github/workflows/update-disclosures.yml`：定期更新から呼び出される処理本体と手動更新入口
- `tests/`：分類・解析・重複防止・失敗時保護の自動テスト

## 画面でできること

- 新着順／重要度順の並び替え、分類・重要度による絞り込み、証券コード・会社名・タイトル検索
- 証券コードを端末内だけにお気に入り保存し、お気に入りだけを表示
- 今日・未読・★4以上・優待・配当・決算／業績修正・TOB／M&Aのかんたん絞り込み
- PDFを開いた情報の既読保存、すべて既読、既読リセット
- 発表時刻の新旧、重要度、会社名、証券コードによる並び替え
- ダーク／ライトテーマ、iPhone・iPad・PC対応、ホーム画面追加、直近データのオフライン表示
- 取得失敗時も前回の正常なJSONを表示し、画面上には警告を表示
- 重要度★4以上、または決算・業績予想修正・増減配・優待新設／廃止・自社株買いの開示に、AI要約・株価への影響・重要ポイント・注意点を表示
- 右上の「↻ 更新」から更新を開始し、GitHub Actionsの正常終了後に自動再読み込み

> 最初の2件は、レイアウトを確認するための明示的なサンプルです。画面にも「サンプル」と警告が出ます。GitHub Actionsが初めて成功すると削除され、TDnetの実データだけになります。

## GitHub Pagesを公開する手順

操作は1つずつ進めてください。

1. GitHubでこのリポジトリのページを開き、上部の **Settings** を押します。
2. 左側の **Pages** を押します。
3. **Build and deployment** の **Source** が表示されたら、**GitHub Actions** を選びます。
4. リポジトリ上部の **Actions** を押します。
5. 左側の **GitHub Pages公開** を押します。
6. **Run workflow** → 緑色の **Run workflow** を押します。
7. 1～3分待って **Settings** → **Pages** をもう一度開きます。
8. `Your site is live at ...` のURLが表示されたら、リンクを押します。

公開する中身はワークフロー内で`docs`フォルダだけに限定しています。データ更新ワークフローも、JSONを保存した後に同じ`docs`フォルダを自動公開します。

公開URLは通常 `https://GitHubユーザー名.github.io/リポジトリ名/` です。リポジトリが非公開の場合にPagesを公開できるかどうかは、GitHubの契約設定により異なります。

## GitHub Actionsを手動実行する手順

事前にリポジトリの **Settings** → **Secrets and variables** → **Actions** で、Gemini APIキーをRepository secret `GEMINI_API_KEY`として登録してください。Secretが未設定でもTDnetの通常更新は継続します。要約は安定版の`gemini-2.5-flash-lite`を使い、1回の更新につき最大8件まで作成します。既存の要約は再利用されます。

1. リポジトリ上部の **Actions** を押します。
2. 左側の **適時開示データ更新** を押します。
3. 右側の **Run workflow** を押します。
4. Branchを確認して、緑色の **Run workflow** を押します。
5. 数秒後に表示される実行行を押します。緑色のチェックなら完了です。

### Run workflowが表示されない場合

上部の **Settings** → 左側の **Actions** → **General** → 下部の **Workflow permissions** で **Read and write permissions** を選び、**Save**を押します。組織やブランチの保護設定により、Actionsから直接pushできない場合があります。

取得に失敗しても `disclosures.json` は書き換えません。失敗状態だけを `status.json` に保存するため、公開画面には前回の正常データと警告が表示されます。

## 画面の更新ボタンを有効にする（Cloudflare Workers無料枠）

GitHubトークンは公開される`docs`には置かず、Cloudflare WorkerのSecretだけに保存します。`worker/`の中継APIは更新開始後のGitHub Actions実行IDを返し、画面はその実行が`success`になるまで確認してから再読み込みします。

### 現在どこまでできているか

| 状態 | 作業 |
|---|---|
| **実装・設定済み** | 更新ボタン、更新中表示、成功までの監視、失敗表示、Workerのソース、`workflow_dispatch`との実行照合、デプロイ済みWorker URLのGitHub Pagesへの設定、テスト |
| **デプロイ済みWorker** | `https://proud-wildflower-1a64.tomoya03212738.workers.dev/` |
| **残りの作業** | この変更をdefault branchへ反映し、GitHub Pagesの公開後に更新ボタンで最終確認 |

> **現在の状態:** Workerはデプロイ済みで、そのURLも`docs/index.html`へ設定済みです。以下の手順2～6はWorkerを再構築するときのために残しています。今回は手順1で変更を反映した後、手順8の最終確認へ進めます。

### 1. 先にこの変更をGitHubのdefault branchへ反映する

この変更を含むPull Requestをマージし、GitHub上のdefault branch（通常は`main`）に `.github/workflows/schedule-disclosures.yml` の`request_id`入力が存在する状態にします。先にWorkerを動かすと、GitHubが未定義の入力を拒否します。

### 2. Cloudflareアカウントを用意する

1. [Cloudflare Dashboard](https://dash.cloudflare.com/)を開き、無料アカウントを作成またはログインします。
2. メール認証が求められたら完了させます。
3. 独自ドメインやクレジットカードは不要です。今回は無料の`workers.dev` URLを使います。

### 3. GitHub Fine-grained Personal Access Tokenを作る

1. GitHub右上のプロフィール画像 → **Settings** を開きます。
2. **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token** を開きます。
3. Token nameを`kabu-daily-cloudflare-worker`などにし、有効期限を選びます（期限後は再発行が必要です）。
4. **Repository access** は **Only select repositories** を選び、このリポジトリだけを指定します。
5. **Repository permissions** の **Actions** を **Read and write** にします。それ以外は既定のままにします。
6. **Generate token** を押し、表示されたトークンを一時的に安全な場所へコピーします。GitHubを離れると再表示できません。

### 4. Wrangler設定のプレースホルダーを置き換える

`worker/wrangler.toml`を開き、次の4項目を実環境に合わせます。

```toml
GITHUB_OWNER = "GitHubのユーザー名またはOrganization名"
GITHUB_REPO = "edinet-ai-analyzer"
GITHUB_REF = "main"
ALLOWED_ORIGIN = "https://GitHubユーザー名.github.io"
```

- Pages URLが`https://octocat.github.io/edinet-ai-analyzer/`なら、`ALLOWED_ORIGIN`はリポジトリ部分と末尾スラッシュを除いた`https://octocat.github.io`です。
- default branchが`main`以外なら`GITHUB_REF`をそのブランチ名に変えます。
- 変更した`wrangler.toml`はGitHubへ保存して構いません。ここには秘密情報を入れません。

### 5. WranglerへログインしてSecretを登録する

Node.js 20以上が入ったPCのターミナルで、リポジトリのルートから順番に実行します。

```bash
cd worker
npm install
npx wrangler login
npm run secret
```

1. `npx wrangler login`でブラウザが開いたら、手順2のCloudflareアカウントを選んで許可します。
2. `npm run secret`が値を求めたら、手順3でコピーしたGitHub PATを貼り付けてEnterを押します。入力文字が画面に出なくても正常です。
3. Secret名はコード側で固定済みの`GITHUB_TOKEN`です。`docs`、`wrangler.toml`、GitHubの通常ファイルにはトークンを書かないでください。

通常の手動デプロイでは、別途Cloudflare APIトークンやAccount IDを作る必要はありません。`wrangler login`のブラウザ認証を使います。CIから自動デプロイしたい場合だけ、Cloudflare APIトークンの設定が別途必要です。

### 6. Workerをデプロイして疎通確認する

```bash
npm run deploy
```

初回に`workers.dev`サブドメインの登録を求められたら、画面の案内に沿って任意の名前を決めます。完了時に表示される`https://kabu-daily-update-api....workers.dev`形式のURLをコピーします。次に、`ALLOWED_ORIGIN`と同じ値をOriginヘッダーへ指定して確認します。

```bash
curl -H "Origin: https://GitHubユーザー名.github.io" \
  https://発行されたWorker URL/health
```

`"ok":true`、正しい`repository`、`"workflow":"schedule-disclosures.yml"`が返ればWorker側は準備完了です。`403`ならOrigin、`ok:false`ならSecretまたはWrangler設定を確認します。

### 7. Worker URLをダッシュボードへ設定する

`docs/index.html`先頭付近のメタタグには、デプロイ済みWorker URLを設定済みです。

```html
<meta name="update-api-url" content="https://proud-wildflower-1a64.tomoya03212738.workers.dev/">
```

今後Worker URLを変更した場合だけ、この値も変更してください。今回の変更をGitHubへpushして`main`へ反映し、GitHub Pagesのデプロイが完了するまでActions画面で待ちます。

### 8. ブラウザから最終確認する

1. GitHub Pagesを開き、必要なら一度強制再読み込みします。
2. 右上の **↻ 更新** を押します。
3. ボタンが **更新中…** とスピナー表示になることを確認します。
4. GitHubの **Actions** を別タブで開き、**適時開示データ定期更新**に「開示データ更新（UUID）」という実行が増えることを確認します。
5. Actionsが緑のチェックで終了すると、元の画面が自動再読み込みされ、最終更新日時とデータが更新されます。赤い×なら画面にも失敗メッセージが出ます。

Workerは`ALLOWED_ORIGIN`以外のブラウザからのリクエストを拒否します。GitHub上でPATを失効させれば、いつでも中継APIからの起動を停止できます。既存の平日4回のschedule設定には変更を加えず、ボタンは同じ「適時開示データ定期更新」の`workflow_dispatch`だけを起動します。

## 公開URLを確認する

リポジトリ上部の **Settings** → 左側の **Pages** の順に押します。ページ上部の **Visit site** または `Your site is live at ...` のリンクが公開URLです。

## iPhone・iPadのホーム画面へ追加

1. Safariで公開URLを開きます（ChromeではなくSafariを使います）。
2. 画面下部の共有ボタン `□↑` を押します。iPadでは上部にあります。
3. メニューを上へ動かし、**ホーム画面に追加**を押します。
4. 右上の **追加** を押します。
5. ホーム画面の `KABU DAILY` アイコンを押すと起動します。

## セキュリティと公開範囲

GitHub Pagesは公開サイトです。保有株数、取得単価、資産額、氏名、パスワードは保存も表示もしません。「保存銘柄」は各端末の`localStorage`（ブラウザ内の保存場所）だけに入り、GitHubや外部APIへ送信されません。外部通信はブラウザから静的ファイルと公式PDFを開く通信、ActionsからTDnet公開一覧を確認する通信だけです。

## 現在の制限

- TDnetの当日一覧の先頭ページを取得します。非常に開示が多い日の2ページ目以降は未対応です。
- GitHub Actionsの定期実行は混雑時に数分以上遅れる場合があります。
- 定期実行の履歴は **Actor が `github-actions` になるとは限りません**。schedule の Actor は通常、cron を最後に変更したユーザーです。Actions の履歴では Actor ではなく、実行名 **「定期実行（schedule）」**、または実行詳細の event が `schedule` であることを確認してください。
- schedule は default branch にあるworkflowだけが対象です。Actionsでworkflowが無効、リポジトリがfork、またはpublicリポジトリで60日間活動がない場合は、GitHub上で定期実行を再度有効化する必要があります。手動実行が成功しても、それだけではscheduleイベントが発生した証明にはなりません。
- GitHub APIが公開するworkflowの`state`や実行履歴には、内部スケジューラへのcron登録状態を示す項目がありません。このリポジトリでは定期実行入口を独立したworkflowとして作り直し、GitHub側に新しいworkflow IDでscheduleを再登録させています。
- 分類はタイトル中のキーワードによる自動判定で、誤分類の可能性があります。
- Safariは状況により古いオフラインキャッシュを表示することがあります。その場合はSafariでページを開いて再読み込みしてください。
- 株価、市場情報、ニュース、通知は今回の第1段階には含めていません。

## 開発者向けテスト

```bash
python -m unittest discover -s tests -v
python -m http.server 8000 --directory docs
```

ブラウザで <http://localhost:8000> を開きます。
