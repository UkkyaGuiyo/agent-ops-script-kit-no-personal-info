# 共通受け皿（Shared Intake）：技術仕様

**Status: PILOT.** 個別の新規clone・独立環境試験、初期状態Museの説明再現試験は未完了。
**License: GPL-3.0-only.** Python 3.10以降。追加パッケージ不要。ローカル動作のみ。

## 目的

複数の拾い係が作ったアイテムを1か所に**追記専用の正本**として保存し、現在の未処理件数を単一の旗に反映し、外部の判断に基づく状態遷移をイベントとして記録する。内容をAIで判定しない。外部送信・Notion/Gmail接続・自動配送・自動スケジュールは行わない。

## 使用条件・配置

`--data-dir` は利用者が**事前に作成した**ローカルディレクトリ。公開キットのチェックアウト外。実データ、実パス、アイテム入力やJSON応答を公開リポジトリへ入れない。ディレクトリ経路やログ・派生ファイルのシンボリックリンクは拒否する。ロックは `.intake.lock` という固定名のローカルファイルで行う（POSIXは `flock`、Windowsは `msvcrt.locking`）。ロックファイルは削除しない。競合は終了コード3で今回を飛ばす。

正本：`events/YYYY-MM-DD.jsonl`（UTC日付）。1行＝1イベント、`schema_version=1`, `seq`（1から欠番なし）, `event_id`（重複禁止）, `occurred_at`（タイムゾーン付きISO-8601）, `kind`。イベントの種類は `item_added`, `item_transition`, `source_run_started`, `source_run_error`, `source_run_completed`。

派生物：`flag.json`（`raised`, `unprocessed_count`, `open_count`, `total_items`, `last_seq`）、`state.json`（状態件数、送信元の実行履歴、エラー種別など）。いずれもログを再生して再構築でき、**正本ではない**。中断した `.intake-temp-*` が残れば自動で無視せず要確認エラー。

## 投入アイテムJSON

```json
{
  "schema_version": 1,
  "when_fetched": "2026-11-17T00:00:00+00:00",
  "where": {"source_id": "synthetic-source"},
  "source_event_id": "synthetic-event-01",
  "who": "synthetic producer",
  "what": "synthetic example",
  "why": "demonstrate safe intake",
  "how": "manual local CLI",
  "payload": {"example": true}
}
```

必須：`when_fetched`（UTCまたはオフセット付き）、`where.source_id`（英数字・点・ハイフン・アンダースコア、1〜128文字）。**`item_id`も`source_event_id`も無い投入は拒否**。`item_id`が無い場合は、`source_id`と`source_event_id`からSHA-256で決定的に生成。`status`省略時は `unprocessed`、別の初期状態は拒否。追加フィールドはJSONとして保存されるので個人情報・秘密情報を混ぜない。

同じ `item_id` と同一内容の再投入は追記せず `added=false`。内容不一致、または同一 `source_id/source_event_id` で異なるIDは拒否。送信元は**再送時も取得時刻を含む原アイテムを変えない**。

`ingest`の返答は `{status:"accepted",item_id,added,current_state,flag}`。全アイテムをエコーしない。ログ追記→`fsync`→旗と要約の原子的な保存が成功して初めて終了コード0。派生物だけ失敗したらエラーとなるが、同一IDで再試行すればログを重複させず派生物を修復できる。

## 状態遷移

- `unprocessed → audited → reported`（終端）
- `unprocessed → discarded` または `audited → discarded`（終端）
- 終端からの変更不可。初期に `audited` や `reported` で投入不可。
- `transition` は現在状態を確認してから、`from_state`, `to_state`, `item_id`, `event_id` を正本へ追記。`event_id`の同内容再送は `changed=false`、内容が異なる再使用は拒否。
- 受け皿は「本当に監査されたか」を判定しない。`transition`の権限判断は外部側の責任。本人の指示や実際の権限はこのツールでは付与できない。

## 送信元の実行記録

- `run-start --source-id --run-id`：RUNNINGを記録。
- `run-error --source-id --run-id --error-id --error-code`：取得や解析の**失敗情報を別イベント**として記録。`error_code` は一般化した機械可読カテゴリだけにする。
- `run-finish --source-id --run-id --outcome success|partial|error`：COMPLETEDにして結果を記録。実際に取得できなかった場合、**新着0件とは記録しない**。
- 同じ実行IDを再投入しても追記せず、完了済みoutcomeの変更は拒否。受信したアイテムの存在を実行成功の証拠としては扱わない。

## 旗、状態、再構築

- `flag.json`の `raised = (unprocessed_count > 0)`。`open_count`は `unprocessed + audited`。
- `status` は毎回ログから正本状態を算出し、旗・要約の欠落・不一致を警告するだけ。取得失敗は異常であり、正常な0件として表示しない。
- `rebuild` はログから旗と要約を上書き再生成。**ログは削除・再生成しない**。
- JSONL行の切断、欠番、event_id再使用、不正遷移、未知イベント、スキーマ不一致、記録ファイルのリンクはFail Closed。ログが壊れた場合は自動で作り直さない。

## 保持・削除（候補の確認だけ）

`retention-preview --days 90` は**終端になった時刻**を起点に、90日以上経過した `reported` と `discarded` のitem_idを表示するだけ。`unprocessed`と`audited`は候補にすらならない。デフォルト90日は公開パイロットの説明用設定であり、自動削除の承認ではない。

削除は**未実装**。prepare→検証→completeによる削除根拠、orphanの除外判定、履歴掃除との接続は将来の独立監査事項。既知削除の証拠がない参照を「正常なorphan」と判定する実装もない。

## 付け忘れ検出係との接続（手動パイロット）

`untagged_watch` の `pending` JSONを、`scripts/untagged_to_intake.py` で受信アイテム形式へ変換できる。`source_event_id = pending.report.event_id`を保持し、送信元の再送が同一item_idになることを保証する。

1. 変換だけでは保存成功ではない。
2. `shared_intake.py ingest` が終了コード0と `status=accepted`を返すまで、送信元のpendingを維持する。
3. `added=false`でも**同内容のイベントが正本に既存で、旗・要約再計算が成功した**ときは、受領済みと判断できる。
4. **その後に限り**、送信元へ元の `event_id` でackする。アダプターはackを実行しない。

## 終了コード・制限

- 0：処理成功。`ingest`の追加・重複回答、`transition`、`run-*`、`status`、`rebuild`、候補表示。
- 1：不正入力、読取・書込失敗、正本の不整合、権限問題。**0件や成功とは解釈しない**。
- 3：ロック競合で今回を実行せず停止。

同一ローカルファイルシステム内での単一プロセス追記・ロックを想定。JSONLへの追記と旗の更新は2ファイル以上に及ぶため原子的な単一トランザクションではない。再送・再構築で対処する設計。大量イベント時の再生性能、Windows、NFS/ネットワークファイルシステムは独立検証未実施。SHA-256はファイル同一性・整合性確認に使い、外部に対する真正性や内容の正確性を証明しない。

[HowTo](../howto/shared-intake.md) / [初心者への説明](../explain/shared-intake.md) / [P1裁定](../plans/shared-intake-p1.md)
