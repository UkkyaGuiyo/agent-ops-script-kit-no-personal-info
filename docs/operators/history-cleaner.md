# 履歴掃除係：第4号共通受け皿の記録を調べる、提案専用オペレーター

**Status: VERIFIED for commit 61c3364af28a5f367205f4d8c41d587e9ce9e97f within reported Linux/root read-only scope.** 新規clone全370/370件PASS（第4号実CLI統合試験を含む、SKIPなし）とC-7説明再現PASSがV.E.S.T.A.R.D.から報告された。非root・他OS・NFS・大量記録はUNVERIFIED。削除・seen独立保存は未実装、正式RELEASEDではない。GPL-3.0-only、Python 3.10+、標準ライブラリのみ。

## 役割と非目的

対象は第4号の`events/YYYY-MM-DD.jsonl`（v1）に追記される**アイテム本体、状態イベント、稼働記録**。ローカルファイル自体、Git履歴やバックアップの掃除ではない。受け皿の正本を**読むだけ**で、期限判定による候補表示を行う。ファイル削除、行の削除、書換え、seq採番し直し、prepare/complete、受け皿への追加、自動スケジュール、ネットワーク転送は存在しない。

CLI：

```text
python scripts/history_cleaner.py --data-dir PRIVATE_INTAKE_DIR \
  --source-roles PRIVATE_SOURCE_ROLES_JSON [--days 90] [--as-of ISO_UTC]
```

- `--data-dir`：既存の第4号ローカル受け皿。**公開チェックアウト外**、実パスを公開しない。中身に`events/`および**既存の**`.intake.lock`が必要。第4号の既存ロックを読み取り区間中保持するが**新しいロックファイルは作成しない**。未初期化・中断した受け皿はhold/error。
- `--source-roles`：既存のJSONファイル、例`{"version":1,"source_roles":{"synthetic-source":"general","synthetic-reminder":"reminder"}}`。source名は安全なASCII記号1〜128文字。`general`/`reminder`のみ。未記入の由来はUNKNOWNとして保留。これは利用者の**宣言**であり、外部証拠による真正性保証はしない。実IDを公開Gitへ保存しない。
- `--days`：整数0〜36500、既定90 **日**。判定は最終`reported`/`discarded`遷移からUTC経過が指定日数**以上（境界を含む）**。登録・取得日時を起点にしない。
- `--as-of`：時刻オフセット付きISO-8601。**合成試験用**。通常は省略して現在のUTCを使う。
- 第4号v1の`item_added`は初期`unprocessed`のみ。登録時から終端となる内部専用ケースは**この公開版に存在しない**。

## 出力（stdout JSON）

- `status`: `preview`（完全な候補表示）、`hold`（保留あり・実施不可）、`error`（正本/入力が不正）。
- `as_of_utc`: ISO-8601 UTC。`retention_days`: 日、`record_count`: **イベント行数**、`run_count`: **取得実行件数**。`counts`: アイテム件数の`candidate`/`not_due`/`excluded`/`hold`。
- `item_previews[]`: `item_id`、`state`、`decision`、`reason`、`source_role_declared`、`origin_verified_independently`（false）、`age_seconds`（秒またはnull）、`event_ids_protected`、`event_delete_allowed=false`、`seen_retention_independent=false`、`deletion_safe=false`。
- `run_previews[]`: source_id/run_id、run状態、decision/reason、event_ids_protected、deletion_safe=false。失敗イベントの保護件数は`protected_error_event_count`で報告。
- 常に`dry_run=true`、`records_changed=0`、`safe_to_delete_count=0`、`journal_compaction_authorized=false`。`seen_memory_independent=false`、`prune_prepare_complete_verified=false`も明示。
- `hold`/`error`で完全な分類ができない時、`counts=null`、`item_previews=null`として**正常0件に見せない**。
- `item_id`/source ID/実行IDは実名や個人情報を含む可能性あり。stdout/実際のpolicy/ログを公開しない。

## 判定基準

| 状態／情報 | decision | reason |
| --- | --- | --- |
| 未処理/監査済み | `excluded` | `NONTERMINAL_NEVER_PRUNE` |
| 終端、期限未到来 | `not_due` | `TERMINAL_BELOW_RETENTION` |
| 終端、期限到来、宣言済み由来 | `candidate` | `TERMINAL_AT_OR_BEYOND_RETENTION` |
| 終端、期限到来、由来不明 | `hold` | `UNKNOWN_ITEM_ORIGIN` |
| 終端時刻が未来 | `hold` | `FUTURE_TERMINAL_TIMESTAMP` |
| 取得run稼働中 | `excluded` | `RUN_NOT_COMPLETED` |
| 取得run完了、エラー行なし | `hold` | `RUN_RETENTION_RULE_UNCONFIRMED` |
| 取得runにエラー行あり | `hold` | `ERROR_AUDIT_PROTECTED` |
| 未完のintake一時ファイル、prune証跡 | `hold` | `INTERRUPTED_INTAKE_SAVE` / `UNSUPPORTED_PRUNE_EVIDENCE` |
| 正本の不正JSON、seq欠番、未知イベント等 | `error` | `INVALID_JSON` / `BAD_SEQ` / `UNSUPPORTED_EVENT_KIND` 等 |

**注意:** `candidate`は寿命条件だけの確認。今の第4号の追記専用ログは`source_event_id`を再生して重複排除に用いるため、`item_added`等を直接削除してはいけない。**reminder由来の状態イベントも保護し、通常由来のイベントも公開版では一切消さない**。内部の`prepare/complete`意味検証・チェックポイント再計算は公開v1に存在せず、孤立参照を「過去の正常削除」と認定しない。

## 終了コードと制限

- **0:** 候補表示が完了し、holdが無い。候補件数があっても何も削除しない。
- **2:** holdが存在し、削除適用を判断できない。未初期化の既存ロック、完了runの保持規則不明、未知由来、未完prune記録等。
- **1:** 土台の不正、読めない正本、不正policy、連番・状態遷移不整合。**0件と解釈しない**。
- 引数不正は`argparse`のexit2。これは「検査してholdがあった」時の2と異なる。

本ツールは正本と同じ既存`.intake.lock`を共有し、主な取り込み操作と衝突しないようにする。しかしロック非協調の外部プロセスや、読み取り後の変更は防げない。クロスファイルで原子的なスナップショットは保証しない。第4号公開Kit v1との合成CLI互換は独立検証報告でPASS（対象コミット限定）。Windows・非root・NFS・大量データはUNVERIFIED。削除・圧縮・チェックポイントの更新・Git履歴書換えは**未実装**。

[P1裁定](../plans/history-cleaner-p1.md)／[HowTo](../howto/history-cleaner.md)／[説明](../explain/history-cleaner.md)／[制作側テスト](../verification/history-cleaner-local-2026-11-17.md)

[独立検証概要](../verification/history-cleaner-independent-2026-11-17.md)。
