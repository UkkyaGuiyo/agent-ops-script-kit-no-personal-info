# Gmail収集係：オフライン合成データで試す

**実メールは一切使わない。** Python 3.10以降、追加パッケージなし。これはGmail APIや接続済みのメールサービスを利用する操作手順ではなく、公開キットの**合成分類器**を動かす手順。

## 1. 公開キットを取得する

```sh
git clone https://github.com/UkkyaGuiyo/agent-ops-script-kit-no-personal-info.git
cd agent-ops-script-kit-no-personal-info
python -m unittest discover -s tests -v
```

このオペレーターは独立検証前はPILOT。全キットのテスト件数やSKIP数は必ず実測し、期待数と区別する。

## 2. 非公開の一時ディレクトリを用意する

```sh
STATE_DIR="$(mktemp -d)"
```

状態をGitリポジトリ内部へ置かない。実メールのIDや件名を含み得る状態JSON・標準出力を公開しない。Windowsでは利用者が用意した公開チェックアウト外のディレクトリを`--state-dir`へ指定する（Windows動作は未検証）。

## 3. 合成フィクスチャをcheckする

```sh
python scripts/gmail_collector.py \
  --policy config/examples/gmail-collector-policy.example.json \
  --accounts config/examples/gmail-collector-accounts.example.json \
  --state-dir "$STATE_DIR" \
  check --fixture examples/gmail/snapshot-synthetic.json
```

合成データには**2アカウント・11通**あり、想定値は次のとおり。

- `status=ok`、`new_event_count=8`、`pending_proposal_count=8`
- `accounts_complete=2`、`accounts_failed=0`、`invalid_messages=0`
- `excluded_messages=1`、`unmatched_messages=2`
- `gmail_connection=NONE`、`shared_intake_write=false`、`external_delivery=NONE`

同じコマンドを再実行すると`new_event_count=0`、`pending_proposal_count=8`（既存候補は重複追加されない）。これは**ローカル差分検出の成功**であり、外部メール送信や第4号受領の成功ではない。

## 4. ローカル投入案を見る

```sh
python scripts/gmail_collector.py \
  --policy config/examples/gmail-collector-policy.example.json \
  --accounts config/examples/gmail-collector-accounts.example.json \
  --state-dir "$STATE_DIR" pending
```

`proposals[]`内の`item`は第4号公開v1の形式に合わせた**未配送の候補**。この操作でもGmail/第4号へ接続しない。`pending`のJSONにはアカウント役割、ハッシュ参照、検出時刻などのデータがある。実データに差し替えて実行しない。

## 5. 正規の空応答を試す

**別の空状態ディレクトリ**を作り、次を実行する。

```sh
EMPTY_STATE_DIR="$(mktemp -d)"
python scripts/gmail_collector.py \
  --policy config/examples/gmail-collector-policy.example.json \
  --accounts config/examples/gmail-collector-accounts.example.json \
  --state-dir "$EMPTY_STATE_DIR" \
  check --fixture examples/gmail/snapshot-empty.json
```

この**正規の完了済み空一覧**だけが`status=ok,new_event_count=0`。アカウント応答の欠落、形式不正、ページ上限、取得不能なら`partial`または`error`となるため、「新着がなかった」と解釈しない。

## 6. 安全な停止と復旧の原則

- CLIは手動同期実行のみ。定期ジョブを自動で追加しない。`pending`を失わないうちに状態ファイルを勝手に消さない。
- 構成JSONの内容が変わると既存状態とSHAが一致せず、Fail Closed。既存stateを無断でリセット・再baselineしない。
- 状態破損、シンボリックリンク、ロック競合、書込み途中の一時ファイルは停止して原因を確認する。破損を「0件」に変換しない。
- 全件確認できない場合は正常報告をしない。一部取得の成功分はローカルに保持できるが、`last_success_at`は更新しない。
- 実メールへの適用、Gmail接続、既読化、ラベル変更、受け皿への実投入、通知・返信・応募はすべて**別途設計と承認が必要**。

[技術仕様](../operators/gmail-collector.md)／[説明](../explain/gmail-collector.md)／[P1裁定](../plans/gmail-collector-p1.md)
