# 保持管理係：デモ領域限定の段階式保持管理

**Status: VERIFIED for code commit 992e1e6430788514b5c9e19c66036a080bd592dd within reported Linux/root synthetic demo scope.** 別環境検証担当AI報告：新規clone618/618件PASS、SKIPなし（第6号実統合含む）、合成stage/restoreのSHA-256一致、C-7合格。異常中断・非root・他OS・NFS・本番データはUNVERIFIED。正式RELEASEDではない。GPL-3.0-only、Python 3.10+標準ライブラリ。

## 役割と範囲

第6号の整理係は**提案**。第11号は作成時`disposable`と明示されたファイルを**合成サンドボックスのゴミ箱へ移し、明示的に戻す**実行工程のサンプル。実環境への使用権限を与えるものではない。設計の基準は作成者の宣言した2区分とファイル自身のmtimeだけ。保存場所が正本か否かを自動判定しない。

## 入力

- `--root`: 存在する実ディレクトリ（symlink親経路拒否）。実操作ができるのは、OS一時ディレクトリ配下の**空領域に`demo-init`で作った合成マーカーを持つルートだけ**。ルートのコピーやマーカー偽装を防ぐ署名はない。
- `.retention_records.json`: 公開Organizerと共通の`{"version":1,"entries":[{"path":"old-disposable.txt","class":"disposable"}]}`。`class`は`disposable | permanent`。登録時刻は持たない。未知・不正・欠落はhold（記録JSON全体の破損はerror）。この初版の**移動対象は安全な単一ファイル名だけ**。深いサブディレクトリはhold。
- `--age-days`: 整数0〜365000、既定14、24時間単位、mtimeが14日ちょうどでcandidate。UTCのoffset付き`--as-of`は合成試験用。
- `--apply`: stage・restoreを有効にする明示フラグ。なしでは変更しない。

## 状態と手順

| 操作 | 条件 | 実行 | 戻し方 |
| --- | --- | --- | --- |
| `demo-init` | OS一時領域内・既存で空のルート | マーカー・架空ファイル・登録JSONを作成 | デモ用一時ディレクトリの後片付けはユーザーが別に管理 |
| `preview` | 登録JSONが有効 | 候補/未到来/永続/保留の分類のみ | 変更なし |
| `stage` | マーカー・正しい登録・候補・未完了manifestなし | `--apply`があるとゴミ箱へ`os.replace`、manifest・監査を保存 | 個別`restore --apply`（元パス空、SHA一致） |
| `restore` | staged manifest・バイトが合致・元パス空 | `--apply`で元へ移動、manifestの段階をrestoredへ変更 | 衝突時停止、上書き禁止 |
| `purge` | **未実装** | 物理削除0件 | 不可逆操作は行わない |

- ゴミ箱は`.trash/<YYYYMMDDTHHMMSSZ-32桁乱数>/payload`。各エントリに`manifest.json`（ID、デモID、元の単一ファイル名、SHA-256、バイト数、mtime_ns、stage時刻、phase）を残し、`.trash/events.jsonl`に`staged`と`restored`を記録する。SHA-256は同一バイト判定のみで、内容の正当性・悪意ある改変の真正性は証明しない。
- 移動済みの元ファイルは登録JSONには残るため、**復元されるまでは次回のstageで欠落holdとなり、新しい移動は停止する**。この公開版は連続的な自動運用に対応していない。
- manifestはまず`prepared`で記録し、ファイル移動・バイト照合後`staged`に変える。preparedが残ったら次回はFail Closed、**自動修復しない**。稼働ログの書込失敗など、stage途中失敗後の完全整合性は保証しない。
- `stage`/`restore`のapply時にロックファイル`.retention_demo.lock`を利用し、同一ホスト上の協調実行を排他。NFSや非協調プロセスに対して保証しない。ルート内参照のrace/TOCTOU対策は検証済みの完全防御ではない。
- 永久ファイル、未知タグ、欠落・リンク・ハードリンク・フォルダ・ルート外パス、将来mtimeは移動しない。**holdが一つでもあればstageを一切実行しない。** 未登録ファイルは走査しない。
- 既存の内部プログラムのpurge（運用上約1か月）とは別。公開版では保持日数で削除する機能、タグ反転、スケジュール、他の私的ファイルへアクセスする機能は**NONE**。

## 終了コード

- `0`：成功、または正常な候補0件。`--apply`なしstage/restoreも変更なし。
- `2`：判定でholdがあるためstageを停止した`partial`。**argparse構文不正のexit 2と区別する**。
- `1`：JSON・manifest・マーカー・ファイル・ロックなどのerror。先行操作の一部変更が発生した可能性を否定しない。デモ状態を手動点検する。

## 制限

内部版が本番で削除済みという報告は公開版の保証ではない。**復元の定期検証は内部でもUNVERIFIED**。この対象限定のVERIFIEDが実証したのは合成POSIX領域の限定的復元であり、停電、プロセス中断、ファイル変更競合、他OS、実運用データの保存は未検証。利用者の実作業フォルダに対する移動／削除実行は公開初版の認可範囲外。結果の例やパスを公開Issueへ貼らない。

[P1裁定](../plans/retention-manager-p1.md) / [HowTo](../howto/retention-manager.md) / [説明](../explain/retention-manager.md) / [ローカル試験](../verification/retention-manager-local-2026-11-17.md)

[独立検証概要](../verification/retention-manager-independent-2026-11-17.md)。
