# KABU DAILY — GitHub Pages版（第1段階）

PCを起動していなくても、iPhone・iPad・PCから見られる日本株適時開示ダッシュボードです。表示はGitHub Pages、データ更新はGitHub Actionsで行います。OpenAI API、有料API、APIキー、ローカルサーバー、SQLiteは使用しません。

## 構成

- `docs/`：GitHub Pagesで公開するHTML・CSS・JavaScript・PWAファイル
- `docs/data/disclosures.json`：最大180日間の適時開示（同じPDFは重複保存しません）
- `docs/data/status.json`：直近の取得成否と取得件数
- `scripts/fetch_tdnet.py`：TDnet公開ページを低頻度で確認してJSONを作るPython処理
- `.github/workflows/update-disclosures.yml`：平日9:00、12:00、15:30、17:30（日本時間）の自動更新と手動更新
- `tests/`：分類・解析・重複防止・失敗時保護の自動テスト

## 画面でできること

- 新着順／重要度順の並び替え、分類・重要度による絞り込み、証券コード・会社名・タイトル検索
- 証券コードを端末内だけにお気に入り保存し、お気に入りだけを表示
- 今日・未読・★4以上・優待・配当・決算／業績修正・TOB／M&Aのかんたん絞り込み
- PDFを開いた情報の既読保存、すべて既読、既読リセット
- 発表時刻の新旧、重要度、会社名、証券コードによる並び替え
- ダーク／ライトテーマ、iPhone・iPad・PC対応、ホーム画面追加、直近データのオフライン表示
- 取得失敗時も前回の正常なJSONを表示し、画面上には警告を表示

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

1. リポジトリ上部の **Actions** を押します。
2. 左側の **適時開示データ更新** を押します。
3. 右側の **Run workflow** を押します。
4. Branchを確認して、緑色の **Run workflow** を押します。
5. 数秒後に表示される実行行を押します。緑色のチェックなら完了です。

### Run workflowが表示されない場合

上部の **Settings** → 左側の **Actions** → **General** → 下部の **Workflow permissions** で **Read and write permissions** を選び、**Save**を押します。組織やブランチの保護設定により、Actionsから直接pushできない場合があります。

取得に失敗しても `disclosures.json` は書き換えません。失敗状態だけを `status.json` に保存するため、公開画面には前回の正常データと警告が表示されます。

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
- 分類はタイトル中のキーワードによる自動判定で、誤分類の可能性があります。
- Safariは状況により古いオフラインキャッシュを表示することがあります。その場合はSafariでページを開いて再読み込みしてください。
- 株価、市場情報、ニュース、通知は今回の第1段階には含めていません。

## 開発者向けテスト

```bash
python -m unittest discover -s tests -v
python -m http.server 8000 --directory docs
```

ブラウザで <http://localhost:8000> を開きます。
