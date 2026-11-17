# 初心者向けの入口

**個人情報流入禁止！！** GitHubの公開ページやIssueに、実際の名前・メール・パス・アカウント情報・ログを貼らないこと。

## この仕組みは何？
小さなプログラムが同じ確認作業を担当し、AIは結果を説明し、人間が重要な操作を決める。何でもAIに任せるより、何が実行されたのか分かりやすくする狙いがある。

## 最初に試せるもの
**容量見張り係**。指定したフォルダに含まれるファイルの合計サイズを調べ、基準を超えたか表示する。削除、送信、定期実行はしない。

1. Python 3.10以降を用意し、リポジトリのZIPを展開する。
2. 展開先でターミナルを開く。
3. `python -m unittest discover -s tests -v` を実行する。
4. `python scripts/capacity_watch.py --config config/examples/capacity-watch.example.json` を実行する。
5. `status: ok` のときだけ結果を確認する。`warning: true` は設定した値以上。失敗は `status: error` で、正常な測定結果ではない。

自分のフォルダを試すなら、設定JSONをリポジトリ**外**にコピーして変更する。実際の設定は絶対にGitHubへ登録しない。

[詳しい手順](docs/howto/capacity-watch.md) / [わかりやすい説明](docs/explain/capacity-watch.md) / [安全方針](SECURITY.md)

AIに手伝ってもらう場合は [AI_SETUP_GUIDE.md](AI_SETUP_GUIDE.md) と [AI_EXPLANATION_GUIDE.md](AI_EXPLANATION_GUIDE.md) を渡す。AIが実際にPC操作できるかどうかは別途確認する。

## 付け忘れ検出係（対象コミット限定VERIFIED）
[初心者向け説明](docs/explain/untagged-watch.md) / [導入HowTo](docs/howto/untagged-watch.md)。最初の実行では既存ファイルを覚えるだけで通知しない。ファイル自体には書き込まないが、観測履歴用の状態JSONは**キット外の専用フォルダ**に保存する。報告の受領確認（ack）は人間の判断。定期実行・受け皿送信・自動タグ付け・削除は未搭載。独立検証は報告済みだが、非root権限拒否の実測は未確認。

## 共通受け皿：新しい試作品
複数の係からの報告を一つにまとめ、**未処理が何件あるか**を旗で知らせる。AIや人間による判断は受け皿の外で行う。追記専用の正本ログから旗を作り直せる。書き込み可能な**キット外の専用データフォルダ**が必要。実データの公開は禁止。自動配信・削除・定期実行は実装していない。
[共通受け皿の初心者向け説明](docs/explain/shared-intake.md) / [導入手順](docs/howto/shared-intake.md)。対象コミット限定のVERIFIED。ただし他OS・非root動作は未検証。

## 投入量見張り係（PILOT）
AIに毎回読み込ませる常駐資料の**ファイル容量をバイト単位**で測る。大きさ・増加率が設定値を超えたときだけ、**キット外の私的フォルダ**へバックアップ・分類候補・下書き・比較レポート・機械的な自己テストを保存する。原本は自動変更しない。**意味や要点の保存は未審査**。トークン数の推定もしない。[HowTo](docs/howto/injection-size-watch.md) / [平易な説明](docs/explain/injection-size-watch.md)。
