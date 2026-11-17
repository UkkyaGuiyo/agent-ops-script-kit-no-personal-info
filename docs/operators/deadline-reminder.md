# 第7号：期限リマインダー係の公開パイロット技術仕様

**Status: VERIFIED for deae5969af6ab358e700b9e8e3b68f159bc032b2 within reported Linux/root local scope.** 別環境検証担当AIから新規clone全303/303件PASS、初期状態Muse説明再現PASSが報告された。外部配送・第4号接続はOUT_OF_SCOPE。非root・他OS・長期運用はUNVERIFIED。正式RELEASEDではない。Python 3.10+、標準ライブラリ（IANA tzdb必要）。GPL-3.0-only。

## 目的と非目的

日時が**絶対時刻として確定済み**の一回限りの条件をローカルへ登録し、手動`check`の時点で期限到来した条件を一度だけ`fired`に遷移させる。発動した条件のoutbox IDとpending状態を永続化する。**その先に何をするかは判断せず、実配送、受け皿接続、外部通知、cron登録はしない。**

## 入力型

```json
{
  "schema_version": 1,
  "origin_id": "synthetic-case-01",
  "condition_id": "synthetic-deadline",
  "due": {
    "utc": "2026-11-17T02:00:00+00:00",
    "local": "2026-11-17T11:00:00+09:00",
    "timezone": "Asia/Tokyo",
    "epoch_seconds": 1794880800
  }
}
```

`origin_id`、`condition_id`はASCII英字始まり、英数字/点/下線/ハイフンを続けて最大128文字。`epoch_seconds`は**整数秒**（bool、float、文字列、NaN、Infinityは拒否）。`utc`は秒精度で`+00:00`、`local`は秒精度で明示offset、`timezone`はIANA名。3表現が同じ瞬間かつ指定IANA地域の実際のoffsetと地方時に一致することを検証。存在しない夏時間の地方時は拒否。公開版の例示期限は2000-01-01から2099-12-31までに限定。相対指定・猶予時間・繰返しは未対応。

冪等ID=`rem-`＋SHA-256（`origin_id`,`condition_id`,`epoch_seconds`の正規JSON）の先頭40桁。**秒とIDの組に相当する同じ投入**は`added=false`。異なる内容で同じIDになる再投入は拒否。日時変更時は旧IDを`cancelled`にして新IDを生成し、双方の変化を一個の追記イベントに記録する。変更後の旧IDも履歴に残る。

## ファイル、寿命、ロック

`--state-dir`は**存在する**ローカル私的ディレクトリ。必ず公開チェックアウトの外に設ける。親ディレクトリ・状態ファイル・入力ファイルのシンボリックリンクは拒否。

- 正本：`deadline-events.jsonl`（1行1イベント、UTF-8 JSON、`seq`は1から欠番なし、イベントID重複なし、状態遷移を再生時に全件検査）。追記後`fsync`。
- 派生：`deadline-outbox.json`。各`fired`から決定的に生成されるoutboxエントリと`pending`/`delivered`（後者は**外部から申告された受領を保存しただけ**）。正本が正常であれば`repair-outbox`または次の`check`で再構成できる。
- 障害記録：`deadline-failures.json`。正本とは別で、`check`の失敗を一般化エラーコードで記録する。開いた障害は重複集約し、成功で解消扱い、その後の再発は新規発生。障害台帳のSHA-256は偶発的整合性確認だけで、署名ではない。
- ロック：`.deadline-reminder.lock`を削除せず使う（POSIX flock、Windows msvcrt.locking）。ロック競合exit3。派生更新中に失敗した`.deadline-temp-*`は自動で無視せず、要確認エラーにする。

**原本と派生ファイルの同時原子更新は不可**。原本追記後の派生保存失敗では成功を返さないが、正本が完全な場合は再生で派生を復元できる。途中で壊れた正本JSONLは**自動で切り捨てない**。

## アイテムと配送の状態遷移

- アイテム：`active → fired`（`due.utc <= check.at_utc`）、または`active → cancelled`。`reschedule`は旧`active`の取消と新`active`の登録。`fired`の取消・再発動・再予定は拒否。
- 配送：発動した項目から`pending` outboxを生成。再`check`はpendingを**同じIDで再表示するだけ**。送信試行は`0`、外部配送は`NONE`。
- `ack`は`{"schema_version":1,"status":"accepted","outbox_id":"...","consumer_id":"...","receipt_id":"..."}`を読み、IDと形の整合だけ検証して**手動の受領申告**として`delivery_attested`イベントを追記。出力は常に`consumer_verified=false`。受け皿内の実物検査や受信者の真正性確認は**行わない**ため、出力`delivery_state=delivered`は実際の到達保証ではない。未検証のreceiptで安易にackしないこと。
- 決定的outbox ID：`out-`＋SHA-256（`"deadline-fired"`とreminder_idの正規JSON）の先頭40桁。再check、プロセス再起動、派生復旧で同一。

## CLI・出力

```text
python scripts/deadline_reminder.py --state-dir PRIVATE_DIR register --file ITEM.json
python scripts/deadline_reminder.py --state-dir PRIVATE_DIR reschedule --reminder-id ID --due-file DUE.json
python scripts/deadline_reminder.py --state-dir PRIVATE_DIR cancel --reminder-id ID
python scripts/deadline_reminder.py --state-dir PRIVATE_DIR check [--at-utc ISO_UTC]
python scripts/deadline_reminder.py --state-dir PRIVATE_DIR list
python scripts/deadline_reminder.py --state-dir PRIVATE_DIR outbox
python scripts/deadline_reminder.py --state-dir PRIVATE_DIR repair-outbox
python scripts/deadline_reminder.py --state-dir PRIVATE_DIR failures
python scripts/deadline_reminder.py --state-dir PRIVATE_DIR ack --outbox-id ID --receipt-file RECEIPT.json
```

`--at-utc`は**合成試験用**。通常の実利用では省略してUTC現在時刻を使う。`check`の`new_fired_count`は**今回初めて発動した件数**、`pending_delivery_count`は再送待ちの件数。発動件数の再計上は禁止。`list`と`outbox`は正本から算出し、派生の欠落・stale・破損を`derived_warnings`で示す。`repair-outbox`は正本を変更しない。

終了コード：`0`成功、`1`不正入力/正本破損/保存失敗等、`3`ロック競合（実行を飛ばす）。未知CLI動作はargparseの`2`。エラーは**新着0件ではない**。外部アカウントにアクセスしない。

## 重要な未実装

- 第4号共通受け皿への実送信・保存現存確認、受け皿の処理済み90日経過後の不在許容、outbox自動配送再試行、受信者認証、受信者による閲覧確認、定期起動、単発cron、通知内容解釈、キャンセル記録の物理削除。
- 非root、他OS、tzdb差異、長期間、大量レコード、同一state dirのネットワークFS、クロック逆行、攻撃者による正本再編集に対する強度は独立検証していない。

[P1裁定](../plans/deadline-reminder-p1.md) / [HowTo](../howto/deadline-reminder.md) / [初心者への説明](../explain/deadline-reminder.md) / [制作側テスト](../verification/deadline-reminder-local-2026-11-17.md)

[独立検証概要](../verification/deadline-reminder-independent-2026-11-17.md)。
