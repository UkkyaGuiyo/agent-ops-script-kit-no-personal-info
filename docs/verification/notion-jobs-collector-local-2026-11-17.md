# 第9号 Notionジョブ収集係：制作側ローカル検証

**Date:** 2026-11-17 JST。**Status: PILOT**。すべて架空のページ・ドメイン・識別子を使用。実Notion接続、アカウント操作、第4号への実投入なし。  
**Environment:** Linux container、root、Python 3.13.5、標準ライブラリ。非root、Windows/macOS、NFS、実Notion、規模試験はUNVERIFIED。

## 実測結果

- `python -m unittest discover -s tests -v`：**71件発見、70件PASS、1件SKIP、失敗0件**。SKIPは第4号の実ソース`shared_intake.py`を使った`validate_item`互換性テスト。単独制作フォルダには第4号が存在しないため、公開キットの新規cloneで必ず実行・判定する。
- `python -m py_compile scripts/notion_jobs_collector.py`：PASS。
- 既存公開キットは第8号まで**370/370件PASSの独立報告**。新規71件追加で、全体**441件の期待値**。現時点では**441/441はUNVERIFIED**。

## 合成CLIアンカー

`config/examples/notion-jobs-policy.example.yaml` と2つの合成スナップショットにより実施（保存状態は毎回新規の私的な一時フォルダ）。

| 段階 | 実測 | 解釈 |
| --- | --- | --- |
| bootstrap初回 | exit0、baseline_pages=1、baseline_urls=1、new_events=0 | 既存分を新着とは通知しない |
| updated snapshotの初回check | exit0、new_event_count=3、pending_proposal_count=3 | 新しい日付1件＋新しい正規化URL2件 |
| 同じupdated snapshotの再check | exit0、new_event_count=0、pending_proposal_count=3 | 再実行は新規通知を重複させない |
| pending | exit0、count=3 | 全件ローカル投入案、受け皿への実投入ではない |
| 全段階 | `notion_connection=NONE`（check）、`shared_intake_write=false`、`external_delivery=NONE` | 実サービスに触らない |

サンプルのページ本文の指示らしい文字列は命令として解釈されず、投入案の本文としてもコピーされなかった。本文に含まれるURL文字列だけを比較対象とした。元のYAMLと2つのJSONはSHA-256不変。ローカル状態JSONはチェックアウト外にのみ生成。

## 危険側・異常系の合成確認

- YAML条件の必須欠落・未知ID・二重キー・未知キー・版違いは拒否。状態に記録された条件ファイルSHAとの相違は`POLICY_MISMATCH`で停止し、既存状態は不変。
- 3形式（親ID・URL・タイトル）の不一致、親`complete=false`、親本文非文字列は全体停止。子のID・URL・タイトル不一致、本文非文字列、欠落、`complete=false`、不正日付はpartial。失敗した子はseenに入らない。
- `bootstrap`完了後の再bootstrapは拒否。途中失敗時には開始状態・試行履歴を残し、成功入力で再試行できる。通常checkはbootstrap完了前に拒否。
- 構文不正JSON、重複JSONキー、NaN、状態ハッシュ不一致、シンボリックリンク、孤児の一時保存ファイル、公開チェックアウト内の状態ディレクトリは拒否。
- 正規化ではクエリ/フラグメントを除外し、同一ページ内の同じURLを重複させない。URL・ページの消失や、URLを伴わない本文変更は新着扱いしない。
- `PageProvider`はインターフェースだけで、同梱`FixtureProvider`以外に実装なし。外部HTTP、通知、Notionページ書込、応募・共有受け皿への投入コードはない。

## 独立検証の要件

1. 新規cloneを対象コードコミットに固定し、`python -m unittest discover -s tests -v`で**期待441件**を実測。第4号互換性テストがSKIPなしでPASSすること。
2. 合成bootstrap、初回check、再check、pendingの上表アンカーを再現。入力SHA-256不変、出力に実アカウント情報が無いこと。
3. 親/子失敗、bootstrap再実行拒否、ポリシー変更Fail Closed、ページ指示文の非実行、出力が実配送でないことを確認。
4. C-7説明：**「Notionは本来入力元だが公開版は合成読み取りのみ」「収集は判断・応募・台帳登録ではない」「失敗は0件ではない」「第4号にはまだ実投入していない」「bootstrapは一回限り」**を正確に再現できること。
5. 実Notionへの接続、第4号への実配送、本番運用・スケジューラ・ページ書込は今回検証しない。独立試験後もP4/P5は別工程。

[仕様](../operators/notion-jobs-collector.md) / [P1裁定](../plans/notion-jobs-collector-p1.md)
