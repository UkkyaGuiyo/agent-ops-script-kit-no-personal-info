# 保持管理係：合成デモで安全に試す

**警告：これは本番のファイル整理・削除ツールではない。** Linux/POSIXの一時領域に自分で作った空のデモフォルダでだけ`stage --apply`と`restore --apply`を実行する。**purgeは存在しない。**

## 1. 合成環境を作る

公開リポジトリのルートで次を実行する。

```bash
ROOT="$(mktemp -d)"
python scripts/retention_manager.py --root "$ROOT" demo-init
```

`demo-init`が架空の`old-disposable.txt`（15日前）、`fresh-disposable.txt`（13日前）、`permanent.txt`（60日前）と登録外の`unregistered.txt`を作る。登録時点でdisposable/permanentを宣言する。実ファイルの検索・変換は行わない。

## 2. 提案を表示する

```bash
python scripts/retention_manager.py --root "$ROOT" --age-days 14 preview
```

通常は`candidate=1`、`not_due=1`、`excluded=1`、`hold=0`。14日は**提案候補になるまでの間隔**で、物理削除の時間ではない。`preview`はファイルのSHA-256とmtimeを変えない。

## 3. 移動・ゴミ箱と復元

```bash
# まだ移動しない（--applyなし）
python scripts/retention_manager.py --root "$ROOT" stage

# 合成デモファイル1件だけを移す
python scripts/retention_manager.py --root "$ROOT" stage --apply
```

標準出力JSONの`items[0].entry_id`を読み取り、以下の`ENTRY_ID`へそのまま入れること。**実行時に出た値のみ使用**する。

```bash
ENTRY_ID="<stage結果のentry_id>"
python scripts/retention_manager.py --root "$ROOT" restore --entry-id "$ENTRY_ID"
python scripts/retention_manager.py --root "$ROOT" restore --entry-id "$ENTRY_ID" --apply
```

復元ではSHA-256と元の保存先が空であることを確認し、元のパスへ戻す。元のパスに別のファイルがあれば上書きせず停止。ゴミ箱内にはmanifestと監査が残る。`stage`や`restore`がエラーで止まったら、**繰り返し実行する前にデモのmanifestとpayloadを確認すること**。途中で止まったケースの自動復元はない。

## 4. テスト

```bash
python -m unittest discover -s tests -v
```

第6号Organizerの実コードとの比較試験は新規clone内で実行される。制作側の単体ディレクトリではSKIPになる。公開キット全体の期待テスト数は**618件（先行539＋本係79）**。これは独立環境の実測値ではない。

## 不実装・禁止

`purge`、実データへのapply、タグ自動変更、外部正本の判定、cron、Gitの履歴削除、既存AIタスク記録の変更、バックアップの自動消去は行わない。一時ディレクトリの後片付けは別工程。生の実行結果や実パスを公開リポジトリに投稿しない。
