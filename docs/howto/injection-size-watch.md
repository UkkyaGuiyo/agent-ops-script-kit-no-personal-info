# HowTo：投入量見張り係

**個人情報流入禁止！！** 実設定、常駐記憶の本文、バックアップ、下書き、状態ファイル、実パス、CLIの結果JSONを公開リポジトリ・Issue・外部チャットに貼らない。

## 何をする？
指定した常駐コンテキストファイルの容量をB単位で測り、履歴と比べる。超過したら**原本に触れず**、別フォルダにバックアップと安全な下書き・比較報告を作る。AIモデルのトークン数を計算しない。下書きを元ファイルへ戻す機能はない。

## 合成サンプルを試す
Python 3.10以降。リポジトリを展開した場所でターミナルを開く。Linux/macOSでは次の手順。状態フォルダは**キットの外**にする。

```bash
python -m unittest discover -s tests -v
STATE_DIR="$(mktemp -d)"
python scripts/injection_size_watch.py \
  --config config/examples/injection-size.example.json \
  --state-dir "$STATE_DIR"
```

このサンプルは一般に`status=ok`、2つの合成ファイルの実バイト数と`total_bytes`を返す。初回の週次増加率は `UNKNOWN_NO_BASELINE`。これが正しい。毎日の測定は可能だが、7日以上前の参照点がないうちは週次判定ができない。

## 下書きまで試す

**前のサンプルとは別の新しい**状態フォルダを作る。警告用設定ではJSONサンプルの上限を1 Bにしてある。原本は公開用の合成データのみ。

```bash
DRAFT_STATE_DIR="$(mktemp -d)"
python scripts/injection_size_watch.py \
  --config config/examples/injection-size-warning.example.json \
  --state-dir "$DRAFT_STATE_DIR"
```

`status=warning`、`package_id`が出る。`$DRAFT_STATE_DIR/package-<package_id>/`に`backups`、`drafts`、`audit.json`、`classification.json`、`comparison.json`、`self_test.json`、`manifest.json`が保存される。JSONの余白が減った分だけ実測の削減値が出るが、下書きは自動適用されない。

WindowsではPowerShell等でキット外に専用の空フォルダを手動で作成し、`--state-dir`に指定する。現時点のWindows動作は独立検証前。

## 自分のファイルを測る場合
設定例をキットの**外**にコピーし、`targets`を明示的な常駐ファイルだけに変更する。上限も用途に応じて設定し、必ずバックアップを保存できる私的な状態フォルダを選ぶ。バックアップに秘密が複製されるため、共有フォルダや公開Git管理下は不適切。権限昇格で無理に読まない。

結果が`error`または終了コード1の場合、合計0Bや異常なしとは解釈しない。部分的に測れたファイルがあっても、全体合計と履歴は確定しない。競合終了コード3は後で手動確認。壊れた履歴や途中生成物を勝手に捨てて再ベースラインしない。

## 判断の境界
**A/B/Fは機械的な暫定分類にすぎない。** C/D/Eは自動生成しない。Markdownの意味的な圧縮、言い換え、要点保持の検証はできないため、そうした作業は人間の判断と別工程に置く。`self_test.json`の`NOT_ASSESSABLE`をPASSと読み替えない。

[技術仕様](../operators/injection-size-watch.md) / [平易な説明](../explain/injection-size-watch.md).
