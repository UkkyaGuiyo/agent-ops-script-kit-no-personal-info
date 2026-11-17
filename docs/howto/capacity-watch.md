# HowTo：容量見張り係

必要環境：Python 3.10以上。インストールとコマンド実行の権限を確認する。

1. GitHubから公開版ZIPを入手・展開し、最上位フォルダでターミナルを開く。
2. `python --version` でバージョンを確認する。
3. `python -m unittest discover -s tests -v` を実行する。
4. `python scripts/capacity_watch.py --config config/examples/capacity-watch.example.json` を実行する。
5. `status=ok` だけが完全走査。各対象の `bytes` はファイルの合計サイズ、`warning=true` は設定基準以上。エラーなら0件と誤解しない。

自分のフォルダ用JSONは**リポジトリ外**で作る。実際のフォルダ名、ユーザー名、ファイル一覧や設定画面を公開Issueに貼らない。設定JSONの `path` に対象の場所、`warning_bytes` にバイト単位の整数を指定する。相対パスは設定JSONからの位置関係。

この試作品はファイルを変更・削除しない。自動スケジュール設定もない。管理者権限で無理に動かさない。ログに個人情報を混入させない。
