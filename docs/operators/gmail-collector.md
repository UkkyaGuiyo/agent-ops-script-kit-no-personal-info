# 第10号 Gmail収集係：公開版技術仕様

**Status: VERIFIED（対象コードcbfa915930096a535bb229188f54a830d9b208ba、Linux/root・合成入力限定）。** 新規clone全539/539件PASS（SKIPなし、第4号validate_item互換性含む）とC-7説明合格が別環境検証担当AIから報告された。非root・他OS・実Gmailと実際の重要メール判定精度は未検証。正式RELEASEDではない。Python 3.10+、標準ライブラリ、GPL-3.0-only。

## 仕事

複数の**合成アカウント**から、ページングされたID一覧を取得し、個別合成メールを機械的に分類する。条件の一致により生成した**候補**を、第4号Shared Intake v1の投入形式でローカル状態に保存する。実メール・実アカウント・実案件判断に使用するための完成品ではない。

**実装の境界：** `MailProvider`は`list_page(account_id,token)`と`get_message(account_id,message_id)`の**読取専用インターフェース**。同梱実装は`FixtureProvider`のみ。Gmail/Google API、メール送信、アカウント操作、ネットワークアクセス、添付DL、HTTP URLを開く処理、スケジューラ、第4号`ingest`は存在しない。

## 入力

| 種類 | 例 | 検査 |
| --- | --- | --- |
| `--policy` | `config/examples/gmail-collector-policy.example.json` | JSON版1、`policy_version/source_id`、分類順序、辞書、規則ID重複・未知キー、数値型と上限、SHA-256 |
| `--accounts` | `config/examples/gmail-collector-accounts.example.json` | JSON版1、アカウント件数・`account_id,role,address`、役割集合・住所重複・キー型、SHA-256 |
| `--fixture` | `examples/gmail/snapshot-synthetic.json` | JSON版1、`accounts`、各アカウントの`pages`と`messages`を機械検証。本人の実メールや実設定を使わない |
| `--state-dir` | 利用者が事前作成する非公開の一時ディレクトリ | 公開チェックアウト外、シンボリックリンク不可。状態ファイル・ロックはこのディレクトリのみ |

形式は**独自の合成JSON契約**であって、Gmail APIのJSONのままでも、メールMIME形式でもない。アカウント例のメールアドレスは架空の`.invalid`ドメイン。実Gmailアドレスを公開しない。

- ページ契約：`{"token":null,"next":"next-token-or-null","message_ids":["synthetic-id"]}`。`next=null`で終わる正規一覧のみ完全取得。空の正規一覧は`message_ids=[]`。応答欠落/不正やページ/メッセージ上限は**未完了**。
- 個別メール契約：`id,thread_id,received_at,from,to,subject,body_text,body_html,attachments`。日時は**UTCオフセット付きISO-8601**。添付配列は形だけ検査し、ファイルは開かない。本文・件名・HTMLは文字列としてのみ処理し、`script/style`の内容は分類材料から除外。命令として評価しない。
- 条件/アカウントJSONは各操作で再読込。既存状態のポリシー版・SHA・アカウント設定SHAと一致しない場合、再初期化せず**ERROR**。JSONの重複キー/NaN、未知条件ID、重複ルールID、誤ったrole、型違いは開始前に拒否する。
- サイズ制限：条件64 KiB、アカウント64 KiB、合成スナップショット4 MiB、ローカル状態8 MiB。ページ/メッセージ数は条件側の設定値で制限。未読ページが残る場合はpartial、正常扱いしない。

## 分類順序（確定）

1. **対象外**：`exclude.terms`に一致した時点で除外。候補に入れない。
2. **宛先ルール**：アカウントの`role`に対応する`routes`でローカル分類先を決める。実メール転送は行わない。
3. **募集系**：`recruitment.terms`があれば主カテゴリ`recruitment`。
4. **重要の独立判定**：`importance`で強い不利益の兆候、弱い兆候＋不利益/文脈グループ、行動喚起＋不利益/本人関連を判定。主カテゴリを`important`にする前に判定するが、募集系でも`important_flag`は別に保持。
5. **プラットフォーム通知**：他の主カテゴリにならない場合に`platform.terms`を検査。重要ならプラットフォーム名があっても`important`を優先。

どれにも当たらなければ`other`（投入案なし）。重要の具体的な語彙は**完全に架空の合成例**であって、一般的な重要メール検出アルゴリズムの品質は未確認。弱い語＋宣伝の購入期限だけなら重要判定をしない。添付の内容は分類材料にしない。

## 永続化と重複

- 既知キー：`sha256([account_id,message_id])`。スレッドIDだけ、送信者や件名だけでは重複判定しない。**異なるアカウントの同じメールIDは別物**。
- 候補の`source_event_id`：`sha256([source_id,account_id,message_id])`に基づく決定的ID。同じ候補を再検査しても再作成・再時刻更新しない。
- ローカル`gmail-collector-state.json`にseen（正常に検査済みID）、outbox（未配送候補）、`last_success_at`、試行情報、条件/アカウントSHAを**一つの原子的な保存操作**で確定。内容は私的情報になり得るため、GitHubには絶対に入れない。
- 対象外と条件非該当も正常なメールとしてseenに残す。破損した個別メール・ID不足・取得不能はseenへ入れず再試行。部分成功時は成功分だけを記録し、最終**完全**成功時刻を変更しない。
- ハッシュはファイルの整合性を検知するためであり、外部の攻撃者に対する真正性証明ではない。状態ファイルが壊れた場合に自動でリセットしない。途中保存の一時ファイルが残ったら明示的に停止する。

## 第4号互換のローカル候補

`pending`は`{event_id,item}`の配列を出す。`item`は第4号公開v1の`validate_item`が受け入れるキー群：`schema_version=1`、初回`when_fetched`、`where.source_id`、`source_event_id`、`who,what,why,how`、および`payload`。payloadには、**ハッシュ化したメッセージ参照**、`account_role`、`route`、`category`、`important_flag`、`condition_id`、`routing_condition_id`、`policy_version`、`policy_sha256`、`account_config_sha256`、`external_delivery=NONE`だけを含める。本文、件名、送信者アドレス、添付内容を候補に複写しない。

**第4号形式と互換であることと、受け皿に投入済みであることは違う。** 本ツールは第4号のCLIを実行しない。pendingは送信済みでも本人が読んだ証明でもない。`ack`も同梱しない。

## コマンド

- `check --fixture FILE`：合成データを調べ、成功分の候補とseenを同時保存。出力`status=ok|partial|error`、`new_event_count`、`accounts_complete/partial/failed`、`pending_proposal_count`、`invalid_messages`、条件版/ハッシュ。`gmail_connection=NONE`、`shared_intake_write=false`、`external_delivery=NONE`。
- `pending`：状態に保存された投入案だけを表示する。書込みなし。これを公のIssue・PRやログへ転載しない。
- **非対応**：`send`、`ingest`、`apply`、`ack`、メール既読変更、ラベル操作、削除、`cron`/スケジューラ。

| 終了コード | status | 意味 |
| --- | --- | --- |
| 0 | ok | 全アカウントの設定範囲で、全件一覧・個別取得が正しく完了。0件でも正しい |
| 2 | partial | 一部アカウント失敗、欠落個別ID、ページング上限到達。成功分のみseen/outboxへ登録 |
| 1 | error | 条件/アカウント/状態の破損、全アカウント取得不能等。`new_event_count=null`（0件ではない） |
| 3 | error | ロック競合。処理なし |

`argparse`構文不正によるexit2は業務`partial`とは別。アカウントの入力JSONが正しいかどうかはGmail APIの取得権限と同義ではない。取得済みフィクスチャの完全性も**自己申告**に過ぎない。

## 制限・未解決

- 実Gmailの権限失効、レート制限、MIME、APIページネーション、スレッド変更、永続カーソルや既読状態との連携は対象外。
- 内部の重要メール取りこぼし1件の根因・修正効果は未検証。公開版での分類は語句一致の**候補化**であり、重要度・案件適合度の保証ではない。
- 非root、Windows/macOS、NFS、実メール大量データ、日次・15分定時運転は未検証。
- P3独立clone・C-7説明試験は対象コード限定で報告上PASS。[独立検証概要](../verification/gmail-collector-independent-2026-11-17.md)。P4セキュリティ/履歴/ライセンス監査、P5本人の正式リリース承認は別工程。

[P1裁定](../plans/gmail-collector-p1.md)／[HowTo](../howto/gmail-collector.md)／[説明](../explain/gmail-collector.md)／[制作側テスト](../verification/gmail-collector-local-2026-11-17.md)
