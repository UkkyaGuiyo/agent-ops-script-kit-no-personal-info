# 第8号 履歴掃除係：制作側ローカル検証

**Date:** 2026-11-17 JST。**Status: PILOT**。実験は合成ファイルのみ、実受け皿・実データ・外部送信なし。  
**Environment:** Linux container / Python 3.13.5。root権限の環境、非root・Windows・macOS・NFSは**UNVERIFIED**。  
**Source:** EVP/1 `20261117-034`一般化P1報告、第4号公開JSONL v1仕様。

## 実行と判定

- `python -m unittest discover -s tests -v`：**67件発見、66件PASS、1件SKIP、失敗0件**。SKIPは既存第4号`shared_intake.py`を使う**実CLI統合テスト**。この制作側の単独一時フォルダには既存第4号が無いため実行されない。**公開リポジトリの新規cloneでこの1件が実行されることが必須**。
- `python -m py_compile scripts/history_cleaner.py`：PASS。
- 既存公開キットは第7号検証後、**303/303件PASS**の独立報告がある。第8号の67件を合算した全スイートの**期待数370件**は**UNVERIFIED**。テストSKIPが全体で0件かどうかも独立環境で確認する。

## 合成CLI実測アンカー

`examples/history-cleaner/intake/events/` から7日別JSONL（**8イベント行**）を一時受け皿へコピーし、既存ロックの合成コピーとして空の`.intake.lock`を置き、
`--days 90 --as-of 2026-11-17T00:00:00+00:00 --source-roles config/examples/history-cleaner-source-roles.example.json`で実行。

- exit0、`status=preview`
- `record_count=8`イベント行
- `counts.candidate=2`（一般終端1件、明示reminder由来の終端1件）
- `counts.excluded=2`（unprocessed1件、audited1件）
- `counts.not_due=0`、`counts.hold=0`
- `safe_to_delete_count=0`、`records_changed=0`、`dry_run=true`
- 元の正本・合成ロックの**全ファイルSHA-256前後一致**。ロックや派生ファイルの追加なし。

## 合成単体テストで確認した重要事項

- 90日ちょうど／1秒未到来／1秒超過、別設定14日、終端遷移時刻起算、`reported`/`discarded`と`unprocessed`/`audited`の区別。
- 期限到来の由来不明→hold・exit2、reminder由来アイテムのイベント保護、source roleは申告であり`origin_verified_independently=false`、seen未分離・`prune_prepare_complete_verified=false`。
- 完了済みrunの保持規則不明→hold、エラー行付きrun→hold、稼働中run→excluded。エラー行保護件数確認。
- 未完のintake temp / prune logマーカー→hold、空ジャーナル/既存ロック欠落→holdまたは明示異常。正本のseq不連続、重複ID、不正遷移、未知イベント、日付不一致、NaN、重複JSONキー、リンク経路・改ざん入力はFail Closed。
- ドライランで入力ファイルのSHA-256・mtime不変。削除・seq再採番・checkpoint保存コードはない。

## 未実施と追加検証

- 第4号の**本物の**`shared_intake.py`で`ingest → audited → reported`を経てからの統合テスト：SKIP、P3独立cloneで必須。
- 第4号が受け付けるすべてのオプショナルフィールド、現行のflag/state整合性、重複排除の別保存、内部版の正規`prepare/complete`意味検証、reminder接続、定期cleanup、実レコード物理削除の動作：OUT_OF_SCOPEまたはUNVERIFIED。
- 根本的に公開JSONL v1は**既存行を消してよい根拠を提供しない**ため、候補を確定したことと安全削除の立証は別の問題。いかなる`candidate`も行削除の許可ではない。

[仕様](../operators/history-cleaner.md) / [P1裁定](../plans/history-cleaner-p1.md)
