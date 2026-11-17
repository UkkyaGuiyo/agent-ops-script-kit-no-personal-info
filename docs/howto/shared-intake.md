# HowTo：共通受け皿（PILOT）

**個人情報流入禁止！！** 実データ、設定、ログ、実際のパス、メールアドレス、トークンを公開リポジトリやIssueへ入れない。以下は合成データだけで動かす例。

## 準備

- Python 3.10以降、ローカルでコマンドを実行する権限。
- キットのダウンロード先とは**別の場所**に私的な受け皿用フォルダを作る。既存のデータを使わず、初回は空のフォルダを指定する。
- 外部サービス接続、AI実行、スケジューラーは不要。Windowsでの実動作検証は未完了。

### Linux / macOSで架空アイテムを試す

```bash
python -m unittest discover -s tests -v
INTAKE_DIR="$(mktemp -d)"
python scripts/shared_intake.py --data-dir "$INTAKE_DIR" ingest --file examples/intake/synthetic-item.json
python scripts/shared_intake.py --data-dir "$INTAKE_DIR" status
```

1回目の`ingest`は`added: true`。同じファイルを再投入すると`added: false`で、件数は増えない。`flag.json`で`unprocessed_count=1`、`raised=true`を確認できる。

### 次の段階へ進める

`item_id` は上の投入結果から取得する。**以下の識別子は置き換える。**

```bash
python scripts/shared_intake.py --data-dir "$INTAKE_DIR" transition --item-id <item-id> --to audited --event-id synthetic-audit-001
python scripts/shared_intake.py --data-dir "$INTAKE_DIR" transition --item-id <item-id> --to reported --event-id synthetic-report-001
python scripts/shared_intake.py --data-dir "$INTAKE_DIR" status
```

状態を進めるのは人間または承認されたAIの役割。`event-id`は**再試行では変えず**、別の操作では新しいIDを使う。`discarded`は未処理・監査済みからのみ指定できる。

### 取得失敗を記録する

```bash
python scripts/shared_intake.py --data-dir "$INTAKE_DIR" run-start --source-id synthetic-source --run-id example-run-1
python scripts/shared_intake.py --data-dir "$INTAKE_DIR" run-error --source-id synthetic-source --run-id example-run-1 --error-id example-error-1 --error-code FETCH_FAILED
python scripts/shared_intake.py --data-dir "$INTAKE_DIR" run-finish --source-id synthetic-source --run-id example-run-1 --outcome error
```

`outcome=error`は「新着0件」と同じ意味ではない。`partial`は途中まで取得できた状態を区別する。

### 旗を再構築する／削除候補を調べる

```bash
python scripts/shared_intake.py --data-dir "$INTAKE_DIR" status
python scripts/shared_intake.py --data-dir "$INTAKE_DIR" rebuild
python scripts/shared_intake.py --data-dir "$INTAKE_DIR" retention-preview --days 90
```

`rebuild`は追記ログを改変せず、派生した`flag.json`と`state.json`だけを作り直す。正本のJSONLが壊れていた場合は**失敗して止まる**。`retention-preview`は候補表示のみで、**どのファイルも削除しない**。未処理項目は候補に含めない。

## 付け忘れ検出係との手動接続

1. 付け忘れ検出係の `scan` で `pending` が返ったことを確認し、**キット外**の私的なファイルへJSONを保存する。
2. `python scripts/untagged_to_intake.py --file <private-pending.json> > <private-intake-item.json>` で変換する。
3. `python scripts/shared_intake.py --data-dir <private-intake-dir> ingest --file <private-intake-item.json>` で保存する。
4. `status=accepted`かつ**終了コード0**を確認する。`added=false`でも同一アイテムが保存済みで旗の再計算が成功していれば受領できている。
5. **この後だけ**元の`untagged_watch.py ack`を元のイベントIDで実行する。自動ackは搭載していない。

注意：pendingに書かれた相対ファイル名も個人情報になりうる。変換出力・実行結果を公開しない。

## 失敗したとき

| 終了コード | 意味 | 対応 |
|---|---|---|
| 0 | 指定操作は成功 | `added`、`status`、旗を確認 |
| 1 | 不正な入力・I/O・正本破損など | **成功や新着0件と扱わない**。記録を保全し、原因を確認 |
| 3 | 共通ロックを取得できなかった | 今回は何も実行せず、先行操作を確認 |

ログに途中で切れた行があるとき、勝手に削除しない。`events/`は追記専用の正本。原状を把握してから対応する。見かけ上古い項目でも自動削除は存在しない。

[技術仕様](../operators/shared-intake.md) / [初心者向け説明](../explain/shared-intake.md)
