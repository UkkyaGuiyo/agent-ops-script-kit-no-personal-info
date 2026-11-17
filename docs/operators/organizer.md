# 整理係：保持タグ寿命の**提案のみ**を行う技術仕様

**Status: VERIFIED for commit 84ca9fe08fb21658fab05e99a5029f55ee2d56ab (reported fresh clone on Linux/root).** Full-kit 223/223 tests and initial-Muse C-7 explanation PASS reported. Non-root access denial, other OS, network filesystems and large datasets UNVERIFIED. No formal RELEASED tag. GPL-3.0-only; Python 3.10+ standard library.

## 役割

「整理」はファイルをフォルダに振り分けることではない。**作成時にタグ付けされたローカルファイルの寿命判定**である。内容・用途・外部の正本の有無を推測しない。ファイル本文は読まない。JSONの所属記録だけ読む。対象は登録済みパスのみ。

`disposable` かつ「mtimeから経過時間が設定日数以上」なら `candidate`（ゴミ箱移動の**提案**）。`permanent` は候補にしない。日時はUTC、経過は24時間単位、比較は**ちょうど閾値を含む `>=`**。ファイル作成時刻や最終アクセス時刻は判定しない。時刻が将来なら `hold`。

## 設定

```json
{
  "version": 1,
  "age_days": 14,
  "roots": [
    {
      "name": "synthetic-root",
      "path": "../../examples/organizer/root",
      "exclude_subtrees": []
    }
  ]
}
```

- `version` は整数1。`age_days` は0〜365000の整数、サンプルは14日、利用者が変更できる。`14`は公開サンプル値であり、一般のファイルを14日で削除してよいという意味ではない。
- `roots`: 1件以上。`name` は一意の安全な英数字/ハイフン/アンダースコア（1〜48文字）。`path` は存在するローカルディレクトリで、設定ファイルを基準とした相対パスか絶対パス。ルートが重複・内包する場合はエラー。親経路を含むリンクは拒否。
- `exclude_subtrees` はルート相対の配列。絶対・`..`・空区間・バックスラッシュは禁止。組み込み対象外名：`.git`、`node_modules`、`__pycache__`、`venv`、`.venv`、`.trash`。
- ルート直下に `.retention_records.json` が**必須**。形式は `{"entries":[{"path":"sub/sample.txt","class":"disposable"}]}`。トップレベル `version:1` は任意。`path` は安全な相対パス。`class` は `disposable` / `permanent` のみで判断する。未知のラベルは削除候補にはせず `hold`。同一パス重複や不正JSONの記録全体はエラー。
- 第3号付け忘れ検出係と同じ公開版のレコード形式を使うが、他の管理ツール・内部版との完全互換を保証しない。

## 出力スキーマ（stdout JSON）

- `status: "ok" | "candidates" | "partial" | "error"`。
- `as_of_utc`: ISO-8601 timezone-aware UTC。`age_threshold_days`: 日。`counts`: `candidate` / `not_due` / `excluded` / `hold` の**記録件数**。`items` は各記録について `root`、`record_index`、`relative_path`（危険な入力はnull）、`tag_class`、`decision`、`reason`（機械可読）、`age_seconds`（取れない場合null）、`threshold_days`。
- `dry_run=true`、`changed_files=0`、`trash_move_available=false`、`purge_available=false`、`deletion_available=false`、`unregistered_files_scanned=false`。
- パス・所属記録が不明でも `candidate=0` を正常値として返さない。`hold` が1件以上存在すれば `status=partial` / exit1。設定・記録破損なら `status=error` / exit1で分類件数を返さない。
- ログ・出力に含まれる**相対ファイル名や日時は個人情報を含む可能性がある**。実物の結果をGitHub等に投稿しない。エラーメッセージは実パスを出さない。

## 判定状態

| タグ・状態 | 結果 | 原因 |
| --- | --- | --- |
| 登録あり、`disposable`、mtimeが閾値以上 | `candidate` | `DISPOSABLE_MTIME_AGE_AT_LEAST_THRESHOLD` |
| 登録あり、`disposable`、閾値未満 | `not_due` | `DISPOSABLE_MTIME_AGE_BELOW_THRESHOLD` |
| 登録あり、`permanent`、通常ファイル | `excluded` | `PERMANENT_TAG` |
| 非対象フォルダ・記録自身 | `excluded` | `EXCLUDED_BY_SCOPE` |
| 未知タグ、記録先欠落、危険な記録パス、リンク経路、mtime異常等 | `hold` | 明示的な理由コード |
| レコード外のファイル | **調べない** | 登録状態を推測しない |

## CLI・終了コード・復旧

`python scripts/organizer.py --config config/examples/organizer.example.json`

`--as-of 2026-11-17T00:00:00+00:00` は合成テスト用に時刻を固定したい時だけ指定する。普通は指定せず現在のUTCを使う。

- **exit 0**: `ok` または `candidates`。操作実施の意味ではない。
- **exit 1**: `partial`（保留あり）または `error`（全体の信頼性なし）。保留を候補とみなさない。
- **exit 2**: argparseによる未知の操作引数等。`apply`、`purge`、`move`コマンドは存在しない。
- 本ツールに永続状態、通知、ack、スケジュール、タグ登録、ゴミ箱移動、マニフェスト生成、物理削除、復元機能は**NONE**。止めても実ファイルは変更されない。

## 制限

走査中の外部変更やTOCTOUは防げない。ドライランの表示を移動の承認に流用してはならない。物理削除の「1か月」や受け皿の「90日」は別機能の仕様で、公開版では期間設定も実行も不採用。非root/Windows/NFS・巨大な所属記録は未検証。

[P1裁定](../plans/organizer-p1.md) / [HowTo](../howto/organizer.md) / [初心者説明](../explain/organizer.md) / [制作側試験](../verification/organizer-local-2026-11-17.md) / [独立検証概要](../verification/organizer-independent-2026-11-17.md)。
