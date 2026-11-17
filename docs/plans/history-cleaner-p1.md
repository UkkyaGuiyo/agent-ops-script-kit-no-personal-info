# 第8号：履歴掃除係 P1裁定（EVP/1 20261117-034）

**Status:** `ACCEPT_WITH_CONDITIONS` → 公開版独立実装 `PILOT`。独立の新規clone/C-7説明再現は未実施。  
**Source:** V.E.S.T.A.R.D.の一般化した内部実装・運用報告。実データ、実コード、実パス、内部ログは転用していない。  
**Repository basis:** 第4号の公開版 `scripts/shared_intake.py` のJSONL v1、`docs/operators/shared-intake.md`。

## 対象の確定

「履歴」は、**第4号・共通受け皿**のアイテム、状態遷移イベント、取得実行履歴（runs）。ファイルそのもの・Git履歴・バックアップを掃除しない。内部版は既定でドライラン、明示的な`--apply`のときに個々の記録を間引く設計で、準備記録・完了記録・読み戻し検算を持つと報告された。ただし内部での**実データ削除の運用実績はUNVERIFIED**（初期保存期限の到来前）。

### 内部版の要件（公開版で実現済みという意味ではない）

- `reported` / `discarded`のみ。`unprocessed` / `audited`は削除不可。
- 終端到達時刻から90日。最初から終端として投入された特殊項目は取得時刻起点。ただし公開版の第4号は**初期状態`unprocessed`のみ**許容するため、この例外を公開PILOTは実装しない。
- リマインダー由来は本体と状態イベントを分けて保護し、エラー行、`seen`、`prune_log`を削除しない。
- `prepare`→`complete`を検査し、未完prepareで保留。適用後にチェックポイント再計算・読み戻し・別経路の整合性検証。連番seqの相対順序を保って再採番。内部でも定期実行は未開始。

## U1/U2/U3裁定

| 論点 | 公開初版 | 搭載しないこと |
| --- | --- | --- |
| U1 操作範囲 | **(a) ドライランのみ**。期限条件に達したアイテム本体の候補を表示 | `--apply`、正本書換え、記録削除、seq再採番、チェックポイント更新、`prepare/complete`、スケジュール |
| U2 形式 | **第4号公開JSONL v1に厳密に連動**。`events/YYYY-MM-DD.jsonl`、event kind・seq・item_idなどを検証 | 無関係な抽象履歴JSONを別規格として採用しない |
| U3 期限 | `--days`指定、既定90日。終端遷移時刻からの経過`>= days×86400秒` | run履歴への90日流用、エラー行の削除、一律14日/1か月流用 |

## 公開版の必須の区別

[FACT: PUBLIC CODE] 第4号の`replay`は、`item_added`イベント内の`source_event_id`を重複排除の記憶として再構成している。`prune_prepare/complete`イベントも、独立した`seen`記録も、現在の公開v1に存在しない。既存イベントの削除や詰め直しを行えば、再生と重複排除を壊す可能性がある。

そのため公開版の`candidate`は**期限条件を満たすという意味のみ**。削除対象の物理的な行を確定したわけではない。出力では常に`safe_to_delete_count=0`、`journal_compaction_authorized=false`。`seq`、event ID、内容、ファイルのSHA-256・mtimeは一切変えない。

第4号の公開投入スキーマには由来の正規フィールドがない。そのため公開パイロットは`source_roles`（source_id→`general`または`reminder`）を**利用者が宣言する任意の根拠**として読み取る。これを真正性確認済みの証拠とはしない（`origin_verified_independently=false`）。未登録sourceで期限が到来した項目は**hold**。明示したreminder由来アイテム本体を候補表示しても、その状態イベントは保護する。全アイテムイベントは`seen`移行未整備のため削除不可。

- `unprocessed` / `audited`：必ず`excluded`。
- 期限前の終端：`not_due`。
- 期限到来の終端＋宣言済み由来：`candidate`（安全な削除ではない）。
- 期限到来の終端＋由来不明、未来時刻：`hold`。
- 継続中run：`excluded`。完了済みrun：保持規則未確定のため`hold`。エラー行を伴うrun：`hold`、エラー監査として保護。
- `prune_log`等の存在、保存途中の`.intake-temp-*`：**hold（exit 2）**。不正なJSONL、未完行、seq欠番、孤立遷移、未知イベント：**error（exit 1）**。既知の`complete`証拠と見なす経路は存在しない。
- 並行処理対策：第4号と同じ既存`.intake.lock`にロックを取得する。ただし**新しく作成しない**。無い場合はhold。正本と補助資料の書換えは0件。

## 残る不明・別審査

- 公開v1で`seen`を分離して保存する正本仕様、prepare/completeの意味検証、削除後の正本再生、二系統の到達照合、状態イベントを保護したうえでの行の間引き方式は**未設計**。
- 取得実行runの個別保持期限は**UNKNOWN**。90日を自動で当てはめない。
- 削除自体の内部運用実績、他OS・非root・NFS・大規模イベント件数・外部システムの参照正当性は**UNVERIFIED**。
- 真の記録削除、手順書と既存実装の変更、既存cron、通知、外部送信は**OUT_OF_SCOPE**。正式リリースにはP4監査・P5本人承認が別途必要。

[技術仕様](../operators/history-cleaner.md)／[HowTo](../howto/history-cleaner.md)／[初心者説明](../explain/history-cleaner.md)
