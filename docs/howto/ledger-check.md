# HowTo：台帳係（試作品）
**個人情報流入禁止！！** 実台帳、実パス、検査結果のJSON、画面写真をGitHubやIssueへ投稿しないこと。

## 必要なもの
Python 3.10以上、手動でコマンドを実行できる環境。外部アカウント不要。台帳を変更する権限も不要。

## 手順
1. 公開リポジトリを新規cloneまたはZIP展開し、ルートでコマンドを実行。
2. 先に **python -m unittest discover -s tests -v** を実行。
3. 合成台帳を検査：**python scripts/ledger_check.py examples/ledger/synthetic-ledger.md**
4. 表示されたJSONの status=ok と entries を確認。合成台帳の標準例は終了コード0。
5. 自分の台帳を検査するときだけ **python scripts/ledger_check.py /your/local/ledger.md** のように実際のファイルをローカルで指定。
6. 完了を台帳に残す運用なら **--allow-completed** を追加。他の形式異常は引き続き検出する。

## 結果の読み方
- **exit 0**：指定した書式規則では異常を見つけなかった。実際の仕事が終わっている保証ではない。
- **exit 2**：検査できたが異常報告あり。issues の type と line を見て、人間が台帳を確認する。
- **exit 1**：ファイルを読めなかった。正常な空台帳として扱わない。

## 制限
本試作品は行頭のタスク箇条書きを認識するため、関係ない箇条書きを台帳に混ぜると異常と判定しうる。後続の別用途表を台帳表から区別するには異なる見出しを使い、表の後は空行などの非表行を置く。同じ見出しの別用途表は区別できない。パスの実在は実行端末の権限・OSで判定する。

[技術仕様](../operators/ledger-check.md) / [初心者向け説明](../explain/ledger-check.md).
