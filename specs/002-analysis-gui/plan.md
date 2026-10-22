# Implementation Plan: CANログ解析ツールの画面

**Branch**: `002-analysis-gui` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-analysis-gui/spec.md`

## Summary

機能 001 の解析コア `can_log_analysis` の上に、PySide6 のデスクトップアプリ `can_log_analysis_gui` を作る。
メインウィンドウ（MFC と同じ「ファイル」「解析」メニュー＋プロジェクトの情報と .canprj の内容の表）、4 つの解析画面（表・注記・グラフ）、
「解析中」ウィンドウ（0.5 秒後に出る進捗と中断）を、MFC 版の `AnalysisDlg.cpp`・`RunAnalysis` と同じ配置・振る舞い・文言で作る。

表の文字列は機能 001 の Table をそのまま表示する。グラフは matplotlib ではなく Qt の描画で MFC の `CAnalysisGraph::Draw` と同じ手順で描き、
目盛り・間引きの計算は Qt に依存しない関数として解析コアの `plot.py` に置く（research R-2）。
解析は `QThread` で動かし、読み込み中は 0.2 秒以内に中断が効く（実測。research R-3）。

## Technical Context

**Language/Version**: Python 3.11 以上（開発は 3.12.10）

**Primary Dependencies**: PySide6 6.8 以上（`[gui]` と `[dev]` の optional-dependencies）。解析コアは標準ライブラリのみのまま。開発時は pytest、pytest-qt 4.5

**Storage**: ファイルのみ（.canprj、.log.csv を読む。書き込みはしない）

**Testing**: pytest＋pytest-qt（`QT_QPA_PLATFORM=offscreen`）。グラフは描画計画（範囲・目盛り・図形の座標）を検証。300 万行の応答性・中断は `-m perf`

**Target Platform**: Windows 11（主）、画面の DPI 100〜200%

**Project Type**: デスクトップアプリ（GUI）。機能 001 のライブラリ＋CLI と同じリポジトリ

**Performance Goals**: 300 万行で解析画面が開くまで 1 分以内（読み込み 7.1 秒＋計算 最長 2.9 秒の実測）、行の選択からグラフ更新まで 0.5 秒以内、解析中も GUI が 0.5 秒以内に応答

**Constraints**: 表のセルは機能 001 の CLI 出力と完全一致。解析コアは Qt を import しない。MFC にない画面・指標は足さない（FR-004 の .canprj 表示は Q1 = B の決定）

**Scale/Scope**: ウィンドウ 6 種（メイン、解析 4、解析中）、メッセージ 4 種、グラフ 4 種

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 判定 | 根拠 |
|---|---|---|
| I. MFC版との数値互換 | ✅ | 表は機能 001 の Table（golden 一致済み）をそのまま表示。メニュー・文言・配置・目盛り・間引きは MFC のソース／リソースに合わせ、テストで .rc と照合（research R-8）。元仕様 AR-090 と MFC のメニュー順の食い違いは MFC に従う |
| II. 解析コアと画面の分離 | ✅ | 画面は別パッケージ `can_log_analysis_gui`。コアへの追加（`plot.py`、`read_project_contents`、`make_histogram` の高速化）は Qt 非依存で、test_no_gui_import の対象 |
| III. テストファースト | ✅ | pytest-qt で画面ごとの受け入れシナリオを先に書く。golden CSV との一致、`plot.py` の単体テスト、描画計画のテスト |
| IV. 大容量ログでも固まらない | ✅ | `QThread`＋0.5 秒後の「解析中」ウィンドウ（進捗バー、中断）。読み込み中の中断 0.2 秒以内、計算中は MFC と同じく計算終了後（最長約 3 秒。spec SC-003 を実測に合わせて修正）。グラフは列単位の間引き |
| V. トレーサビリティと最小スコープ | ✅ | FR／AR／MFC の関数名で辿れる。ログ表示・シミュレーション・保存・印刷・単体 exe は範囲外。.canprj の表示は表示のみ |
| 技術的制約 | ✅（注記） | PySide6 を使う。憲章が挙げる matplotlib は使わない（依存を減らす方向。理由は research R-2） |
| 品質ゲート | ✅ | pytest 全成功（001 の golden を含む）、MFC 版との目視確認 2 画面の記録（VERIFIED.md）、コアの GUI 非 import、ID で辿れる |

**Phase 1 後の再確認**: data-model・contracts でも違反なし。解析コアへの追加は 3 点のみで、機能 001 の契約（core-api.md）を壊さない。

## Project Structure

### Documentation (this feature)

```text
specs/002-analysis-gui/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── gui.md              # ウィンドウ・メニュー・配置・グラフ・振る舞い
│   └── core-additions.md   # 解析コアへの追加
├── checklists/requirements.md
└── tasks.md                # /speckit-tasks が作る
```

### Source Code (repository root)

```text
pyproject.toml                      # [gui] = PySide6、dev に pytest-qt、gui-scripts: can-log-analysis-gui
can_log_analysis_gui.bat            # ダブルクリック／ドラッグ＆ドロップ用（research R-6）
src/can_log_analysis/               # 機能 001 の解析コア（Qt 非依存）
├── plot.py                         # 追加: nice_ticks、ticks_from_zero、ticks_covering、format_tick、min_max_per_column、max_per_column
├── project.py                      # 追加: read_project_contents、ProjectContents、EcuInfo、FrameInfo
└── stats.py                        # 変更: make_histogram を bisect で（結果は不変）
src/can_log_analysis_gui/           # 新規: 画面
├── __init__.py
├── __main__.py                     # python -m can_log_analysis_gui [PROJECT]
├── app.py                          # main()、QApplication、起動引数、差し替え可能なダイアログ関数
├── texts.py                        # .rc の文言（メニュー、メッセージ、軸名、解析中）
├── main_window.py                  # メインウィンドウ、メニュー、プロジェクト表示、解析画面の管理
├── project_view.py                 # プロジェクト情報・ネットワーク・ECU・送信フレームの表示
├── job.py                          # AnalysisJob（QThread の作業、状態、進捗、中断）
├── progress_dialog.py              # 「解析中」ウィンドウ
├── analysis_window.py              # 解析画面の共通部分と 4 種類（配置、表、行の選択、グラフの切り替え）
└── graph.py                        # グラフのウィジェット（描画計画＋QPainter）

tests/
├── unit/
│   ├── test_plot.py                # 追加（コア）
│   ├── test_project_contents.py    # 追加（コア）
│   └── test_no_gui_import.py       # 既存（コアの Qt 非依存）
└── gui/                            # 新規（pytest-qt）
    ├── conftest.py                 # offscreen、ダイアログの差し替え、golden の読み込み
    ├── test_texts.py               # .rc との一致
    ├── test_main_window.py         # メニュー、プロジェクトの読み込みと表示、起動引数
    ├── test_analysis_windows.py    # 4 画面の表（golden 一致）、配置、行選択、Esc／Enter、再選択
    ├── test_graph_plan.py          # 描画計画（範囲・目盛り・間引き）
    ├── test_job.py                 # 解析中ウィンドウ、中断、エラー
    └── test_gui_perf.py            # -m perf: 300 万行の応答性・中断・開くまでの時間
```

**Structure Decision**: 画面は解析コアと別のトップレベルパッケージにし、依存は画面 → コアの一方向（憲章 原則 II）。
画面のファイル分けは MFC の AnalysisDlg.cpp（グラフ、解析画面の基底と 4 種、解析中ウィンドウ）と MFCApplication1Dlg.cpp（メニュー、RunAnalysis）に対応させる。

## 実装の順序（tasks の骨格）

1. 準備: pyproject（PySide6、pytest-qt、gui-scripts）、パッケージの骨格、`tests/gui/conftest.py`、`texts.py`（.rc との照合テスト）。
2. 土台: コアの `plot.py`（MFC と同じ計算の単体テスト）、`read_project_contents`、`make_histogram` の高速化、グラフのウィジェット（描画計画）、ジョブ（QThread）。
3. US1: メインウィンドウ（メニュー、プロジェクト読込み、.canprj の表示、起動引数）＋送信待ち時間の画面（表・注記・ヒストグラム、行選択、再選択、Esc／Enter）。MVP。
4. US2: 受信完了時間・送信ジッター（時系列グラフと間引き）。
5. US3: CAN バス負荷（要約・折れ線・平均・ECU 表、別配置）。
6. US4: 「解析中」ウィンドウと中断、応答性（perf）。
7. US5: メッセージ（未選択、ログなし、読めない、プロジェクトが読めない）。
8. 仕上げ: バッチ、CLAUDE.md・quickstart、MFC 版との目視確認 2 画面（VERIFIED.md、I.H）。

## 未解決・注意点

- **目視確認（SC-002）**: 人の作業。MFC 版（`C:\work\claude\can_simulator`）と 2 画面以上を見比べて `specs/002-analysis-gui/VERIFIED.md` に記録するまで完了としない。
- **計算中の中断**: MFC と同じく計算が終わるまで待つ（最長約 3 秒）。spec SC-003 はこれに合わせて修正済み。
- **元仕様 AR-090 のメニュー順**: MFC と違う。spec Assumptions で MFC に従うと決め、機能 001 の CLI の出力順も MFC に合わせて修正済み（d8c951d）。元仕様の文書そのものを直すかはプロジェクトオーナーが決める。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 憲章の想定ライブラリ matplotlib を使わず、グラフを自前で描く | MFC と同じ目盛り・間引き（FR-050〜052）を確実に再現するため | matplotlib は目盛りの規則が違い、結局手で与えることになる。依存（numpy）も増える（research R-2） |
