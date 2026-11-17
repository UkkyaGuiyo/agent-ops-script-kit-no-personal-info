# 第6号 整理係：P1確定裁定（EVP/1 20261117-023）

**Status:** P1 ACCEPT_WITH_CONDITIONS / public independent PILOT. Independent fresh-clone verification pending.  
**Basis:** V.E.S.T.A.R.D. の一般化した内部仕様報告。内部コード、実ファイル、正確なパス、運用ログは取得・複製していない。

## 名称と根拠の訂正

[FACT: VESTARD-REPORTED] 内部の「整理係」はフォルダへの自動分類ではなく、**作成時に宣言された所属タグとファイル更新時刻に基づく寿命管理**である。タグは `disposable` と `permanent` の2種。条件は「`disposable`」かつ「mtimeから14日以上」。ファイル内容や外部正本を読んで判定しない。未登録を後から推測して分類しない。

[FACT: VESTARD-REPORTED] 内部版は既定でドライランだが、独立した操作でルート内ゴミ箱へ移動し、別のpurgeで後日に物理削除する。今回の公開版がこれらを実装したという意味ではない。

## U1〜U3裁定

| Decision | Public PILOT | Explicit exception |
| --- | --- | --- |
| **U1 公開初版権限** | **(a) 提案のみ**。移動、リネーム、タグ書換え、削除、パージ、スケジューリングの実装なし | 内部版の段階制(b)とは意図的に異なる。将来の書込み系は別設計・試験・本人の承認が必要 |
| **U2 保存期間** | `age_days` を設定ファイルで指定。初版サンプルは14日、mtime起点、`>=` で候補 | 内部の「1か月後purge」は参考情報。公開初版ではパージ期間の設定・判定・実行は**NONE** |
| **U3 受け皿担当の保持掃除** | **含めない**。受け皿の90日保持管理は独立した将来の監査対象 | 14日・1か月・90日を一つのルールに混ぜない |

## 独立公開実装の判断

- 既存の第3号 `untagged_watch` と共通の一般化JSON形式：ルート直下の `.retention_records.json` の `entries` に、root-relative `path` と `class`。任意の `version=1`。これは公開向けの契約であり、内部実装完全互換の保証ではない。
- 設定は明示的な複数ルート、固有別名、`age_days`、`exclude_subtrees`。ルートの重複・シンボリックリンクは拒否。既定の非対象ディレクトリ `.git`、`.trash`、`node_modules` 等を除外する。
- **登録されているパスしか検査しない**。未登録の通常ファイルは絶対に勝手に分類しない。内容の読込みは所属記録JSONだけ。登録済みファイルは`lstat`でmtime・種別を確認する。
- `candidate`、`not_due`、`excluded`、`hold` に分類。`hold` は未知タグ、欠落ファイル、危険な相対パス、将来mtime、シンボリックリンク、非通常ファイル、読取失敗などを理由付きで表示。`hold` が存在すれば `status=partial` / exit 1。設定・記録全体の破損や重複は `error` / exit 1（正常結果として0件を出さない）。
- 通常は `ok`、候補があれば `candidates`。どちらもexit 0。すべての出力は `dry_run=true`、`changed_files=0`、`trash_move_available=false`、`purge_available=false`。出力に相対パスが含まれ得るため**実結果を公開しない**。
- mtimeの条件判定はUTC時刻とnanosecond整数で実施し、境界の丸め誤差を避ける。14日とは14×24時間。ファイルのmtimeが変われば次回判定も変わる。
- `age_days` の値は候補提示用であって削除権限を与えない。候補表示は「目的を達成した」意味を独自に証明しない。必要なファイルは製作者が正しくpermanentと登録する責任がある。
- public code does not maintain a mutable snapshot, pending queue, delivery state or duplicate detection events. **state = NONE, delivery = NONE**. No integration with Shared Intake.

## 残る制約

- 公開PILOTはルート内で対象が移動・改名されたことや、読み取り中の競合を監視しない。走査は原子的スナップショットではない。レポートから実操作を実行してはならない。
- 非root権限拒否のライブ挙動、Windows、ネットワークファイルシステム、非常に多数のタグ登録、実運用での正確性は独立検証されていない。
- 内部版の `apply`・`purge`・ゴミ箱移動ログ・日付命名・復元機能・タグ管理CLI・受け皿保持掃除は、この公開初版には一切含めない。できると説明してはならない。

## 独立検証ゲート

合成タグ/mtime、14日のちょうどの境界、永久タグ、未登録、未知タグの保留、記録欠落、相対パス逸脱、シンボリックリンク、複数ルート、オプション不正、原本のSHA-256・mtime不変、READMEからの初心者再現（C-7）。本番操作は一切しない。正式リリースはP4監査とP5本人承認を別途要する。
