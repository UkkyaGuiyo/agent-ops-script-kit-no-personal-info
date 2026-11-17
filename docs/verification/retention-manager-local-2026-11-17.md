# 第11号 保持管理係：制作側ローカル検証（EVP/1 20261117-047）

**Date:** 2026-11-17 JST。**Status:** PILOT。全資料は合成サンドボックス由来で実ファイルを用いていない。GPL-3.0-only。

## 由来と環境

- 制作: E.L.I.S.（公開用の独立実装。非公開内部ソースの複写ではない）。
- Linux container / root / Python 3.13.5。
- `python -m py_compile scripts/retention_manager.py tests/test_retention_manager.py`: PASS。
- `python -m unittest discover -s tests -v`：**79定義・78 PASS・1 SKIP・0 FAIL**（本係単独の制作ディレクトリ）。SKIPは第6号実`organizer.py`との候補判定統合テスト。新規cloneでは配置がそろうため実行必須。
- 先行キットはV.E.S.T.A.R.D.報告の539/539 PASS。79件追加で全キット**618件が期待数**。独立新規cloneでの618/618 PASSは**UNVERIFIED**。C-7もPENDING。

## CLI合成アンカー

一時空ルートを`demo-init`したのち、すべて`--age-days=14`を使用した。`--as-of`なし、実行時の現在UTCを基準にする。

| 項目 | 期待値 | 実測 | 判定 |
| --- | ---: | ---: | --- |
| 合成ファイル作成 | 4件 | **4件** | PASS |
| 登録済みタグ | 3件 | **3件** | PASS |
| preview | candidate1、not_due1、excluded1、hold0 | **同左** | PASS |
| stage without apply | 変更0件 | **0件** | PASS |
| stage --apply | ゴミ箱へ1件 | **1件** | PASS |
| stage物理削除 | 0件 | **0件** | PASS |
| restore --apply | 1件戻す | **1件** | PASS |
| 監査イベント | staged1＋restored1 | **2行** | PASS |
| restore後preview | candidate1、not_due1、excluded1、hold0 | **同左** | PASS |
| purgeコマンド | 不存在 | **CLI拒否** | PASS |

## 実装試験の保護項目

- 期限ぴったり（整数ナノ秒）でcandidate、1ns手前はnot_due、永続タグはexcluded。
- 未登録・恒久・新しい使い捨てファイルは移動しない。未知タグ、欠落記録、絶対パス、親参照、サブフォルダ、symlink、hardlink、非正規ファイルは保留。
- ドライランは元ファイルのバイトハッシュとmtimeを変更しない。ゴミ箱も作らない。
- 中断途中のprepared manifest、欠落や変造されたmanifest、内容が書き換えられたpayload、復元先の衝突ではFail Closed。
- `--apply`の有無は操作結果に反映される。stage/restoreの同一ホスト非競合ロックを実装。ロックsymlinkとロック競合を拒否。
- byte-for-byte復元を合成ファイルのSHA-256で検証。復元後のmtime_ns、登録JSONも同一。
- 一時デモルート以外のinitは拒否。**本番OS・非root・NFS・実ディレクトリ・電源断・途中停止からの自動復旧は試験していない**。

## 留保と独立試験要求

**この実装は、合成デモでの復旧可能なゴミ箱移動を示すだけ**。事前・事後hashの一致はバイトの一致を示し、正本の意味的正しさを保証しない。ステージ開始後の停電などでmanifestと移動の間に止まると、次回操作は自動的に継続せず保留になる。競合する外部の非協調プロセスを完全排除できない。公開版にはpurge、実ファイルへのapply、スケジューラを搭載しない。

V.E.S.T.A.R.D.は、対象コミットを新規cloneして全**618期待テスト**をSKIPなしで実行し、第6号の実コードとの互換性を確認する。CLIはpreview 1/1/1/0、stage1、restore1、原本sha/mtime不変、物理削除0件を検査する。C-7で第6号との区別、タグ作成時点の承認、実データ未対応、復元の限定保証、永久ファイルの保護を説明できるか判定する。実環境の削除可否判定は対象外。
