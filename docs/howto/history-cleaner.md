# HowTo：履歴掃除係を合成データで試す

**最初に：記録は消さない。** この係は第4号の受け皿JSONLを読んで、90日を超えた終端アイテムの候補だけを示す。実受け皿・実出力の公開は禁止。

## 環境

- Python 3.10+（標準ライブラリ）。合成データで先にテスト。
- このGitHubリポジトリをチェックアウトしていること。
- Linux/macOSでは次の例。Windows/非rootの実地検証はまだ。

```bash
python -m unittest discover -s tests -v

INTAKE_DIR="$(mktemp -d)"
cp -R examples/history-cleaner/intake/events "$INTAKE_DIR/events"
touch "$INTAKE_DIR/.intake.lock"

python scripts/history_cleaner.py \
  --data-dir "$INTAKE_DIR" \
  --source-roles config/examples/history-cleaner-source-roles.example.json \
  --days 90 \
  --as-of 2026-11-17T00:00:00+00:00
```

期待アンカー：`record_count=8`（イベント行8件）、`candidate=2`（一般終端1件、reminder終端1件）、`excluded=2`（unprocessedとaudited）、`hold=0`、`safe_to_delete_count=0`、`records_changed=0`、exit0。**candidate=2は削除OKが2件という意味ではない。**

## 異常・保留の確かめ方

`--source-roles`から`synthetic-reminder`等を削ると、期限到来で由来不明の項目は`hold`になり、exit2を返す（例のsource名は実際には`synthetic-reminder`）。また、元の正本JSONLに不正行・欠番・未知kindを入れた場合はexit1で止まる。どちらも**正常0件ではない**。

`events/`は第4号の正本なので、実験のためでも**既存運用受け皿を編集しない**。異常系試験は必ず別の合成コピーで行う。`.intake.lock`は第4号と共有する既存ロックの合成コピーであり、本係は作成しない。

## 実運用を想定する前に

- 実ID入りの`source_roles`設定は公開Git外へ置く。sourceとroleの対応は利用者の**宣言**であり、外部証明ではない。
- タグ付けのないsourceは保留。期限が来ても、削除する行を選べたわけではない。
- 実データでの`--as-of`指定を避ける。検査結果をそのまま削除スクリプトに流用しない。
- 第4号に`prune_log`や未完の`prepare`がある場合、公開v1の根拠検証では対応できず保留・エラーとなる。
- 物理削除・イベント間引き・seq詰め直し・チェックポイント書換えはこの公開実装に存在しない。第4号の現行`retention-preview`とも別のread-only監査である。

[技術仕様](../operators/history-cleaner.md)／[初心者向け説明](../explain/history-cleaner.md)
