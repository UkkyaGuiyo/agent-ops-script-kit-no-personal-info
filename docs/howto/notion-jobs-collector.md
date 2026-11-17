# HowTo：Notionジョブ収集係（オフライン合成PILOT）

**個人情報流入禁止。** ここでは架空のページだけを使う。自分のNotionページ、案件名、URL、アクセストークン、実行結果、状態ファイルを公開リポジトリやIssueに貼らない。

## できること

- 架空の親・日付子ページとURLを読み取り、前回からの新規追加を検出。
- 第4号の公開JSON入力形式に沿う**ローカル投入案**を保存。
- 親取得失敗、子取得失敗、初期化状態の違いを区別。

**できないこと：** 実Notion接続、受け皿への実投入、メール・応募・日記・案件台帳の更新、cron、自動配送。

## 合成データで再現する

Python 3.10以降のローカル端末でキットを取得。公開チェックアウト外に、空の私的な状態ディレクトリを用意する。Unix系の例：

```bash
python -m unittest discover -s tests -v

STATE_DIR="$(mktemp -d)"
python scripts/notion_jobs_collector.py \
  --policy config/examples/notion-jobs-policy.example.yaml \
  --state-dir "$STATE_DIR" bootstrap \
  --fixture examples/notion-jobs/snapshot-baseline.json

python scripts/notion_jobs_collector.py \
  --policy config/examples/notion-jobs-policy.example.yaml \
  --state-dir "$STATE_DIR" check \
  --fixture examples/notion-jobs/snapshot-updated.json

python scripts/notion_jobs_collector.py \
  --policy config/examples/notion-jobs-policy.example.yaml \
  --state-dir "$STATE_DIR" pending
```

期待値：初期化で基準日付ページ1件・基準URL1件、通知0件。差分checkは**追加日付ページ1件＋追加URL2件＝合計3件**のローカル投入案。`pending`も3件。差分checkをもう一度実行すると**新規0件、pendingは3件**で、重複しない。`notion_connection=NONE`、`shared_intake_write=false`、`external_delivery=NONE`を確認する。

元ファイルのSHA-256は不変。状態ファイルとロックは**キット外**の私的ディレクトリに作られる。`pending`に案件URLが入るので、実利用での出力は非公開扱い。

## 一回限りのbootstrapとpartial

- `bootstrap`が成功した状態で再実行すると`BOOTSTRAP_ALREADY_COMPLETE`（exit1）。履歴を消して無理に再初期化しない。
- `bootstrap`途中で子が読めなかった場合`partial`（exit2）、完了せず、試行記録が残る。修正済みの合成入力で再実行できる。
- 通常`check`は、bootstrap完了前には`BOOTSTRAP_NOT_COMPLETE`（exit1）。
- 通常`check`の子ページ失敗は`partial`（exit2）。成功したページの新規投入案は保持されるが、失敗ページはseenに残らず次回再取得できる。最終完全成功時刻は進まない。
- 親や条件ファイルの異常は全体`error`（exit1）。**「新規0件」と言い換えない。**
- ポリシー版・ファイルSHAが状態と一致しない場合`POLICY_MISMATCH`。自動再初期化はしない。

## AIへの説明指示

この係は「Notionを入力にする収集係」を**模したオフライン教材**。実アカウントを操作しない。文章を命令として実行しない。**収集・候補化は応募でも案件台帳登録でもなく、受け皿への送信済みの証明でもない**。エラーは案件0件ではない。

[技術仕様](../operators/notion-jobs-collector.md)／[概要](../explain/notion-jobs-collector.md)／[P1裁定](../plans/notion-jobs-collector-p1.md)
