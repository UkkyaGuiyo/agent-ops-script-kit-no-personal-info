# P4-PRIV-01｜内部AI呼称の伏せ案（本人承認待ち）

**2026-11-17 JST／STATUS: PROPOSAL ONLY。** 対象GitHubコミット：`641fd1004527cff051765be0b2397efab2a90c54`（確認時点で26コミット・mainのみ）。EVP/1 `20261117-063`：本人は内部AI呼称を公開可能な別名として認めず、伏せる案の検討を指示したと報告された。ただし**置換・SPDX変更・履歴強制書換え・新リポジトリ公開の承認はまだ無い**。この公開計画書自体には元の固有呼称を再掲載しない。

## 1. 対応表（元の2呼称は公開再掲しない）

| 非公開対応キー | 使い分け | 置換後の日本語／英語 | 必ず残す証拠の意味 |
| --- | --- | --- | --- |
| **A（設計側）** | 実装・設計・P1裁定 | **設計・制作担当AI**／裁定・監査には**公開版設計・監査担当AI**（Public design/audit AI） | 自分が実施した公開コード照合と、他者の試験報告を区別する |
| **B（検証側）** | 内部仕様の一般化報告 | **内部仕様報告担当AI**（Private specification reporting AI） | 非公開コードを設計側が直接確認したという主張にしない |
| **B（検証側）** | 新規clone試験・C-7説明報告 | **別環境検証担当AI**（Fresh-clone test-reporting AI） | 試験値は検証担当からの報告。設計側が試験を直接実行したという意味ではない |
| **B由来の略称・報告ラベル** | 短縮英字・日本語呼称・ファクトタグ | **検証担当**／**[TESTER-REPORTED]** | 報告由来の主張を検証済みの直接観測へ格上げしない |
| **OWNER** | 仕様・公開・P5の承認 | **本人（公開承認者）** | AI担当の裁定と本人の承認を混同しない |

**非公開のA/B元文字列との対応表は本人・仲介AIへの非公開の回答にのみ置く。** 公開版では役割名を使う。役割に応じた文法調整が必要なので、機械的な全置換のみで完了とはしない。

## 2. HEADの直接計数・変更予定範囲

対象HEADの公開Markdownを直接照合した結果、正式英字呼称は**37ファイル・109回（A＝43回、B＝66回）**。仲介AIの「約77回」は概数であり、修正前の確定値には使わない。派生表記として**短縮英字4回（既存2ファイル内）＋日本語略称2回（別の追加2ファイル）**を確認。**計39ファイル・115回**を初期差分レビュー対象とする。ファイル数は重複排除済み。追加の未検出別表記が存在しないとは断定しない。

| 領域 | 正式呼称のファイル | 正式呼称の回数 | 派生表記 |
| --- | ---: | ---: | --- |
| ルート文書 | 4 | 28 | 0 |
| `docs/audits/` | 2 | 13 | 0 |
| `docs/operators/` | 5 | 5 | 日本語略称2回・追加2ファイル |
| `docs/plans/` | 10 | 20 | 短縮英字4回・同じ2ファイル内 |
| `docs/verification/` | 16 | 43 | 0 |
| **合計** | **37** | **109** | **派生6回、計39ファイル115回** |

**ルート4：** `AI_EXPLANATION_GUIDE.md`, `AI_SETUP_GUIDE.md`, `README.md`, `SPEC_P0.md`。

**監査2：** `docs/audits/p4-audit-round1-2026-11-17.md`, `docs/audits/p4-remediation-checklist-2026-11-17.md`。

**係の仕様5：** `docs/operators/deadline-reminder.md`, `docs/operators/gmail-collector.md`, `docs/operators/history-cleaner.md`, `docs/operators/notion-jobs-collector.md`, `docs/operators/retention-manager.md`。

**P1文書10：**
- `docs/plans/deadline-reminder-p1.md`
- `docs/plans/gmail-collector-p1.md`
- `docs/plans/history-cleaner-p1.md`
- `docs/plans/injection-size-watch-p1.md`
- `docs/plans/ledger-checker-pilot.md`
- `docs/plans/notion-jobs-collector-p1.md`
- `docs/plans/organizer-p1.md`
- `docs/plans/retention-manager-p1.md`
- `docs/plans/shared-intake-p1.md`
- `docs/plans/untagged-watch-p1.md`

**検証文書16：**
- `docs/verification/capacity-watch-2026-11-17.md`
- `docs/verification/deadline-reminder-independent-2026-11-17.md`
- `docs/verification/gmail-collector-independent-2026-11-17.md`
- `docs/verification/history-cleaner-independent-2026-11-17.md`
- `docs/verification/injection-size-watch-independent-2026-11-17.md`
- `docs/verification/injection-size-watch-local-2026-11-17.md`
- `docs/verification/ledger-check-2026-11-17.md`
- `docs/verification/notion-jobs-collector-independent-2026-11-17.md`
- `docs/verification/organizer-independent-2026-11-17.md`
- `docs/verification/organizer-local-2026-11-17.md`
- `docs/verification/retention-manager-independent-2026-11-17.md`
- `docs/verification/retention-manager-local-2026-11-17.md`
- `docs/verification/shared-intake-independent-2026-11-17.md`
- `docs/verification/shared-intake-local-2026-11-17.md`
- `docs/verification/untagged-watch-independent-2026-11-17.md`
- `docs/verification/untagged-watch-local-2026-11-17.md`

**派生の追加対象：** `docs/plans/organizer-p1.md` と `docs/plans/retention-manager-p1.md`（既存37に含まれる・短縮英字計4回）。`docs/operators/capacity-watch.md` と `docs/operators/injection-size-watch.md`（37に含まれない・日本語略称各1回）。`scripts/` と `tests/` は仲介AI報告で正式呼称0件だが、実施前に全追跡ファイルで再走査する。

## 3. 履歴の選択肢と帰結

| 方式 | 操作案 | 残留範囲 | 代償／評価 |
| --- | --- | --- | --- |
| **(a) HEADだけ通常コミットで修正** | 承認後に39ファイルを役割名へ修正。LIC-01のSPDX表示不足12ファイルも**同じ通常コミットへ束ねられる** | **旧26コミットの公開履歴に元の呼称が残る**。既存の旧SHAや検証引用は維持 | 変更と再試験が最も簡単。ただし**旧履歴での残存を例外として本人が明示承認しない限り**公開禁止の趣旨を完全には満たさない |
| **(b) Git履歴の書換え** | 書換え対象commit/ref、旧→新SHA対応、全差分、バックアップ、保護設定と復旧案を別途設計し、**別の明示承認**があって初めて実行 | mainを清浄化しても**旧clone・fork・キャッシュ・旧Gitオブジェクトの完全な消失は保証できない** | 書換え位置以降のSHAは全て変化。根からやり直すなら当時の26コミット全件が変化。引用リンク・署名・履歴の証拠・旧SHAアンカーの再固定と追加P3/P4再審査が必要。**実施しない** |
| **(c) 新しい公開リポジトリへ清浄スナップショット** | 承認された役割名だけを含む新しい初期スナップショットを別リポジトリに作る。旧リポジトリの扱いは追加判断 | **旧リポジトリが公開のままなら既存履歴も公開のまま**。旧リポジトリの非公開化・削除も過去コピーの消去保証はない | 移行URLや検証証拠の再構築が必要。旧リポジトリの削除・非公開化・公開先変更は別途本人承認が必要 |

**推奨：** 先に本人が(a)/(b)/(c)と「旧履歴残存を許容するか」を決める。どの案でも実操作の承認は別。履歴書換えの暗黙承認、force-push、旧リポジトリ削除、タグ作成は認めない。GitHub公開者の**アカウントハンドル・noreply著者メール・コミット著者メタデータは今回の伏せ範囲外**として明示する。出版社識別子の完全匿名化を主張しない。

## 4. 検証主体の実在性・証拠連続性

公開版では**AUTHOR-REVIEWER（設計／公開コード確認）**、**FRESH-CLONE-TESTER（別環境試験を実施したと報告する主体）**、**OWNER（公開承認）**を別役割として記す。旧P3記録には報告ID、原対象SHA、テスト件数、SKIP数、CLIアンカー、Linux/root等の環境、C-7範囲、公開担当がログ原文を未確認という制約を残す。独立した実行環境から報告が届いた事実と、検証者の本人性が暗号学的に立証されたことは別。**役割名の置換だけでは、別個の検証者が実在したことを新たに証明できない**。

原本の保存主体が、非公開の検証記録・C-7全文の**サイズ（バイト）・SHA-256・作成日時・EVP報告ID・元の対象SHA**を私的な監査台帳へ記録し、必要に応じて読み戻す。公開へ実ログ・固有名・個人情報を持ち出さない。署名・原本SHA-256・実行証跡の真正性が未検証なら**UNVERIFIED**と明記する。

歴史を書き換える場合、**旧SHA→新SHA対応表は私的管理**。旧コミットで報告された618/618件は新SHAの実測と見なさず、清浄な新規cloneで全618件・SKIPなしの再実行、C-7再説明、現行資料と旧資料の引用関係の再検証を行う。旧報告のSHAを機械的に新SHAにすげ替え、「その新コミットで当時試験した」とは記述しない。対象ごとの再検証日・環境・計測値を新たに記録する。

## 5. 実施分担と再検証（本人による採用・操作承認の後だけ）

1. **設計・制作担当AI：** 承認範囲で39ファイルの役割語置換、文ごとの主語・動詞・報告由来のレビュー、LIC-01の12ヘッダー変更。コード動作変更なし。採用方式(a)なら伏せとSPDXを**1件の内容修正コミット**にまとめ、独立再試験を1巡で済ませられる。方式(b)なら最終SHA確定後に再試験する。
2. **別環境検証担当AI：** 新規cloneで全追跡ファイルの名称・短縮・日本語表記スキャン、39ファイルの差分と文意の一致、Python全618試験・SKIP0、compileall、必要なC-7再確認。既存コミットをそのままPASSにしない。
3. **公開版監査担当AI：** GitHub読み戻し、現行ツリー・履歴の再走査、対象例外の確認、P4裁定。名前の残存を本人が許容しないなら(a)だけでPRIV-01をPASSにはしない。
4. **両者：** P4合格候補を凍結後、全追跡ファイルのサイズ・SHA-256マニフェストを作成、別環境で全件とアンカーを照合。SHA-256はバイト同一性の証拠であり内容の正しさは証明しない。
5. **本人：** 公開方針、権利帰属、履歴処置とP5正式リリースはそれぞれ別の承認事項。

## 6. HUMAN REVIEW CARD（案の判断。実施承認ではない）

- **目的：** 内部AI呼称の公開禁止と検証記録の証拠保存を両立する。
- **変更：** 正式名37ファイル109回。派生を含む39ファイル115回。LIC-01別途12ファイルを同時修正できるか方式に従い決める。
- **重要数値：** 基準26コミット、全11系統P3限定VERIFIED、618/618件PASSは以前の独立報告。修正後は再試験。
- **未解決事項：** 旧履歴・既存cloneの残存、旧→新SHAアンカー、非公開試験原本の証拠、著作権。GitHub公開者メタデータは伏せの対象外。
- **判断要求：** **(a)現行だけ・旧履歴残存を例外許容／(b)明示承認後に履歴再生成／(c)新公開先への移行**のどれを検討・採用するか。作業実施は別途承認。

**VERDICT:** NOT_ASSESSABLE for execution authorization（設計案だけ）。**BASIS:** EVP/1 `20261117-063`、GitHub HEAD `641fd100`。**SCOPE:** 伏せ案の作成。**OUT_OF_SCOPE:** 実置換、SPDX編集、履歴変更、公開先変更、P5。**UNRESOLVED:** 案の承認・履歴残存・権利確認。**RESPONSE_STATUS:** COMPLETE（計画書だけ）。**P4: REVISE、P5: BLOCKEDを維持。**
