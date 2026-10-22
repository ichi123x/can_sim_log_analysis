# Implementation Plan: CANログ解析コアとコマンドライン

**Branch**: `001-log-analysis-core-cli` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-log-analysis-core-cli/spec.md`

## Summary

MFC 版 `reference/mfc/CanSim/LogAnalysis.cpp` の 4 つの解析（受信完了時間、送信待ち時間、送信ジッタ、CAN バス負荷）と
ログの読み込みを、GUI に依存しない Python パッケージ `can_log_analysis` に 1 関数ずつ移植し、
`AnalysisDlg.cpp` と同じ書式で表 CSV を出すコマンド `can-log-analysis` を作る。

MFC 版と文字列一致することの正解は、`reference/mfc` を書き換えずにそのままビルドする C++ の正解生成プログラム
（`tools/mfc_golden/`）で作る。差し替え用の空の `pch.h` で MFC なしにビルドできることは確認済み（research R-1）。
浮動小数点の計算順と丸めを C++ と同じにする方針は research R-4。

## Technical Context

**Language/Version**: Python 3.11 以上（開発は 3.12）。正解生成プログラムは C++17（MSVC、Visual Studio 2022 以降）

**Primary Dependencies**: 実行時は標準ライブラリのみ（`array`、`configparser`、`argparse`、`math`、`re`）。開発時は pytest

**Storage**: ファイルのみ（入力 .canprj と .log.csv、出力 表 CSV）

**Testing**: pytest（unit / integration / perf）。golden テストは正解 CSV とのバイト一致

**Target Platform**: Windows 11（主）。コアとコマンドラインは OS に依存しない書き方にする

**Project Type**: ライブラリ＋コマンドライン（デスクトップアプリの解析コア。画面は次の機能）

**Performance Goals**: 300 万行（約 300 MB）のログで 4 解析すべてを 1 分以内（SC-003）。見積もり 10〜30 秒（research R-3）

**Constraints**: 表のセルが MFC 版と文字列一致（憲章 原則 I）。300 万行でメモリ 1 GB 未満（ログは列ごとの整数配列で約 190 MB、
解析の途中の値も `array('q')`。research R-3）。進捗は標準エラーだけに出し、表 CSV に混ぜない（FR-043）。
`reference/mfc` は変更しない。

**Scale/Scope**: 解析 4 種、表 4 種。ノード数・ID 数は決め打ちしない（11 ビット ID、ECU は 2 桁表示）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 判定 | 根拠 |
|---|---|---|
| I. MFC 版との数値互換 | ✅ | 関数を 1 対 1 で移植（data-model の対応表）。正解は MFC のコードそのものから生成（contracts/mfc-golden.md）。浮動小数点の順序・丸めを research R-4 で固定。MFC にない指標は作らない |
| II. 解析コアと画面の分離 | ✅ | `can_log_analysis` は標準ライブラリのみ。セル書式の関数をコアに置き CLI・画面・テストで共有（contracts/core-api.md）。GUI を import しないことをテストで確認 |
| III. テストファースト | ✅ | 既知解（AS-001）、golden（sample_vehicle_16ecu）、Edge Cases ごとの境界テストを、実装より先に書く順で tasks を作る |
| IV. 大容量ログでも固まらない | ✅ | 解析コアは 4 MB ごとの進捗通知と中止（FR-007）。コマンドラインは 0.5 秒を超えたら標準エラーに進捗を出し、Ctrl+C で中止して終了コード 130（FR-042〜FR-044、research R-12。/speckit-analyze D1 で追加）。ログと途中の値は `array('q')` に入れる（research R-3）。別スレッドと「解析中」ウィンドウは画面機能で扱う。300 万行の性能テスト（時間とメモリを別々に測る）を持つ |
| V. トレーサビリティと最小スコープ | ✅ | tasks・テスト名に FR/AR の ID を付ける。グラフの間引き・numpy・PySide6 は入れない。[要確認] は残っていない（AQ-4 は Clarifications で解決、AQ-6 は .rc の文言で解決） |
| 技術的制約 | ✅（注記あり） | Python 3.11 以上。開発 PC は 3.9.13 のみ → 実装前に 3.12 を入れる（research R-2、quickstart 前提） |
| 品質ゲート | ✅ | pytest 全成功、golden 一致＋目視確認の記録（VERIFIED.md）、GUI import なし、ID で辿れる |

**Phase 1 後の再確認**: 設計（data-model、contracts）でも違反なし。C++ の正解生成プログラムを加えるが、これは spec の
FR-040a〜e（利用者の決定）で求められたテスト用の道具で、製品のコードではない（Complexity Tracking に記録）。

## Project Structure

### Documentation (this feature)

```text
specs/001-log-analysis-core-cli/
├── plan.md              # このファイル
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── core-api.md      # 解析コアの公開 API
│   ├── cli.md           # コマンドライン
│   ├── table-csv.md     # 表 CSV の形式・文言・書式
│   └── mfc-golden.md    # 正解生成プログラム
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2（/speckit-tasks が作る）
```

### Source Code (repository root)

```text
pyproject.toml                    # パッケージ定義、console_scripts: can-log-analysis、pytest 設定（markers: perf）
src/can_log_analysis/
├── __init__.py                   # 公開 API の再エクスポート
├── __main__.py                   # python -m can_log_analysis
├── errors.py                     # CanLogAnalysisError ほか（research R-8）
├── project.py                    # open_project / Project
├── log_reader.py                 # read_log_records / LogRecords（MFC ReadLogRecords）
├── stats.py                      # compute_stats / make_histogram / nice_ceil（MFC ComputeStats, MakeHistogram, NiceCeil）
├── analysis.py                   # collect_transmissions / analyze_latency / analyze_tx_wait / analyze_jitter / analyze_bus_load
├── formatting.py                 # ecu_name / can_id_text / fixed1 / period_text、.rc の文言
├── tables.py                     # Table、*_table、write_table_csv
└── cli.py                        # argparse、終了コード

tools/mfc_golden/                 # 正解生成プログラム（contracts/mfc-golden.md）
├── README.md
├── pch.h
├── golden_main.cpp
└── build.ps1

tests/
├── conftest.py                   # 小さなログを一時フォルダに書くヘルパ
├── data/
│   ├── as001/                    # AS-001 の 3 行ログ＋.canprj＋期待 CSV
│   ├── errors/                   # 不正ログ（列なし、bad number など）
│   └── sample_vehicle_16ecu/     # 既存のサンプル
│       └── golden/               # 正解 CSV 4 本＋VERIFIED.md
├── unit/
│   ├── test_log_reader.py
│   ├── test_stats.py
│   ├── test_latency.py
│   ├── test_tx_wait.py
│   ├── test_jitter.py
│   ├── test_bus_load.py
│   ├── test_formatting.py
│   ├── test_tables.py
│   └── test_no_gui_import.py
├── integration/
│   ├── test_cli.py
│   ├── test_cli_progress.py      # 進捗・--quiet・Ctrl+C（FR-042〜FR-044）
│   └── test_golden.py
└── perf/
    ├── test_large_log.py         # -m perf のときだけ。時間とメモリは別のテスト・別のプロセスで測る
    └── memory_probe.py           # メモリ計測用に別プロセスで動かす小さなスクリプト
```

**Structure Decision**: 単一プロジェクトの src レイアウト。パッケージ名は `can_log_analysis`。
仮のテンプレート `PythonApplication1/`（空の .py と VS のプロジェクトファイル）は、CLAUDE.md と憲章の後続 TODO のとおり
この機能で削除する。解析は MFC のファイル分け（LogAnalysis.cpp 1 本）より細かく、読み込み・統計・解析・書式で分けるが、
関数は MFC と 1 対 1 に対応させる。

## 実装の順序（tasks の骨格）

1. 準備: Python 3.12、pyproject、パッケージの空の骨格、`PythonApplication1/` の削除。
2. 正解生成: `tools/mfc_golden` を作り、sample_vehicle_16ecu と AS-001 の正解 CSV を生成してコミット。
   ここでI.Hに目視確認を依頼する（実装と並行してよい）。
3. US1（P1）: テスト → `log_reader` → `stats` → `collect_transmissions` → latency / tx_wait → `formatting` / `tables` → CLI。
   この時点で AS-001 と golden の latency・txwait が通る。
4. US2: jitter。5. US3: bus load。6. US4: エラー系。7. US5: ヒストグラム・進捗・中止。
8. 仕上げ: 性能テスト、GUI 非依存テスト、quickstart の手順を通す。

## 正解生成プログラムのビルドと出力の取り決め

1. **ビルドは PowerShell（または cmd）から実行する。**
   - `tools/mfc_golden/build.ps1` を PowerShell で実行する。Bash（Git Bash）から `.cmd`／`.bat` を直接実行しない
     （Git Bash からはバッチファイルが正しく起動できないことを research R-1 の試行で確認した）。
   - `vswhere.exe` は PATH にないので、`"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"` を
     フルパスで呼んで Visual Studio を探す（`-latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`）。
   - 見つかったインストール先の `VC\Auxiliary\Build\vcvars64.bat` を `cmd /c` の中で呼び、同じ `cmd /c` の中で `cl` を実行する
     （vcvars の環境変数は PowerShell 側に残らないため）。
2. **CSV の文字コードと改行をそろえ、文字列として比較できるようにする。**
   - 正解生成プログラムは UTF-8（BOM なし）、改行 LF で書く。Windows の C/C++ はテキストモードだと `\n` を `\r\n` に
     変えるので、ファイルはバイナリモード（`fopen(path, "wb")` または `std::ios::binary`）で開く。文字列リテラルは `/utf-8` でコンパイルして UTF-8 のまま書く。
   - Python 側は `open(path, "w", encoding="utf-8", newline="\n")` で書き、標準出力も UTF-8・LF にする
     （`sys.stdout.reconfigure(encoding="utf-8", newline="\n")`）。
   - golden テストは両方のファイルを UTF-8 の文字列として読み、そのまま `==` で比べる（改行の正規化や空白の除去はしない）。
     形式の詳細は [contracts/table-csv.md](contracts/table-csv.md)。

## 未解決・注意点

- **.gitignore**: 共通の .gitignore には Python の生成物（`__pycache__/`、`.venv/`、`*.egg-info/`、`.pytest_cache/`）がない。
  CLAUDE.md により .gitignore は種別に依存しない内容を保つ設計なので、本機能では変更しない。
  ベース作成ツール側に追加するか、別の方法にするかはプロジェクトオーナーが決める（tasks に確認タスクを置く）。
  - **決定（2026-10-22、プロジェクトオーナー、T006）**: このリポジトリの `.gitignore` の末尾に「# ---- Python ----」の節を足し、
    `.venv/`、`__pycache__/`、`*.egg-info/`、`.pytest_cache/` を除外してよい。追加済み。
- **目視確認（FR-040e）**: 人の作業。golden テストが通っても、VERIFIED.md がそろうまで SC-002 は完了としない。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| C++ の正解生成プログラム（2 つ目の言語） | FR-040a〜e（利用者の決定）。MFC のコードそのものから正解を作り、原則 I を機械的に検証するため | 画面から書き写す → 手間と写し間違い。Python の出力を固定 → MFC との一致の証明にならない |
