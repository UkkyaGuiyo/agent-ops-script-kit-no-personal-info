# HowTo：保持タグ付け忘れ検出係

**個人情報流入禁止！！** 本人の実フォルダ名、実台帳、設定JSON、状態JSON、実行結果をGitHub・Issue・公開チャットに貼らない。

## この係ができること
「前の確認では無かった、保持タグの登録がない通常ファイル」を知らせる。既にあった未登録ファイルは初回のベースラインに含まれ、最初から大量通知しない。**削除や自動タグ付けはしない**。ただし通知のための**状態ファイルは作成・更新する**。

## 必要条件
Python 3.10以降、ローカルの読み取り権限、そしてキットのフォルダや調べるフォルダの**外側**に作った空の状態保存フォルダ。外部アカウントは不要。実際のデータではなく、まず合成サンプルを試す。

## Linux / macOS の例
```bash
python -m unittest discover -s tests -v
STATE_DIR="$(mktemp -d)"
python scripts/untagged_watch.py scan \
  --config config/examples/untagged-watch.example.json \
  --state-dir "$STATE_DIR"
```
サンプルの最初の結果は `status: baseline`、観測ファイル **1件**、新規未登録 **0件**。次回までにそのルートに**新しい通常ファイル**ができた場合、`pending` のJSONが表示される。サンプルの既存ファイルは初回に報告しない。

WindowsではPowerShellなどでキット外の作業フォルダを作成し、`--state-dir` に指定する。Python起動コマンドは環境により `python` または `py`。

## pendingと受領確認
```bash
python scripts/untagged_watch.py scan --config <config-json> --state-dir <state-dir>
python scripts/untagged_watch.py ack --config <config-json> --state-dir <state-dir> --event-id <event-id>
```
**ackは、利用者が報告を確認したか、別の保存先に確実に保存した後にのみ実行する。** 画面へ表示されただけで配送完了とはならない。pendingの間に再実行すると、同じイベントIDの報告が再び表示される。重複報告を受け取る側はイベントIDで重複排除する。

## 結果とトラブル
- 終了 **0**：正常実行。pendingであっても配送は未確認。
- 終了 **3**：ロック競合。今回は実行せず、先行処理や残留ロックを人間が確認する。
- 終了 **1**：失敗。記録JSON不正、状態のハッシュ不一致、読み取り不能、設定変更など。**「新着なし」とみなさない。**
- 残留した一時状態ファイルを勝手に消さない。破損したstateを自動再作成しない。状態を捨てると、再ベースラインで過去の未タグが報告されなくなる可能性がある。

設定JSON、記録JSON、状態JSON、出力JSONは機密扱い。ルートの記録形式は[技術仕様](../operators/untagged-watch.md)を参照。パスは**ルート相対**で、`..`は使えない。

[初心者向けの説明](../explain/untagged-watch.md) · [P1設計](../plans/untagged-watch-p1.md).
