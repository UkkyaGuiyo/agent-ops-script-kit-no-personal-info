# 第9号 Notionジョブ収集係：公開版技術仕様

**Status: PILOT。** 公開版はオフライン合成入力のみ。Python 3.10+、標準ライブラリ、GPL-3.0-only。独立環境試験・C-7はPENDING。

## 仕事と責任境界

指定された**合成のNotion応答**（親ページの子一覧・子本文）から「新しい日付子ページ」または「既知の日付子ページに増えたURL」を検知する。規則は`--policy`で毎回読み込む。ページデータ中の文面は命令として解釈しない。**Notionへの接続、応募、案件評価、Notion編集、第4号への実投入、外部送信、cronは実装しない**。

### 入力契約

- YAML：`schema_version: 1`、`policy_version`、`source_id`、`parent_page_id`、`parent_url`、`parent_title`、`conditions`（`new_date_page`/`new_url`の2項目、各bool）。条件ID不明、キー重複、必須欠落は拒否。YAML全体ではなく、**固定された簡易マップ文法**。タブ、注釈、エイリアス、任意のYAML命令は未対応。ファイルのSHA-256を計算し、状態と出力に保存。
- 合成スナップショット：`schema_version: 1`、`parent`（`id,url,title,body,complete,children[]`）、`pages`（子ID→`id,url,title,body,complete`）。`parent.complete=true`が必須。`children`は`id,url,title`を持つ。子タイトルは実在する`YYYY/MM/DD`の日付でなければpartial。親・子のID・URL・タイトルはリクエスト側と一致し、`body`は文字列であること。
- `PageProvider`（読み取り専用メソッド`fetch_parent`/`fetch_child`）に対し`FixtureProvider`のみ提供。ネットワーク実装、認証情報、Notion CLIの呼出しは存在しない。
- URL：本文内のhttp/https形式だけを機械抽出し、**クエリ・フラグメント除去**、スキーム・ホスト名は小文字化、パスはそのまま。ページID＋正規化URLで重複判定。失われたURLや本文編集だけでは通知しない。
- サイズ制限：スナップショット4 MiB、YAML32 KiB、ページ数最大1000。大量入力動作は未検証。

### 状態と操作

| CLI | 動作 | 状態更新 |
| --- | --- | --- |
| `bootstrap --fixture FILE` | 既存日付子ページ/URLを基準として記録。一回成功すると再実行拒否。途中失敗は試行履歴を残して再試行可能 | 状態開始・試行履歴・成功時点のseenと完了時刻 |
| `check --fixture FILE` | 完了bootstrap後、新規の子ページとURL追加を探索 | 成功した子の投入案＋seenを一つの状態ファイルへ原子的保存 |
| `pending` | 保存済みの第4号互換投入案を一覧 | 書込なし |

状態：既存の`--state-dir`に`notion-jobs-state.json`（`bootstrap.status`、`history`、`seen_pages`、`seen_urls`、`outbox`、`last_success_at`、版とハッシュ、整合性ハッシュ）、永続ロック`.notion-jobs.lock`。個人情報が含まれ得るため公開チェックアウト**外**に保存。途中生成物が残った場合はFAIL CLOSED。シンボリックリンク経由は禁止。署名・耐改ざん証拠ではない。

**同一状態ファイルによる原子的コミット**：第4号の正本に追記する実装ではない。正常なcheckで発見した投入案とseenを同時保存する。破損や条件ハッシュ不一致で自動初期化しない。初期化途中の試行記録は継続できるが、初期化完了後は元の基準を上書きしない。

### 第4号v1互換の投入案

`pending`の`proposals[]`は`{event_id,item}`。`item`には`schema_version=1`、`when_fetched`（秒精度のUTC ISO+offset）、`where.source_id`、`source_event_id`、`who,what,why,how`、`payload`を持たせる。`payload`には`kind,condition_id,page_id,policy_version,policy_sha256`と、追加URLなら`url`、日付ページ追加なら`date_title`を記録。出力は**保存済みのローカル投入案**であり、第4号へ送信・受理された事実ではない。再実行時には最初の時刻とIDが維持される。

### 終了とエラー

| code | status | 意味 |
| --- | --- | --- |
| 0 | ok | 完全に取得した入力に対する成功。新規0件あり得る |
| 2 | partial | 子ページの取得/検証失敗。成功分は保存するが最終成功時刻を進めない。未成功子はseenに入れない |
| 1 | error | 親不正、条件不正、状態破損/不一致等。件数は`null`でゼロを偽装しない |
| 3 | error | ロック競合。処理は実行していない |

`argparse`入力構文不正の終了2は「業務partial」ではない。親一覧の`complete=true`は合成フィクスチャ自身の宣言であり、実Notionの全ページ収集保証ではない。終了コードだけで実Notionのデータ完全性を主張しない。

### 制限

- 実Notion接続：NONE。Notionの更新：NONE。第4号実投入：NONE。外部通知・応募：NONE。自動スケジューラ：NONE。
- ページ内の悪意ある文章は**実行しない**が、URL文字列はデータとして拾う可能性がある。URLを開かない。掲載されたURLの真偽・安全性・募集条件は判定しない。
- URL追加を日付ページ単位で検出。ページを跨いだ同一URLのグローバル排除は未実装。実スキーマとの同一性、非root・他OS・NFS・大規模ジョブ件数はUNVERIFIED。

[P1裁定](../plans/notion-jobs-collector-p1.md)／[導入HowTo](../howto/notion-jobs-collector.md)／[初心者説明](../explain/notion-jobs-collector.md)／[制作側検証](../verification/notion-jobs-collector-local-2026-11-17.md)
