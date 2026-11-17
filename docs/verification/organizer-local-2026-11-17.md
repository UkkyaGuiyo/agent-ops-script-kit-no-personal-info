# 第6号 整理係：制作側ローカル検証

**Date:** 2026-11-17 (JST)  
**Status:** PILOT / 別環境検証担当AIの独立新規clone・C-7説明試験はPENDING。  
**Environment:** Linux container, Python 3.13.5. 合成一時ルートのみ使用。

## 実施事項

- `python -m unittest discover -s tests -q`：**55/55 PASS**。この数字は第6号単体の55件であり、既存5系統を含めた全スイートではない。
- `python -m py_compile scripts/organizer.py`：PASS。
- 正常サンプル（Git checkout時のmtimeによる）：登録済み2件、`permanent` 1件 `excluded`、`disposable` 1件 `not_due`、`status=ok`。GitHubからの取得後のmtimeは環境依存で固定アンカーとしては使わない。
- mtime境界：14×24時間ちょうどは `candidate`、1 ns未到来は `not_due`、1 ns以上経過は `candidate`。
- タグ境界：`permanent` は対象外、未登録ファイルは**一切調べない**、未知ラベルは `hold`。欠落、危険な相対パス、リンクパス、未来mtime、不正なレコードは保留または明示エラー。
- 複数ルート、重複・内包ルート拒否、所属記録の重複パス・重複JSONキー拒否、設定不正、明示的除外、異常CLI引数を確認。
- 合成元ファイル・所属記録・設定ファイルの**SHA-256、mtime不変**。実ファイル内容の読取が行われないことをモックで検査。`.trash` は作成されなかった。
- `status=partial` のexit 1、`status=error` のexit 1、正常候補のexit 0。エラーでも正常な「0候補」に偽装しない。

## 合成ファイルの静的アンカー（GitHub原文として同一性を検証可能）

| Path | bytes | SHA-256 |
|---|---:|---|
| `examples/organizer/root/sub/sample.txt` | 56 | `3a529a4d125bb844369b3461908bc151074ae320e985edfc956f3b5aa53424f2` |
| `examples/organizer/root/fixed.txt` | 65 | `b539a6a0fa9244ce9513000156479725b1bf69c4d7952855a6a865551c45d749` |
| `examples/organizer/root/.retention_records.json` | 142 | `c15d16da10a91b602b6245dfb41f42c10ea9b7bd652b2b016cb4d1d5bdbc81df` |

## 未検証

- 非rootでの実ファイルシステム権限拒否は未実証。モックでは保留となることを試験した。
- Windows、別のファイルシステム、非常に多数の登録パス、ファイル走査中の競合は未検証。
- 第6号の**ファイル移動・削除・パージ**は実装自体が無いため試験対象にならない。内部版の実動作と同等とは主張しない。
- 新規cloneでの全系統テストとMuseによる初期状態の説明再現は未実施。

## 次の検証

公開コミットを厳密に固定して新規cloneし、全テスト、上のアンカーチェック、14日の境界、未登録/permanent保護、原本不変、未知タグ・危険な記録のFail Closed、ドライラン専用・不存在のapply/purge、C-7説明再現を独立確認。正式リリースには別途P4/P5を要する。
