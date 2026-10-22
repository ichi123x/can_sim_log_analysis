---

description: "CANログ解析コアとコマンドライン の実装タスク"
---

# Tasks: CANログ解析コアとコマンドライン

**Input**: `specs/001-log-analysis-core-cli/` の設計文書

**Prerequisites**: [plan.md](plan.md)、[spec.md](spec.md)、[research.md](research.md)、[data-model.md](data-model.md)、
[contracts/](contracts/)（core-api.md、cli.md、table-csv.md、mfc-golden.md）、[quickstart.md](quickstart.md)

**Tests**: 必須。憲章 原則 III（テストファースト）と spec FR-041 による。各ストーリーのテストタスクは実装より先に書き、
失敗することを確かめてから実装に進む。

**Organization**: ユーザーストーリーごとにまとめる。ストーリー番号は spec.md の User Story 1〜5。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 並行してよい（別ファイルで、未完了のタスクに依存しない）
- **[Story]**: 対応するユーザーストーリー（US1〜US5）
- パスはリポジトリのルートからの相対パス

## 全タスク共通の決まり

- MFC 版（`reference/mfc/CanSim/LogAnalysis.cpp`、`reference/mfc/AnalysisDlg.cpp`）を正解とする。仕様書と食い違えば MFC に従う。
- `reference/` 配下は読むだけで、変更もコピーもしない。
- 浮動小数点の計算順と丸めは research.md R-4 に従う（`statistics`・`math.fsum`・numpy・`round()` を使わない。表示は `%` 書式）。
- 書くファイルは UTF-8（BOM なし）・LF。Python は `open(path, "w", encoding="utf-8", newline="\n")`。
- 実行時の依存は標準ライブラリだけ。GUI ライブラリを import しない。
- テスト関数名か docstring に、対応する FR／AR／AS の ID を書く（憲章 原則 V）。
- コマンドは PowerShell から実行する。Bash から `.cmd`／`.bat` を直接実行しない。

---

## Phase 1: Setup（共通の準備）

**Purpose**: Python 環境とパッケージの骨格を作る

- [x] T001 Python 3.11 以上（3.12 推奨）が使えることを `py -3.12 --version` で確認する。なければ作業を止めて、利用者に `winget install Python.Python.3.12` などで入れてもらうよう依頼する（research.md R-2）。確認できたら `py -3.12 -m venv .venv` でリポジトリ直下に `.venv` を作る
- [X] T002 仮のテンプレート `PythonApplication1/`（`PythonApplication1.py`、`PythonApplication1.pyproj`、`PythonApplication1.sln`）を削除する（plan.md Structure Decision）
- [X] T003 `pyproject.toml` を作る。setuptools、src レイアウト、パッケージ名 `can_log_analysis`、`requires-python = ">=3.11"`、実行時の依存なし、`[project.optional-dependencies] dev = ["pytest"]`、`[project.scripts] can-log-analysis = "can_log_analysis.cli:main"`、`[tool.pytest.ini_options]` に `testpaths = ["tests"]`、`markers = ["perf: 300 万行の性能テスト"]`、`addopts = "-m 'not perf'"`
- [X] T004 パッケージの骨格を作る: `src/can_log_analysis/__init__.py`（空）、`src/can_log_analysis/__main__.py`（`from can_log_analysis.cli import main; raise SystemExit(main())`）、`src/can_log_analysis/cli.py`（`def main(argv=None) -> int: return 0` だけ）。`.venv\Scripts\python -m pip install -e ".[dev]"` が通り、`pytest` が「テスト 0 件」で終わることを確かめる
- [X] T005 [P] テスト用の空ディレクトリと共通ヘルパを作る: `tests/unit/`、`tests/integration/`、`tests/perf/`、`tests/conftest.py`。conftest に fixture `make_project(tmp_path)` を作る。引数はログの行（ヘッダを除く文字列のリスト）と省略可能なヘッダ（既定は `Timestamp_us,CAN_ID,DLC,Tx_Node,Rx_Node,Tx_Request,Tx_Start,Tx_End,Rx_Start,Rx_End,Rx_Process,Bus_Load_Pct,Status,Retry_Count,Update_Count`）とプロジェクト名（既定 `t.canprj`）。`tmp_path/<名前>`（`[Project]\nEcuCount=1\n` だけの INI）と `tmp_path/<名前>.log.csv` を UTF-8・LF で書き、.canprj のパスを返す
- [x] T006 [P] `.gitignore` に Python の生成物（`__pycache__/`、`.venv/`、`*.egg-info/`、`.pytest_cache/`）の除外がないことを利用者に伝え、どう扱うか（ベース作成ツール側に足す／今回は足さない、など）を確認し、答えを `specs/001-log-analysis-core-cli/plan.md` の「未解決・注意点」に書く。CLAUDE.md の方針により、利用者の指示なしに `.gitignore` は変更しない

---

## Phase 2: Foundational（全ストーリーの前提）

**Purpose**: 正解 CSV、例外、プロジェクト・ログの読み込み、送信のまとめ、表の共通部分

**⚠️ CRITICAL**: この Phase が終わるまでユーザーストーリーに入らない

### 正解生成プログラム（contracts/mfc-golden.md、spec FR-040a〜d）

- [X] T007 [P] `tools/mfc_golden/pch.h` を作る。中身は `#pragma once` とコメント（`reference/mfc/pch.h` は MFC を読み込むため、その代わりに読ませる差し替え用であること）だけ（research.md R-1）
- [X] T008 [P] `tools/mfc_golden/golden_main.cpp` を作る。`mfc_golden.exe LOG_CSV PROJECT_NAME OUT_DIR` で、`CanSim::ReadLogRecords` で読み（失敗なら標準エラーにメッセージ、終了コード 1）、`AnalyzeLatency`・`AnalyzeBusLoad`・`AnalyzeTxWait`・`AnalyzeJitter` の結果を `OUT_DIR/latency.csv`、`busload.csv`、`txwait.csv`、`jitter.csv` に書く。形式・文言・セルの作り方は `specs/001-log-analysis-core-cli/contracts/table-csv.md` のとおり。セルは `reference/mfc/AnalysisDlg.cpp` と同じ書式文字列（`ECU %02d`、`0x%03X`、`%lld`、`%.1f`、周期は `PeriodUs % 1000 == 0` なら `%lld` で `PeriodUs / 1000`、それ以外は `%.3f` で `PeriodUs / 1000.0`）を `snprintf` で使い、空欄の条件（全体の行の 2 列目、jitter の count 0 の行）も `CreateContent` と同じにする。表題・注記・列見出しは `reference/mfc/MFCApplication1.rc` の IDS_LAT_*、IDS_BUS_*、IDS_WAIT_*、IDS_JIT_* の文字列を UTF-8 の文字列リテラルとしてコピーする（`%%` は `%` に）。ファイルは `fopen(path, "wb")` のバイナリモードで開き、UTF-8（BOM なし）・LF で書く。セルに `,` `"` CR LF が含まれたらエラーで終わる
- [X] T009 [P] `tools/mfc_golden/build.ps1` を作る。`"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"` をフルパスで呼び（`-latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`）、見つからなければエラーで止まる。`<installationPath>\VC\Auxiliary\Build\vcvars64.bat` と `cl` を 1 回の `cmd /c` の中で続けて実行する。`cl /nologo /std:c++17 /EHsc /O2 /utf-8 /W4 /I tools\mfc_golden /I reference\mfc\CanSim tools\mfc_golden\golden_main.cpp reference\mfc\CanSim\LogAnalysis.cpp /Fo:tools\mfc_golden\build\ /Fe:tools\mfc_golden\build\mfc_golden.exe`（`/fp:fast`・`/arch:AVX2` は付けない）。`tools\mfc_golden\build\` がなければ作る。スクリプトの場所を基準にパスを解決し、どのディレクトリから実行しても動くようにする
- [X] T010 [P] `tools/mfc_golden/README.md` を書く。目的（MFC 版のコードそのものから正解 CSV を作る）、`reference/mfc` を変更しないこと、PowerShell からのビルド手順、実行例（`specs/001-log-analysis-core-cli/quickstart.md` の 7）、正解を作り直したら `git diff` で確認すること、目視確認の手順と `VERIFIED.md` に書く項目（確認日、確認者、確認した画面、使った MFC 版のビルド、結果）
- [X] T011 AS-001 のテストデータを作る: `tests/data/as001/as001.canprj`（`[Project]\nEcuCount=5\n[Network]\nBitRateBps=500000\n`）と `tests/data/as001/as001.canprj.log.csv`（`Doc/references/CANバスシミュレータ仕様.md` FR-054 のヘッダと 3 行をそのまま、UTF-8・LF）
- [X] T012 PowerShell で `tools\mfc_golden\build.ps1` を実行してビルドし、`tools\mfc_golden\build\mfc_golden.exe` で正解 CSV を作る: `tests\data\sample_vehicle_16ecu\sample_vehicle_16ecu.canprj.log.csv` → `tests\data\sample_vehicle_16ecu\golden\`（PROJECT_NAME は `sample_vehicle_16ecu.canprj`）、`tests\data\as001\as001.canprj.log.csv` → `tests\data\as001\golden\`（PROJECT_NAME は `as001.canprj`）。as001 の `txwait.csv` と `latency.csv` が `contracts/table-csv.md` の「例」と 1 文字も違わないことを確かめる（違えば T008 を直す）。4 本ずつ、計 8 ファイルができること、どれも BOM なし・LF であることを確かめる
- [X] T013 利用者（I.H）に目視確認を依頼する（spec FR-040e）。MFC 版で `tests/data/sample_vehicle_16ecu/sample_vehicle_16ecu.canprj` を開き、解析画面を 1 つ（例: 送信待ち時間）開いて、表の全セルを `tests/data/sample_vehicle_16ecu/golden/txwait.csv` と見比べてもらう。`tests/data/sample_vehicle_16ecu/golden/VERIFIED.md` を、記入欄（確認日、確認者、確認した画面、MFC 版のビルド、結果）だけ入れて作っておく。結果を待たずに次へ進んでよいが、記入されるまで SC-002 は完了としない

### 例外・プロジェクト・ログの読み込み（contracts/core-api.md、FR-001〜FR-006）

- [X] T014 [P] `tests/unit/test_project.py` を書く（実装より先に、失敗を確認）: `open_project` が `name`（パスの最後の `\` または `/` より後ろ、拡張子付き。例 `as001.canprj`）と `log_path`（`str(path) + ".log.csv"`）を返す。存在しないパスで `ProjectNotFoundError`。UTF-8 の INI として読めないファイル（例: セクションのない `a=1` だけ、不正な UTF-8 バイト）で `ProjectReadError`。ログがなくても `open_project` は成功する
- [X] T015 [P] `tests/unit/test_log_reader.py` を書く（実装より先に、失敗を確認）。contracts/core-api.md「ログの読み込み」の規則 1〜10 をそれぞれ 1 つ以上のテストにする: 列の順が違っても同じ結果、余分な列は無視、行末の `\r` を除く、空行は飛ばすが行番号には数える（例: 3 行目が空行で 4 行目が壊れていれば `line 4: ...`）、最後の行に改行がなくても読む、空欄の既定値（Tx_Node 0、Rx_Node 0、時刻 −1）、`+12` と `-5` は読める、` 12`・`1_000`・`12a`・`1.5` は `bad number`、CAN_ID は `0x7ff`・`0X7FF` が読めて `7ff`・`0x`・`0xg1` は `bad CAN_ID`、Status 3 種と `success`（小文字）は `bad Status`、ヘッダに列がなければ `line 1: no column <名前>`（8 列のうち最初に欠けたもの）、セルが足りなければ `line N: too few columns`、空ファイルは `line 1: no header`、ヘッダしかなければ 0 件、検査の順（CAN_ID → 数値 → Status）、存在しないファイルは `LogNotFoundError`。`LogReadError.message` が MFC と同じ英文であること
- [X] T016 `src/can_log_analysis/errors.py` を実装する: `CanLogAnalysisError`（基底）、`ProjectNotFoundError`、`ProjectReadError`、`LogNotFoundError`、`LogReadError`（属性 `message`。MFC と同じ英文）、`LogReadCancelled`（research.md R-8）
- [X] T017 `src/can_log_analysis/project.py` に `Project`（`path: Path`、`name: str`、`log_path: Path`）と `open_project(path)` を実装する。`configparser.ConfigParser(interpolation=None, strict=False)` で UTF-8 として読み、失敗は `ProjectReadError`。値は検査しない（research.md R-9）。T014 を通す
- [X] T018 `src/can_log_analysis/log_reader.py` に `LogRecords` と `read_log_records(path, progress=None)` を実装する。`LogRecords` は data-model.md のとおり列ごとの `array('q')`（can_id、tx_node、rx_node、tx_request、tx_start、tx_end、rx_end）と `status: bytearray`（「0 = SUCCESS、1 = ARBITRATION_LOST_RETRY、2 = OVERWRITE」）を持ち、`len()` はデータ行の数。読み方は MFC `ReadLogRecords` と同じ: 4 MB ずつバイナリで読み、`\n` で分け、行末の `\r` を 1 つ除き、`,` で分割（引用符は解釈しない）。数値は「先頭に `+` か `-` が 1 つあってもよく、残りが 1 文字以上の ASCII 数字だけ」のときだけ `int()` する。CAN_ID は `re.fullmatch(rb"0[xX][0-9A-Fa-f]+")`。`progress` 引数は受け取るだけで、呼び出しは T057 で入れる。T015 を通す

### 送信のまとめと表の共通部分（FR-010、FR-011、FR-036、contracts/table-csv.md）

- [X] T019 [P] `tests/unit/test_transmissions.py` を書く（実装より先に）: `collect_transmissions` が、受信ノードの数だけ並ぶ行を (can_id, tx_start, tx_node) で 1 回にまとめ、最初に出た行を残し、(can_id, tx_start, tx_node) の昇順に並べること。OVERWRITE の行を数えて返すこと。tx_request < 0 または tx_start < 0 の行を除くこと。Rx_Node が 0 の行も送信として数えること（research.md R-5）
- [X] T020 [P] `tests/unit/test_formatting.py` を書く（実装より先に）: `ecu_name(1) == "ECU 01"`、`ecu_name(16) == "ECU 16"`、`ecu_name(100) == "ECU 100"`、`can_id_text(0x80) == "0x080"`、`can_id_text(0x7ff) == "0x7FF"`、`fixed1(126.0) == "126.0"`。丸めは C の printf と同じく 2 進の値を正確に丸める: `fixed1(0.05) == "0.1"`（2 進では 0.05000000000000000277）、`fixed1(0.25) == "0.2"`（ちょうど半分は偶数側）、`fixed1(0.35) == "0.3"`（2 進では 0.34999999999999997780）。10 進の文字列に直してから四捨五入する実装（`Decimal(str(x)).quantize(Decimal("0.1"), ROUND_HALF_UP)`）では 0.25 → `"0.3"`、0.35 → `"0.4"` となって MFC と違うことも、テストの中で比べて示す（`round(x, 1)` は 2 進の値を正確に丸めるので、この 3 つでは `"%.1f"` と同じになり、比較の相手にならない）
- [X] T021 [P] `tests/unit/test_tables.py` に `write_table_csv` のテストを書く（実装より先に）: 1 行目が表題、2 行目が注記、3 行目が列見出し、以降が行。区切り `,`、引用符なし、改行 LF、最後の行にも LF。行が 0 件でも 3 行出る。セルに `,`・`"`・CR・LF があれば `ValueError`
- [X] T022 `src/can_log_analysis/analysis.py` に `Transmission`（can_id、tx_node、tx_request、tx_start）と `collect_transmissions(records) -> tuple[list[Transmission], int]` を実装する（MFC `CollectTransmissions`。research.md R-5）。T019 を通す
- [X] T023 [P] `src/can_log_analysis/formatting.py` に `ecu_name`（`"ECU %02d" % n`）、`can_id_text`（`"0x%03X" % id`）、`fixed1`（`"%.1f" % x`）と、`reference/mfc/MFCApplication1.rc` からコピーした文言の定数（IDS_LAT_TITLE、IDS_LAT_COLUMNS、IDS_LAT_ALL、IDS_LAT_NOTE、IDS_BUS_TITLE、IDS_BUS_SUMMARY、IDS_BUS_COLUMNS、IDS_WAIT_TITLE、IDS_WAIT_COLUMNS、IDS_WAIT_NOTE、IDS_JIT_TITLE、IDS_JIT_COLUMNS、IDS_JIT_NOTE、IDS_LOG_NONE の 1 文目）を実装する。文言は打ち直さずに .rc からコピーし、µ（U+00B5）、→（U+2192）、−（U+2212）、〜（U+301C）、全角スペース（U+3000）が正しいことをテストで確かめる。T020 を通す
- [X] T024 [P] `src/can_log_analysis/tables.py` に `Table`（kind、title、note、columns、rows）と `write_table_csv(table, out)` を実装する。「セルに `,`・`"`・CR・LF を含んではならない（含めば書き出し時にエラー）」。T021 を通す

**Checkpoint**: 正解 CSV 8 本がそろい、ログを読めて、送信をまとめられ、表を書き出せる

---

## Phase 3: User Story 1 - 送信待ち時間と受信完了時間を確認する (Priority: P1) 🎯 MVP

**Goal**: .canprj を指定すると、受信完了時間と送信待ち時間の表が MFC 版と同じ書式で出る

**Independent Test**: `can-log-analysis tests\data\as001\as001.canprj -a txwait -a latency` が contracts/table-csv.md の例と一致し、sample_vehicle_16ecu の latency.csv・txwait.csv が正解とバイト一致する

### Tests for User Story 1（先に書いて失敗を確認する）

- [X] T025 [P] [US1] `tests/unit/test_stats.py` を書く: `compute_stats` が値を昇順に並べ、件数・最小・最大・平均（`float(sum) / count`）・95%（「昇順の `(count * 95 + 99) // 100` 番目（1 始まり）」）を返す。件数 0 なら「すべて 0」。例: 値 1〜20 で 95% は 19、1〜100 で 95、1 件なら その値、[246, 246, 498] で平均 330.0・95% 498（AR-042）
- [X] T026 [P] [US1] `tests/unit/test_latency.py` を書く: AS-001 の 3 行で、行が「全体」(件数 3、最小 246、平均 330.0、最大 498、95% 498)、(1,5)=498、(3,1)=246、(3,5)=246 の順（AS-001、FR-020、FR-021）。OVERWRITE 2 行を含むログで `overwrite_count == 2` かつ値に入らない（FR-010）。Rx_Node 0、Rx_End −1、Tx_Request −1 の行は外れる。ヘッダだけのログで「全体」の行だけ（件数 0、値はすべて 0）
- [X] T027 [P] [US1] `tests/unit/test_tx_wait.py` を書く: AS-001 で「全体」(2, 0, 126.0, 252, 252)、0x080(ECU 03: 1, 0, 0.0, 0, 0)、0x100(ECU 01: 1, 252, 252.0, 252, 252)（AS-001、FR-023、FR-024）。受信ノード 3 つに並ぶ送信が 1 件に数えられる。各 CAN ID の送信 ECU は「送信開始が最も早い送信の送信ノード」。送信開始が送信要求より前なら負の値のまま。OVERWRITE の数（FR-025）
- [X] T028 [P] [US1] `tests/unit/test_tables.py` に latency と txwait の表のテストを足す: 表題（`受信完了時間 - <P>`、`送信待ち時間 - <P>`）、注記（OVERWRITE の件数入り）、列見出し、全体の行の 2 列目が空欄、セルの書式（contracts/table-csv.md「行の作り方」）
- [X] T029 [P] [US1] `tests/integration/test_cli.py` を書く: `main(["tests/data/as001/as001.canprj", "-a", "txwait", "-a", "latency"])` の標準出力（capsys）が latency → txwait の順で、`tests/data/as001/golden/latency.csv` と `txwait.csv` の内容を空行 1 行でつないだ文字列と等しい。`-o <tmp>` を付けると `<tmp>/latency.csv` と `<tmp>/txwait.csv` だけができ、終了コード 0。`python -m can_log_analysis` を subprocess で呼んでも同じ出力（UTF-8 で読む）
- [X] T030 [P] [US1] `tests/integration/test_golden.py` を書く: ログ（`as001`、`sample_vehicle_16ecu`）と kind（まず `latency`、`txwait`）でパラメータ化し、CLI を `-o tmp_path` で実行して、出力ファイルと `tests/data/<ログ>/golden/<kind>.csv` を UTF-8 の文字列として読み、`==` で比べる（改行の正規化や空白の除去はしない）。違うときは最初に違う行を表示する（SC-001、SC-002）

### Implementation for User Story 1

- [X] T031 [P] [US1] `src/can_log_analysis/stats.py` に `Stats`（count、min_us、max_us、mean_us、p95_us、values）と `compute_stats(values)` を実装する（MFC `ComputeStats`）。`values` は「昇順に並べた値（ヒストグラム用）。メモリのため `list[int]` にしない」: `array('q')` を受け取り、`array('q', sorted(values))` で並べた `array('q')` を持つ（research.md R-3）。T025 を通す（T025 に「values が array('q') であること」の確認も入れる）
- [X] T032 [US1] `src/can_log_analysis/analysis.py` に `LatencyRow`、`LatencyAnalysis` と `analyze_latency(records)` を実装する（MFC `AnalyzeLatency`）: OVERWRITE を数えて除き、`rx_node <= 0 or rx_end < 0 or tx_request < 0` の行を除き、`rx_end - tx_request` を全体と (tx_node, rx_node) ごとに `array('q')` へ集める（`list` にしない。research.md R-3）。rows は「[0] = 全体、続いて (tx_node, rx_node) 昇順」。T026 を通す
- [X] T033 [US1] `src/can_log_analysis/analysis.py` に `TxWaitRow`、`TxWaitAnalysis` と `analyze_tx_wait(records)` を実装する（MFC `AnalyzeTxWait`）: `collect_transmissions` の結果から `tx_start - tx_request` を全体と can_id ごとに `array('q')` へ集める（research.md R-3）。rows は「[0] = 全体、続いて can_id 昇順」、行の tx_node はその ID の最初の送信のもの。T027 を通す
- [X] T034 [US1] `src/can_log_analysis/tables.py` に `latency_table(a, project_name)` と `tx_wait_table(a, project_name)` を実装する（contracts/table-csv.md「行の作り方」、MFC `CLatencyDlg::CreateContent`、`CTxWaitDlg::CreateContent`）。T028 を通す
- [X] T035 [US1] `src/can_log_analysis/cli.py` を実装する（contracts/cli.md）: 引数 PROJECT、`--analysis/-a`（`all`・`latency`・`busload`・`txwait`・`jitter`、複数可、既定 all）、`--output-dir/-o`。出力順は latency → busload → txwait → jitter（この Phase では latency と txwait だけを出し、busload・jitter は US2・US3 で足す）。`sys.stdout.reconfigure(encoding="utf-8", newline="\n")`、`sys.stderr` も UTF-8。すべての表を作り終えてから書き出す。`-o` のファイルは `open(path, "w", encoding="utf-8", newline="\n")`、ディレクトリがなければ作る。成功 0。T029 を通す
- [X] T036 [US1] T030 の golden テスト（latency、txwait）を通す。違いがあれば research.md R-4 の計算順・丸めを見直し、正解 CSV は直さない（正解は MFC のコード）

**Checkpoint**: US1 単独で使える（MVP）。AS-001 と sample_vehicle_16ecu の 2 表が MFC と一致

---

## Phase 4: User Story 2 - 送信ジッタを確認する (Priority: P2)

**Goal**: CAN ID ごとのジッタ表（周期、件数、最小、最大、標準偏差）が MFC 版と同じ書式で出る

**Independent Test**: spec の US2 の受け入れシナリオ 1〜3 を小さなログで確かめ、sample_vehicle_16ecu の jitter.csv が正解とバイト一致する

### Tests for User Story 2（先に書いて失敗を確認する）

- [ ] T037 [P] [US2] `tests/unit/test_jitter.py` を書く（FR-026〜FR-028、AR-070〜AR-072）: 送信要求 0, 10000, 20000 と送信開始 0, 10100, 20000 で、period_us 10000、count 2、min −100、max 100、std_dev 100.0、points が [(10100, 100), (20000, −100)]。送信 1 回の ID は count 0、period_us 0、min/max 0、std_dev 0.0。要求間隔 10000 と 12500 が同数なら 10000。行は can_id 昇順。受信ノードの数だけ並ぶ行が 1 回にまとめられる。OVERWRITE で抜けた送信は、要求間隔が広がるだけでジッタに数えない。標準偏差は「`mean = float(sum) / n` のあと、時系列順に `d = float(v) - mean; squares += d * d`、`math.sqrt(squares / n)`」と同じ値（`statistics.pstdev` と最後の桁が違う例があればそれも入れる）
- [ ] T038 [P] [US2] `tests/unit/test_formatting.py` に `period_text` のテストを足す: 10000 → `"10"`、12500 → `"12.500"`、1 → `"0.001"`、0 → `"0"`、−2000 → `"-2"`、−2500 → `"-2.500"`（剰余と除算は C++ と同じく 0 方向。research.md R-4）
- [ ] T039 [P] [US2] `tests/unit/test_tables.py` に jitter の表のテストを足す: 表題 `送信ジッター - <P>`、注記は IDS_JIT_NOTE、count 0 の行は「CanIdText, EcuName, ``, `0`, ``, ``, ``」
- [ ] T040 [P] [US2] `tests/integration/test_golden.py` と `tests/integration/test_cli.py` に kind `jitter` を足す（-a jitter、all のときの順序）

### Implementation for User Story 2

- [ ] T041 [US2] `src/can_log_analysis/analysis.py` に `JitterPoint`、`JitterRow`、`JitterAnalysis` と `analyze_jitter(records)` を実装する（MFC `AnalyzeJitter`）。period_us は「送信要求の間隔の最頻値（同数なら小さいほう）。送信 1 回なら 0」、count は「送信回数 − 1」、std_dev は research.md R-4 の順序で計算。T037 を通す
- [ ] T042 [US2] `src/can_log_analysis/formatting.py` に `period_text(period_us)` を実装する（C++ と同じ 0 方向の剰余・除算）。T038 を通す
- [ ] T043 [US2] `src/can_log_analysis/tables.py` に `jitter_table(a, project_name)` を実装し、`src/can_log_analysis/cli.py` に kind `jitter` を足す。T039、T040 を通す

**Checkpoint**: US1 と US2 がそれぞれ動く

---

## Phase 5: User Story 3 - CAN バス負荷を確認する (Priority: P2)

**Goal**: バス負荷の要約と ECU 別の表が MFC 版と同じ書式で出る

**Independent Test**: spec の US3 の受け入れシナリオ 1〜3 を確かめ、sample_vehicle_16ecu の busload.csv が正解とバイト一致する

### Tests for User Story 3（先に書いて失敗を確認する）

- [ ] T044 [P] [US3] `tests/unit/test_bus_load.py` を書く（FR-031〜FR-035、AR-080〜AR-083）: AS-001 で range_us 10010000、transmission_count 2、ecus が ECU 01（frame_count 1）と ECU 03（frame_count 1）。9990〜10010 µs の 1 送信で section_pct[0] と [1] にそれぞれ 10 µs 分（0.1）。送信なし（ヘッダだけ）で range_us 10000、average_pct 0.0、max_pct 0.0、max_section 0、ecus 空。Tx_End ≦ Tx_Start と Tx_Start < 0 の行は除き、Tx_Request −1 の行は含む（CollectTransmissions と条件が違う。research.md R-5）。同じ最大値の区間が 2 つあれば最初のほう。重複のまとめはキー (tx_node, can_id, tx_start) で最初の行の tx_end を使う。負荷率は `100.0 * busy / section_us`、使用率は `100.0 * busy_us / range_us` の順で計算
- [ ] T045 [P] [US3] `tests/unit/test_tables.py` に busload の表のテストを足す: 表題 `CAN バス負荷 - <P>`、2 行目の要約 `平均負荷 <A>%　最大負荷 <M>%（<S>〜<E> ms）　範囲 0〜<R> ms（10 ms ごと）`（全角スペース U+3000、〜 U+301C、S = max_section × 10、E = (max_section + 1) × 10、R = range_us // 1000）、列 `ECU,送信フレーム数,使用率 (%)`
- [ ] T046 [P] [US3] `tests/integration/test_golden.py` と `tests/integration/test_cli.py` に kind `busload` を足す（-a busload、all のときの順序 latency → busload → txwait → jitter）

### Implementation for User Story 3

- [ ] T047 [US3] `src/can_log_analysis/analysis.py` に `EcuBusUsage`、`BusLoadAnalysis` と `analyze_bus_load(records)` を実装する（MFC `AnalyzeBusLoad`）。section_us は「10000 固定」、range_us は「送信がなければ 10000、あれば ceil(最後の tx_end / 10000) × 10000」、max_section は「最大の負荷率と、それが最初に現れた区間（0 始まり）。全部 0 なら 0.0 / 0」、ecus は「送信したノードだけ、ノード番号順」。T044 を通す
- [ ] T048 [US3] `src/can_log_analysis/tables.py` に `bus_load_table(a, project_name)` を実装し、`src/can_log_analysis/cli.py` に kind `busload` を足す。T045、T046 を通す

**Checkpoint**: 4 つの表すべてが MFC と一致

---

## Phase 6: User Story 4 - 読めない入力の理由を知る (Priority: P3)

**Goal**: 壊れた入力では理由が 1 行出て、表は 1 つも出ずに失敗で終わる

**Independent Test**: `tests/data/errors/` の各プロジェクトでメッセージと終了コード 1 を確かめる

### Tests for User Story 4（先に書いて失敗を確認する）

- [ ] T049 [P] [US4] 不正入力のデータを作る: `tests/data/errors/` に、`no_status_column.canprj`（ヘッダに Status がない）、`bad_number.canprj`（5 行目の Tx_Start が `12a`）、`bad_can_id.canprj`、`bad_status.canprj`、`too_few_columns.canprj`、`empty_log.canprj`（0 バイトのログ）、`no_log.canprj`（.log.csv なし）、`bad_project.canprj`（INI として読めない）。各 .canprj は `[Project]\nEcuCount=1\n`（bad_project を除く）。UTF-8・LF
- [ ] T050 [P] [US4] `tests/integration/test_cli_errors.py` を書く（contracts/cli.md「出力と終了コード」、SC-004）: 各データで終了コード 1、標準出力は空、標準エラーは 1 行で、`<ログのパス>: line 1: no column Status`、`…: line 5: bad number`、`プロジェクト「no_log.canprj」のシミュレーションログはありません。`、`プロジェクトファイルがありません: <PROJECT>`、`プロジェクトファイルを読めません: <PROJECT>: <理由>` の形。`-o tmp` を付けて失敗したとき、ファイルが 1 つもできない。存在しない `-a foo` で終了コード 2。出力先に書けない（`-o` に既存のファイルを指定）とき `出力できません: <パス>: <理由>` と終了コード 1

### Implementation for User Story 4

- [ ] T051 [US4] `src/can_log_analysis/cli.py` で `CanLogAnalysisError` の各例外を contracts/cli.md の文言に変えて標準エラーに 1 行で出し、終了コード 1 を返す。`OSError`（出力先）は `出力できません: <パス>: <理由>`。読み込み・解析・表の作成をすべて終えてから書き出すことで、失敗時に部分的なファイルを残さない。T050 を通す

**Checkpoint**: 不正入力で誤った表を出さない

---

## Phase 7: User Story 5 - 画面機能から解析コアを使う (Priority: P3)

**Goal**: 画面機能がヒストグラム・ジッタ時系列・区間ごとの負荷率・進捗・中止を解析コアから使える

**Independent Test**: spec の US5 の受け入れシナリオ 1〜3

### Tests for User Story 5（先に書いて失敗を確認する）

- [ ] T052 [P] [US5] `tests/unit/test_histogram.py` を書く（AR-043、FR-013）: 値 0〜99 の 100 件で width 10、start 0、10 本 × 10 件。[246, 246, 246] で start 246、width 1、counts [3]。空で counts 空。負の値（−15〜+15）で start が負方向に切り捨て（floor）。n が大きいとき目安が 50 本で頭打ち（0〜9999 の 10000 件: ceil(√10000) = 100 → 50 本に抑えられ、9999 / 50 = 199.98 → 幅 200、start 0、ビン 50 本 × 200 件。2500 件は √ = 50 ちょうどで上限が効いているか確かめられないので使わない）。幅が 1・2・5 × 10^m になる例（0 と 37 を含む 20 件 → 目安 10 本 → 3.7 → 幅 5）。各ビンの件数の合計 == n
- [ ] T053 [P] [US5] `tests/unit/test_log_reader.py` に進捗・中止のテストを足す（FR-007）: 4 MB を超えるログ（テスト中に一時フォルダへ生成）で progress が「4 MB 読むごと（最後の塊を除く）と、読み終えたときに 1 回」呼ばれ、引数が (読んだバイト数, 全体のバイト数) で、最後は両者が等しい。途中で False を返すと `LogReadCancelled` が出る。小さなログでも最後の 1 回は呼ばれる。あわせて `tests/integration/test_cli_progress.py` を書く（FR-042〜FR-044、contracts/cli.md「進捗」）: `cli._now` を monkeypatch して 0.5 秒を超えた状態にすると、標準エラーに `ログを読み込んでいます... 100%` と `集計しています...` が出て、標準出力は進捗なしの場合と 1 文字も違わない（`-o` のファイルも同じ）。0.5 秒以内なら標準エラーは空。`--quiet`（`-q`）なら 0.5 秒を超えても標準エラーは空。標準エラーが端末でないとき進捗は 1 回 1 行（LF）。N% は前回と同じ値なら出さない。`read_log_records`（または解析関数）を monkeypatch して `KeyboardInterrupt` を出すと、終了コード 130、標準エラーの最後の行が `中断しました。`、標準出力は空、`-o` のディレクトリにファイルが 1 つもできない（読み込み中と計算中の 2 通り）
- [ ] T054 [P] [US5] `tests/unit/test_core_api.py` を書く: `can_log_analysis` から contracts/core-api.md の公開名（`open_project`、`read_log_records`、`analyze_latency`、`analyze_tx_wait`、`analyze_jitter`、`analyze_bus_load`、`collect_transmissions`、`make_histogram`、`latency_table`、`bus_load_table`、`tx_wait_table`、`jitter_table`、`ecu_name`、`can_id_text`、`fixed1`、`period_text`、`write_table_csv`、例外クラス）を import できる。`JitterRow.points` と `BusLoadAnalysis.section_pct` が取り出せる（FR-030、FR-033）。解析関数が records を変更しない

### Implementation for User Story 5

- [ ] T055 [P] [US5] `src/can_log_analysis/stats.py` に `Histogram`（start_us、width_us、counts）、`nice_ceil(x)`、`make_histogram(sorted_values)` を実装する（MFC `NiceCeil`、`MakeHistogram`）。`math.log10`・`math.floor`・`math.pow(10.0, …)` と許容 `1e-9` を C++ と同じに、`std::llround` は `math.floor(x + 0.5)` で置き換える（research.md R-4）。T052 を通す
- [ ] T056 [US5] `src/can_log_analysis/__init__.py` で T054 の公開名を再エクスポートする。T054 を通す
- [ ] T057 [US5] `src/can_log_analysis/log_reader.py` の `read_log_records` で `progress` を呼ぶ（MFC と同じタイミング）。False なら読んだ結果を捨てて `LogReadCancelled` を出す。続けて `src/can_log_analysis/cli.py`（T035 の後）に進捗と中止を入れる（contracts/cli.md「進捗」、research.md R-12）: `--quiet/-q` を足す。`_now = time.monotonic` を経由して開始時刻を取り、`progress` の中で 0.5 秒を超えていれば標準エラーに `ログを読み込んでいます... N%`（N = 読んだバイト数 × 100 // 全体、全体 0 なら 100。前回と同じ N なら出さない）、読み込み後に 0.5 秒を超えていれば `集計しています...` を 1 回出す。標準エラーが端末なら `\r` で上書きして終わりに改行、端末でなければ 1 回 1 行。進捗は標準出力・出力ファイルに書かない。`main` で `KeyboardInterrupt` を受け止め、`中断しました。` を出して 130 を返す（書き出し前ならファイルは作らない）。T053 を通し、T029・T050 も引き続き通ることを確かめる

**Checkpoint**: すべてのユーザーストーリーが動く

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 憲章の品質ゲートと性能

- [ ] T058 [P] `tests/unit/test_no_gui_import.py` を書く: `src/can_log_analysis/` の全 .py を `ast` で読み、`PySide6`、`PyQt5`、`PyQt6`、`tkinter`、`matplotlib`、`numpy`、`pandas` の import がないことを確かめる（憲章 原則 II、SC-005）
- [ ] T059 [P] `tests/perf/test_large_log.py` と `tests/perf/memory_probe.py` を書く（`@pytest.mark.perf`、SC-003、plan.md Constraints）。16 ECU・31 ID 相当の 300 万行（約 300 MB）の合成ログを、モジュール単位の fixture で tmp に 1 回だけ生成し、次の 2 つを**別々のテスト・別々のプロセス**で測る。(1) 時間: `python -m can_log_analysis <proj> -o <tmp> -q` を subprocess で実行し（4 解析すべて）、経過時間が 60 秒以内。計測中は `tracemalloc` などの計測を一切有効にしない。(2) メモリ: `memory_probe.py` を subprocess で実行する。このスクリプトは同じ CLI の処理を呼んだあと、`ctypes` で Windows の `GetProcessMemoryInfo`（`PROCESS_MEMORY_COUNTERS.PeakWorkingSetSize`）を読んでピークのバイト数を標準出力に出す（Windows 以外では `resource.getrusage(RUSAGE_SELF).ru_maxrss`）。テストはそれが 1 GB 未満であることを確かめる。`tracemalloc` は使わない（処理が数倍遅くなり、ネイティブのメモリも数えないため）。どちらも結果の数値をテストの出力に残す。`pytest -m perf` で実行し、60 秒を超えたら research.md R-3 に従って `log_reader.py` の 1 行あたりの処理を、1 GB を超えたら途中の値の持ち方を見直す
- [ ] T060 [P] `CLAUDE.md` の「リポジトリの現状」を更新する: 実装が始まったこと、`PythonApplication1/` を削除したこと、テストコマンド（`.venv\Scripts\Activate.ps1`、`pip install -e ".[dev]"`、`pytest`、`pytest -m perf`）、正解生成プログラムのビルド（`tools\mfc_golden\build.ps1` を PowerShell から）
- [ ] T061 `specs/001-log-analysis-core-cli/quickstart.md` の手順 1〜7 を上から実行し、期待どおりにならない箇所があれば quickstart.md かコードを直す
- [ ] T062 `pytest` が全件成功し、`tests/data/sample_vehicle_16ecu/golden/VERIFIED.md` にI.Hの確認結果が書かれていることを確かめる（憲章「品質ゲート」1〜4）。未記入なら、その旨を利用者に伝えて完了としない

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: すぐ始められる。T001（Python 3.11 以上）がなければ以降すべて止まる
- **Foundational (Phase 2)**: Setup の後。すべてのストーリーを止める
  - T007〜T010 → T012（ビルドと正解 CSV）。T011 → T012。T012 → T013（目視確認の依頼）
  - T014・T015 → T016 → T017・T018
  - T019 → T022、T020 → T023、T021 → T024
- **US1 (Phase 3)**: Foundational の後。MVP
- **US2 (Phase 4)**・**US3 (Phase 5)**: Foundational の後なら US1 と独立に作れる。ただし `analysis.py`、`tables.py`、`cli.py`、`test_tables.py`、`test_golden.py` を共有するので、同時に進めるときは同じファイルへの編集がぶつからないよう順番に入れる。CLI の骨格（T035）が先にあると楽なので、実際には US1 → US2 → US3 の順を勧める
- **US4 (Phase 6)**: T035（cli.py）の後
- **US5 (Phase 7)**: Foundational の後なら独立（T057 は T018 と T035 の後、T056 は全解析関数の後）
- **Polish (Phase 8)**: すべての後。T062 は T013 の記入も待つ

### User Story Dependencies

- **US1 (P1)**: Foundational のみに依存
- **US2 (P2)**: Foundational（collect_transmissions）。CLI への追加は T035 の後
- **US3 (P2)**: Foundational。CLI への追加は T035 の後
- **US4 (P3)**: US1 の CLI（T035）
- **US5 (P3)**: Foundational（log_reader、stats.py の作成は T031 と同じファイルなので T031 の後）

### Within Each User Story

- テストを先に書いて失敗を確かめる → モデル・解析 → 表 → CLI → golden
- 正解 CSV が合わないときは Python 側を直す。正解 CSV と `reference/mfc` は直さない

### Parallel Opportunities

- Phase 1: T005 と T006 は並行可
- Phase 2: T007〜T010（tools/mfc_golden の 4 ファイル）、T014・T015（テスト 2 本）、T019〜T021（テスト 3 本）、T023・T024 は並行可
- 各ストーリーのテストタスク（[P]）は並行して書ける
- US5 の T052〜T055 は US2〜US4 と並行可

---

## Parallel Example: User Story 1

```text
# テストを同時に書く:
Task: "T025 tests/unit/test_stats.py"
Task: "T026 tests/unit/test_latency.py"
Task: "T027 tests/unit/test_tx_wait.py"
Task: "T028 tests/unit/test_tables.py（latency / txwait）"
Task: "T029 tests/integration/test_cli.py"
Task: "T030 tests/integration/test_golden.py"

# その後、stats.py（T031）だけ先に並行で、analysis.py の T032 → T033 は順番に
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup（Python 3.12 の用意が最初の関門）
2. Phase 2: Foundational（正解 CSV を最初に作り、目視確認を依頼しておく）
3. Phase 3: US1
4. **止めて確かめる**: AS-001 と sample_vehicle_16ecu の latency・txwait が正解と一致

### Incremental Delivery

1. Setup + Foundational → 正解 CSV と読み込みができる
2. US1 → 遅延の 2 表（MVP）
3. US2 → ジッタ表
4. US3 → バス負荷
5. US4 → エラー時の振る舞い
6. US5 → 画面機能への受け渡し
7. Polish → 性能・GUI 非依存・quickstart・目視確認の記録

---

## Notes

- [P] = 別ファイルで、未完了のタスクに依存しない
- [Story] はトレーサビリティのため。テスト名・docstring にも FR／AR／AS の ID を書く
- 論理的なまとまりごとにコミットする（コミットは利用者の指示があったときだけ）
- 各 Checkpoint で止めて、そのストーリー単独で確かめられる
