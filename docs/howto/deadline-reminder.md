# 第7号：期限リマインダー係を合成データで試す

**PILOT。対象は合成JSONだけ。外部送信や自動スケジュールはしない。** Python 3.10以降とIANAタイムゾーンデータが必要。

## 安全な再現（Linux/macOSの例）

リポジトリのルートで：

```bash
python -m unittest discover -s tests -v
STATE_DIR="$(mktemp -d)"
python scripts/deadline_reminder.py --state-dir "$STATE_DIR" register --file examples/reminder/synthetic-item.json
python scripts/deadline_reminder.py --state-dir "$STATE_DIR" register --file examples/reminder/synthetic-item.json
python scripts/deadline_reminder.py --state-dir "$STATE_DIR" check --at-utc 2026-11-17T01:59:59+00:00
python scripts/deadline_reminder.py --state-dir "$STATE_DIR" check --at-utc 2026-11-17T02:00:00+00:00
python scripts/deadline_reminder.py --state-dir "$STATE_DIR" check --at-utc 2026-11-17T02:00:01+00:00
python scripts/deadline_reminder.py --state-dir "$STATE_DIR" outbox
python scripts/deadline_reminder.py --state-dir "$STATE_DIR" list
```

二重登録は`added=false`。時刻直前は発動0件、ちょうどで発動1件、その後は発動0件かつpending1件のまま。**このpendingは誰かへの配送が始まったという意味ではない。**

### 受領証明のシミュレーション（合成データ専用）

上記合成アイテムから決定的に生成されるoutbox IDは `out-6add08f4456005fc777486fcf3d54374acab967b`。同じ例の`synthetic-ack.json`を使って、手動の`ack`イベントを試せる。

```bash
python scripts/deadline_reminder.py --state-dir "$STATE_DIR" ack \
  --outbox-id out-6add08f4456005fc777486fcf3d54374acab967b \
  --receipt-file examples/reminder/synthetic-ack.json
python scripts/deadline_reminder.py --state-dir "$STATE_DIR" list
```

**重要：合成receiptは外部配送の証拠ではない。** このCLIが出す`consumer_verified=false`を確認する。実際の受け皿に届いたと主張したり、合成receiptを本番に使ったりしてはならない。

### 通常運用での誤解を避ける

- 登録前に、元項目の確定済み期限をUTC・IANA地域時・エポック秒へ変換する処理が別途必要。相対期限や自然文の解釈は行わない。
- `check`は手で呼ぶCLIであり、独立した起動設定を行わない。説明用に5〜15分間隔で外から起動すると仮定する場合、正常動作でも最大で概ねその間隔分だけ検出が遅れる。実際のOS休止、処理失敗、起動遅延に上限保証はない。
- 内部の別方式である**案件専用の単発cronジョブ＋当日の条件再確認＋日次突合**は、公開版では参考に留める。スクリプトはcronを作成しない。
- 状態ディレクトリには識別子、日時、受領情報があり得る。サンプル以外の入力、正本、outbox、障害記録を公開GitHubへ入れない。
- `deadline-events.jsonl`が壊れた場合は手で削除・切り捨てて復帰したとみなさない。エラーの種類・コピー・元情報を安全に確認してから個別復旧を検討する。

[契約](../operators/deadline-reminder.md) / [初心者向け説明](../explain/deadline-reminder.md)
