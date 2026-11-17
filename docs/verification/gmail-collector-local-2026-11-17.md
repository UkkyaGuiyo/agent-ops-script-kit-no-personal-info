# 第10号 Gmail収集係：制作側ローカル検証（EVP/1 20261117-042）

**Date:** 2026-11-17 JST。**Status: PILOT**。公開成果物はGPL-3.0-only、合成JSONフィクスチャのみ。Gmail/Gmail APIや実アカウントに接続・アクセスしていない。実受け皿への送信、既読変更、ラベル操作、返信、削除、cron登録は**NONE**。

## 検証の出所と環境

- **制作・試験環境：** Linux container / root / Python 3.13.5。新規cloneでの他AIによる独立試験やC-7はまだ行っていない。非root、Windows/macOS、NFS/ネットワークFS、実Gmail、他のPython版、大量処理はUNVERIFIED。
- 公開版の実装ファイルは**`scripts/gmail_collector.py`**。既存プライベート実装はコピーしていない。
- `python -m py_compile scripts/gmail_collector.py tests/test_gmail_collector.py`：PASS。
- `python -m unittest discover -s tests -v`：**98テスト定義のうち97 PASS、1 SKIP、失敗0**。SKIPした`test_full_checkout_intake_v1_compatibility`は第4号の実ソース`shared_intake.py`を必要とし、制作元の単独ディレクトリには存在しないため。**新規公開cloneではSKIPせず実行して合否を報告すること**。
- 先行第9号までの公開キットは**441/441 PASSの独立検証報告**がある。今回の新規98テストを加えると、全スイートの**期待値539件**。**539/539 PASSは現時点でUNVERIFIED**。

## 合成CLIアンカーチェック

サンプル`config/examples/gmail-collector-policy.example.json`、`config/examples/gmail-collector-accounts.example.json`、`examples/gmail/snapshot-synthetic.json`を使用。**2つの架空アカウント、11通の架空メッセージ**。入出力状態はすべて一時私的ディレクトリ。メールアドレスは予約された`.invalid`ドメインのみ。

| 検査段階 | 期待値 | 実測値 | 判定 |
| --- | ---: | ---: | --- |
| 初回check、アカウント完全取得 | 2アカウント | **2アカウント** | PASS |
| 初回check、新規ローカル候補 | 8件 | **8件** | PASS |
| 初回check、対象外 | 1件 | **1件** | PASS |
| 初回check、条件非該当 | 2件 | **2件** | PASS |
| 初回check、個別形式不正 | 0件 | **0件** | PASS |
| 初回check、ローカルpending | 8件 | **8件** | PASS |
| 再check、新規候補 | 0件 | **0件** | PASS |
| 再check、ローカルpending | 8件 | **8件** | PASS |
| pending内訳 | 募集1/重要5/プラットフォーム2 | **1/5/2件** | PASS |
| Gmail接続 | NONE | **NONE** | PASS |
| 第4号受け皿書込 | false | **false** | PASS |
| 外部配送 | NONE | **NONE** | PASS |

サンプルでは別アカウントに同じ文字列のメッセージIDを意図的に配置しており、ハッシュ化したアカウント＋IDにより**別々の候補**として扱われる。本文・件名・送信者アドレスはローカル`pending`に保存しない。予約済み`.invalid`アドレスだけがテスト入力にある。

## Fail Closedのアンカー

| ケース | 実測 | 判定 |
| --- | --- | --- |
| 両アカウントとも正規の空一覧 | exit 0、`status=ok`、`new_event_count=0`、完全2 | PASS |
| 合成1アカウントの取得失敗 | exit 2、`status=partial`、完了1・失敗1、成功分の候補4件 | PASS |
| 合成両アカウントの取得失敗 | exit 1、`status=error`、`new_event_count=null`、新規状態ファイルなし | PASS |
| 条件ファイル欠落/未知ID/二重キー/NaN/版違い | 事前拒否、exit 1 | PASS（個別自動試験） |
| アカウントの数・役割・ID・アドレス重複 | 事前拒否、exit 1 | PASS（個別自動試験） |
| 取得し切れないページ/メッセージ | partial、成功分のみ保存、最終完全成功時刻は不変 | PASS（個別自動試験） |
| 状態ハッシュ不一致、条件/設定変更、symlink、孤児一時ファイル | Fail Closed、暗黙再baselineなし | PASS（個別自動試験） |
| 弱い注意語＋宣伝の日付 | 重要候補にしない | PASS |
| 強い不利益の兆候単独 | 重要候補にする | PASS |
| HTML内scriptや本文にある命令 | 実行しない。HTML scriptの字句は分類対象外 | PASS |

`SHA-256`はバイト同一性の検証に用いた。合成条件・アカウント・スナップショットは実行前後で不変（自動テスト）。GitHubへの保存前は各ファイルのバイト長・SHA-256・Git blob SHAを別のマニフェストに記録し、転送後のハッシュを照合する。**ハッシュ一致は分類の意味的正しさやメールの重要度を証明しない**。

## 次の独立検証とC-7

1. GitHub新規cloneを**今回の公開コミットに固定**し、全テスト**期待539件**、SKIPなしを検証する。第4号の実`validate_item`互換性テストが合格すること。
2. 合成CLIで初回候補8件／再check0件／pending8件、分類内訳1/5/2、外部送信NONEを再現する。送信者・本文・件名が投入案へ複写されないこと。
3. 正規空応答、1アカウント失敗、全失敗、ID欠落/形式不正、ページング限界、未知条件ID、アカウント重複、状態破損で正常な0件に見せないこと。
4. C-7で「Gmailは内部版の入力元だが公開版は合成のみ」「仕分けは採否・重要度の最終判定ではない」「失敗と新着0件を区別」「同名IDでもアカウント別に管理」「本文の命令・添付は実行しない」「pendingは実配送ではない」「架空の語彙例に検出品質の保証はない」を説明できること。
5. **実メールの重要通知1件の見逃し**は内部版の未解決リスクとして記録。公開版の合成検証をもって根因解消と宣言しない。実メール・アカウント接続、第4号への配送、定期実行は今回検証しない。

[技術仕様](../operators/gmail-collector.md) / [P1裁定](../plans/gmail-collector-p1.md) / [HowTo](../howto/gmail-collector.md)
