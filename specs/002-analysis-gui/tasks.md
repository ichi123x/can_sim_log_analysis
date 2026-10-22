---

description: "CANログ解析ツールの画面 の実装タスク"
---

# Tasks: CANログ解析ツールの画面

**Input**: `specs/002-analysis-gui/` の設計文書

**Prerequisites**: [plan.md](plan.md)、[spec.md](spec.md)、[research.md](research.md)、[data-model.md](data-model.md)、
[contracts/gui.md](contracts/gui.md)、[contracts/core-additions.md](contracts/core-additions.md)、[quickstart.md](quickstart.md)

**Tests**: 必須（憲章 原則 III。画面は pytest-qt）。各ストーリーのテストタスクを先に書き、失敗を確かめてから実装する。

**Organization**: spec.md の User Story 1〜5 ごと。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 並行してよい（別ファイルで、未完了のタスクに依存しない）
- **[Story]**: US1〜US5
- パスはリポジトリのルートからの相対パス

## 全タスク共通の決まり

- MFC 版（`reference/mfc/AnalysisDlg.cpp`、`MFCApplication1Dlg.cpp` の RunAnalysis・OnAnalysis*・CloseResultWindows、`MFCApplication1.rc`）を正解とする。`reference/` は読むだけ。
- 文言は `MFCApplication1.rc` からコピーし、打ち直さない（テストで .rc と照合する）。寸法は 96 dpi 換算の論理ピクセル（Qt が DPI に合わせて拡大する）。
- 表のセルは機能 001 の `Table` をそのまま表示する。画面で数値を整形し直さない。
- 解析コア `src/can_log_analysis/` は Qt を import しない（`tests/unit/test_no_gui_import.py`）。画面 `src/can_log_analysis_gui/` → コアの一方向。
- テスト名か docstring に FR／SC／AR の ID を書く。
- 書くファイルは UTF-8（BOM なし）・LF。.ps1 と .bat は ASCII だけで書く（Windows PowerShell 5.1・cmd が日本語を読み違えるため）。
- コマンドは PowerShell から実行する。テストは `.venv\Scripts\python.exe -m pytest`。

---

## Phase 1: Setup（共通の準備）

- [X] T001 `pyproject.toml` を更新する: `[project.optional-dependencies]` に `gui = ["PySide6>=6.8"]` を足し、`dev` を `["pytest", "pytest-qt>=4.5", "PySide6>=6.8"]` にする。`[project.gui-scripts]` に `can-log-analysis-gui = "can_log_analysis_gui.app:main"` を足す。`[tool.pytest.ini_options]` の markers に `perf` があることを確かめる。`.venv\Scripts\python.exe -m pip install -e ".[dev]"` を実行し、`python -c "import PySide6; print(PySide6.__version__)"` が 6.8 以上を出すことを確かめる
- [X] T002 パッケージの骨格を作る: `src/can_log_analysis_gui/__init__.py`（docstring だけ）、`src/can_log_analysis_gui/__main__.py`（`from can_log_analysis_gui.app import main; raise SystemExit(main())`）、`src/can_log_analysis_gui/app.py`（`def main(argv=None) -> int: return 0` だけ）。`.venv\Scripts\can-log-analysis-gui.exe` ができていることを確かめる
- [X] T003 `tests/gui/conftest.py` を作る（実装メモ: conftest.py が 2 つあると既存テストの `from conftest import` が不定になるため、fixture は既存の `tests/conftest.py` に足した）: 先頭で `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")`（Qt の import より前）。fixture: `golden(log, kind)` → `tests/data/<log>/golden/<kind>.csv` を読み、(title, note, columns, rows) を返す。`dialogs`（monkeypatch で `can_log_analysis_gui.app.ask_project_path` と `can_log_analysis_gui.app.show_message` を差し替え、選ばせるパスを設定でき、出たメッセージ (icon, text) を記録する）。`main_window(qtbot, dialogs)` → `MainWindow` を作って `qtbot.addWidget` する。`wait_window(main_window, kind)` → `qtbot.waitUntil(lambda: kind in main_window.windows, timeout=10000)` のヘルパ
- [X] T004 [P] `tests/gui/test_texts.py` を書く（実装より先に）: `reference/mfc/MFCApplication1.rc`（UTF-16）を読み、`can_log_analysis_gui.texts` の定数が .rc の文字列と一致することを確かめる。対象: メニュー（`ファイル(&F)`、`プロジェクト読込み(&O)...`、`解析(&A)`、`送信待ち時間(&W)...`、`受信完了時間(&R)...`、`送信ジッター(&J)...`、`CAN バス負荷(&B)...`。IDR_MAINMENU の POPUP／MENUITEM 行から取る）、IDS_LOG_NONE_NOPROJECT、IDS_LOG_NONE、IDS_LOG_READ_ERROR、IDS_LOAD_ERROR、IDS_PROJECT_FILTER、IDS_PROJECT_PATH_LABEL、IDS_ANALYSIS_NO_DATA、IDS_LAT_AXIS_X、IDS_LAT_AXIS_Y、IDS_BUS_AXIS_X、IDS_BUS_AXIS_Y、IDS_JIT_AXIS_Y、IDS_BUS_AVERAGE、IDS_ANALYZING_READ、IDS_ANALYZING_CALC、IDS_ANALYZING_CANCEL、IDD_ANALYSIS_PROGRESS の CAPTION「解析中」とボタン「中断」。.rc の `\n` は改行に直して比べる。`texts.MENU_EXIT == "終了(&X)"`（.rc にないので値だけ確かめる）
- [X] T005 `src/can_log_analysis_gui/texts.py` を実装する（T004 の定数。.rc からコピー）。メニューの `&` は Qt でもアクセスキーとして働くのでそのまま使う。IDS_PROJECT_FILTER は Qt のファイル選択の書式 `"CAN プロジェクト (*.canprj);;すべてのファイル (*.*)"` に変換する関数 `qt_project_filter()` も置く。T004 を通す

---

## Phase 2: Foundational（全ストーリーの前提）

**⚠️ CRITICAL**: この Phase が終わるまでユーザーストーリーに入らない

### 解析コアへの追加（contracts/core-additions.md。Qt に依存しない）

- [X] T006 [P] `tests/unit/test_plot.py` を書く（実装より先に）。MFC の式どおりの期待値: `nice_ticks(0, 100, 5) == [0, 20, 40, 60, 80, 100]`、`nice_ticks(0, 37, 4) == [0, 10, 20, 30]`、`nice_ticks(5, 5, 4) == [5]`、`nice_ticks(0, 1, 8) == [0, 0.2, 0.4, 0.6, 0.8, 1.0]`（浮動小数点は `pytest.approx`）、`ticks_from_zero(37, 4) == [0, 10, 20, 30, 40]`、`ticks_from_zero(50, 5) == [0, 10, 20, 30, 40, 50]`、`ticks_from_zero(0.0, 1) == [0, 1]`（hi は 1 に引き上げ）、`ticks_covering(-178, 178, 5) == [-200, -100, 0, 100, 200]`、`ticks_covering(3, 3, 5) == [3, 3]`（目盛りが 1 つなら [lo, hi]）、`format_tick(20.0) == "20"`、`format_tick(0.2) == "0.2"`、`format_tick(2.5e-5) == "2.5e-05"`、`format_tick(12.5) == "12.5"`。`min_max_per_column([JitterPoint(0, 3), JitterPoint(5, -1), JitterPoint(10, 7)], 0, 10, 2)` → 列 0: has, min −1, max 3、列 1: has, min 7, max 7（列 = (t − t0) × columns // span、span = max(1, t1 − t0 + 1)、0〜columns−1 に丸める）。点のない列は has False。`columns <= 0` は空。`max_per_column([1, 5, 2, 8, 3, 4], 3) == [5, 8, 4]`（列 c は [c n / cols, (c+1) n / cols)）、値が列以下ならそのまま、`columns <= 0` もそのまま
- [X] T007 [P] `tests/unit/test_project_contents.py` を書く（実装より先に）。`read_project_contents(open_project(tests/data/sample_vehicle_16ecu/sample_vehicle_16ecu.canprj))`: bit_rate_bps 500000、ecu_count 16、duration_sec 5、ecus 16 件（section_no 1〜16 の順）、ecus[0] は node_id 1、name「ECM Engine Control Module」、label「エンジン」、rx_filter「0x0A8,0x0E0,0x380,0x3E8」、receive_delay_us・power_on_time_us・init_duration_us は None（.canprj にない）。frames 31 件、frames[0] は node_section_no 1、frame_no 1、name「EngineRPM_ThrottlePos」、can_id 0x0C0、dlc 8、period_us 10000、initial_offset_us 5000。frames[3] は dlc 4、period_us 200000。tmp に作った .canprj で: [NodeN] の N が 10 と 2 なら 2 → 10 の順（数値順）、`PeriodUs=abc` は None、`CanId=12` は None（0x なし）、セクションがなければ ecus・frames は空、[Project] がなければ ecu_count None。`Node1.Frame1` のように「.FrameM」の M が数でないセクションは無視
- [X] T008 `src/can_log_analysis/plot.py` を実装する（contracts/core-additions.md）。`ColumnRange`（has、min_us、max_us）を含む。刻みは `can_log_analysis.stats.nice_ceil`。NiceTicks: `first = math.ceil(lo / step - 1e-9)`、`(first + i) * step <= hi + step * 1e-9` まで、`abs(t) < step * 1e-9` なら 0.0。TicksFromZero: `nice_ticks(0, max(hi, 1), n)`、2 つ以上あって最後 < hi なら 1 刻み足す。TicksCovering: nice_ticks が 2 未満なら [lo, hi]、先頭 > lo + step·1e-9 なら前に 1 刻み、末尾 < hi − step·1e-9 なら後ろに 1 刻み。T006 を通す
- [X] T009 `src/can_log_analysis/project.py` に `ProjectContents`、`EcuInfo`、`FrameInfo` と `read_project_contents(project)` を実装する（data-model.md。「.canprj に項目がない・数値でないときは None」）。セクション名は `re.fullmatch(r"Node(\d+)", name)` と `re.fullmatch(r"Node(\d+)\.Frame(\d+)", name)`。CanId は `re.fullmatch(r"0[xX][0-9A-Fa-f]+")` のときだけ int。読み方は `open_project` と同じ configparser（共通の関数にまとめる）。読めなければ `ProjectReadError`。`src/can_log_analysis/__init__.py` の `__all__` に足す。T007 を通す
- [X] T010 `src/can_log_analysis/stats.py` の `make_histogram` を、各ビンの件数を `bisect.bisect_left(sorted_values, start + i * width)` の差で数える形に直す（research.md R-5。値は昇順）。`tests/unit/test_histogram.py` と golden テストがそのまま通ること、`tests/unit/test_no_gui_import.py` が `plot.py` も対象に通ることを確かめる

### グラフとジョブの土台（画面）

- [X] T011 [P] `tests/gui/test_graph_plan.py` を書く（実装より先に）。`GraphWidget.plan(width, height) -> Plan`（描画計画。Qt の描画はしない）を検証する。Plan は plot（プロット領域の矩形）、x_range、y_range、x_ticks（値と文字）、y_ticks（値と文字）、shapes（種類ごとの図形のリスト）、no_data_text を持つ。ケース: (1) NoData → no_data_text「データがありません」で他は空。(2) Bars（start 0、width 1、counts [50]）、大きさ 1000×500 → plot = (70, 32, 910, 422)（左 70・上 32・右 20・下 46 を除く）、x_range 0〜1、y_ticks 0,10,20,30,40,50、x_ticks は `nice_ticks(0, 1, max(2, 910 // 90))`、棒 1 本で高さは件数 50 が y_range の上端。(3) 幅 2 px を超える棒は右に 1 px の隙間、件数 0 のビンは描かない。(4) Deviation（点 3 つ、ずれ −100・0・100）→ y_ticks は ticks_covering(−100, 100, 5)、0 の線あり、点と線。全部 0 なら y_ticks −1, 0, 1。(5) Deviation で点の数 > プロット幅（例 幅 300 の画面に 499 点）→ 列ごとの縦線（min_max_per_column(points, 0, 最後の時刻, plot 幅)）。(6) Line（区間 500、平均 19.0）→ y_ticks 0〜100 を 20 刻み、x_range 0〜5000 ms、折れ線の点は max_per_column(section_pct, plot 幅) の数、平均の破線と文字「平均 19.0%」。(7) プロット領域が幅 < 40 または高さ < 30 なら shapes 空。軸名: 横は下中央、縦は左上
- [X] T012 [P] `tests/gui/test_job.py` を書く（実装より先に）: `AnalysisJob(log_path, kind)` を start し、`finished` シグナルで (state, result) を受ける。as001 の log で txwait → state "done"、result は (TxWaitAnalysis, Table) で Table が golden と一致。progress のたびに `phase`・`done_bytes`・`total_bytes` が更新され、読み込み後 phase が "calculating" になる。`cancel()` を読み込み前に呼ぶと state "cancelled"（`LogReadCancelled`）、計算中に呼ぶと計算が終わってから "cancelled"。`tests/data/errors/bad_number.canprj.log.csv` → "read_error"。ジョブのスレッドが GUI スレッドと違うこと
- [X] T013 `src/can_log_analysis_gui/graph.py` に `GraphWidget(QWidget)` を実装する: `set_no_data(text)`、`set_bars(histogram, x_label, y_label)`、`set_line(pct, section_us, average_pct, x_label, y_label)`、`set_deviation(points, x_label, y_label)`（MFC CAnalysisGraph の SetBars／SetLine／SetDeviation／SetNoData）、`plan(width, height)`（contracts/gui.md「グラフの描き方」をそのまま式にする。目盛りと間引きは `can_log_analysis.plot`）、`paintEvent`（plan を QPainter で描く。背景白、外枠、グリッド線、Meiryo UI、棒・線の色は MFC に近い青、平均は破線、平均の文字は白地）。T011 を通す
- [X] T014 `src/can_log_analysis_gui/job.py` に `AnalysisJob(QObject)` を実装する（data-model.md「AnalysisJob」の状態遷移、research.md R-3）: 作業は `QThread` に `moveToThread` して `read_log_records(log_path, progress=...)` → 選んだ解析と表（txwait: `analyze_tx_wait`＋`tx_wait_table` など 4 種）。progress は done・total を記録し `not self._cancel` を返す。状態と進捗はロックで守り、GUI からは `phase()`、`progress()`（done, total）で読む。`finished(str, object)` シグナル（state, result）。T012 を通す

**Checkpoint**: 目盛り・間引き・.canprj の読み取りがコアにあり、グラフの描画計画とジョブが単体で動く

---

## Phase 3: User Story 1 - プロジェクトを開いて送信待ち時間を見る (Priority: P1) 🎯 MVP

**Goal**: メインウィンドウ（メニュー、プロジェクトの読込みと表示）と送信待ち時間の画面

**Independent Test**: sample_vehicle_16ecu を開き、送信待ち時間の画面の表 32 行が golden/txwait.csv と一致し、行を選ぶとグラフが変わる

### Tests for User Story 1（先に書いて失敗を確認する）

- [X] T015 [P] [US1] `tests/gui/test_main_window.py` を書く（FR-001〜FR-005、FR-060a）: タイトル「CAN ログ解析」、メニューバーの 2 つのメニューと項目の表示名・並び・区切り線（contracts/gui.md のメニュー図どおり。`QAction.text()` で比べる）。`dialogs` に sample のパスを選ばせて「プロジェクト読込み」→ タイトル「CAN ログ解析 - sample_vehicle_16ecu.canprj」、プロジェクト名・パス・ログの表示、通信速度「500 kbps」、ECU 数「16」、シミュレーション時間「5 s」、ECU 表 16 行（1 行目: 「ECU 01」「ECM Engine Control Module」「エンジン」「0x0A8,0x0E0,0x380,0x3E8」、遅延などは空欄）、送信フレーム表 31 行（1 行目: 「ECU 01」「1」「EngineRPM_ThrottlePos」「0x0C0」「8」「5」「10」）、表は編集できない。ms 表示は MFC FormatMs（12500 µs → 「12.500」）。`MainWindow(project=<sample>)`（起動引数）でも同じ表示。最初のフォルダは前に開いたプロジェクトのフォルダ
- [X] T016 [P] [US1] `tests/gui/test_analysis_windows.py` に送信待ち時間のテストを書く（FR-010〜FR-011、FR-020〜FR-025、FR-030〜FR-032、SC-001）: sample を開いて「解析 > 送信待ち時間」→ `wait_window` で画面ができる。タイトル「送信待ち時間 - sample_vehicle_16ecu.canprj」、列見出し・全セル・注記が `golden("sample_vehicle_16ecu", "txwait")` と完全一致、数値の列（3 列目から）は右寄せ、列幅 90,90,80,100,100,100,100、1 行だけ選べる、選択は 1 行目、グラフは Bars（全体の行のヒストグラム）。0x1A0 の行を選ぶ → Bars（start 0、width 1、counts [50]）。もう一度メニューを選ぶ → 画面は増えず（`main_window.windows` は 1 つ）、ジョブも始まらない。Esc で閉じて `windows` から消える、Enter では閉じない。大きさは枠を含めたウィンドウ全体（FR-022）: `frameGeometry()` が 900×640、最小サイズまで縮めたときの `frameGeometry()` が 520×400。配置は中身の大きさ（`rect()`）で LayoutListNoteGraph の式に合う（表の高さ = (中身の高さ − 2×8 − 22 − 8) × 2 // 5 など。中身の高さは実際の値から取り、640 と決め打ちしない。offscreen では枠の幅が 0 のことがあるので、そのときも成り立つ書き方にする）。位置（FR-022、MFC OnInitDialog）: 解析画面の `frameGeometry()` の中心がメインウィンドウの `frameGeometry()` の中心と一致（±1 px）。メインウィンドウを作業領域（`screen().availableGeometry()`）の右下の端に寄せてから開くと、解析画面は作業領域からはみ出さないよう左上にずれる（ずらす順は右 → 下 → 左 → 上）。別のプロジェクトを開くと解析画面がすべて閉じる（FR-005）

### Implementation for User Story 1

- [X] T017 [P] [US1] `src/can_log_analysis_gui/project_view.py` に `ProjectView(QWidget)` を実装する（contracts/gui.md「メインウィンドウ」の本体 1〜4。`read_project_contents` の結果を表示。ms は MFC FormatMs と同じ関数 `format_ms(us)`、通信速度は `format_bit_rate(bps)`、値が None なら空欄、表は `QTableWidget` で編集不可・数値列右寄せ、ECU 表と送信フレーム表は `QSplitter` で上下）
- [X] T018 [US1] `src/can_log_analysis_gui/analysis_window.py` に `AnalysisWindow(QWidget)`（共通: Table の表示、列幅・右寄せ、1 行選択、Esc で閉じる・Enter で閉じない、閉じたら `closed(kind)` シグナル。初期サイズと最小サイズは枠を含めた大きさで指定する: `show()` のあとに枠の幅（`frameGeometry()` − `geometry()`）を見て中身の大きさを決める共通の関数を作る。配置は MFC `CAnalysisDlgBase::OnInitDialog` と同じく、枠を含めた矩形をメインウィンドウの中央に置き、作業領域の右 → 下 → 左 → 上の順にはみ出しを直す）と `ListNoteGraphWindow`（LayoutListNoteGraph の配置、開いたら 1 行目を選択、選択でグラフ切り替え、行ごとのヒストグラムを覚える）と txwait 用の設定（列幅、右寄せ開始列 2、グラフは件数 0 → NoData、それ以外 → Bars、軸名 IDS_LAT_AXIS_X／Y）を実装する
- [X] T019 [US1] `src/can_log_analysis_gui/main_window.py` に `MainWindow(QMainWindow)` を実装する: メニュー（texts の表示名、Ctrl+O）、`open_project(path)`（`open_project`＋`read_project_contents`、成功で解析画面を全部閉じて表示とタイトルを更新、失敗は US5 で扱うので今は例外をそのまま出してよい）、`windows: dict[str, AnalysisWindow]`、「解析」の各項目 → `run_analysis(kind)`（開いていれば前面に出して終わり。未選択・ログなしは US5。`AnalysisJob` を始め、done なら解析画面を作って `windows` に入れて表示）、`project_view`。起動引数の project を開く
- [X] T020 [US1] `src/can_log_analysis_gui/app.py` を実装する: `main(argv=None)`（`QApplication`、引数 `[PROJECT]`、`MainWindow` を表示、`app.exec()` の戻り値を返す）、差し替え可能な `ask_project_path(parent, start_dir) -> str | None`（`QFileDialog.getOpenFileName`、filter は `texts.qt_project_filter()`）、`show_message(parent, icon, text)`（`QMessageBox`。icon は "information"／"warning"）。T015・T016 を通す

**Checkpoint**: MVP。sample を開いて送信待ち時間を見られる

---

## Phase 4: User Story 2 - 受信完了時間と送信ジッターを見る (Priority: P2)

**Goal**: 受信完了時間（ヒストグラム）と送信ジッター（時系列）の画面

**Independent Test**: sample で 2 画面の表が golden と一致し、ジッターの時系列が出る

### Tests for User Story 2（先に書いて失敗を確認する）

- [X] T021 [P] [US2] `tests/gui/test_analysis_windows.py` に受信完了時間と送信ジッターのテストを足す（FR-032〜FR-034、SC-001）: 受信完了時間の表・注記・タイトルが `golden("sample_vehicle_16ecu", "latency")` と一致、列幅・右寄せは txwait と同じ、全体の行のヒストグラム。送信ジッターの表・注記・タイトルが golden の jitter と一致、列幅 90,90,90,80,100,100,110、右寄せは 3 列目から、1 行目（0x050）の Deviation（点 49 個、横軸名「時刻 (ms)」、縦軸名「ずれ (µs)」）。as001 を開いて送信ジッター → 2 行とも件数 0 で、グラフは NoData「データがありません」。ジッター画面を幅 400 にすると 0x0A0（499 点）の描画計画が列ごとの縦線になる（FR-033、AR-073）

### Implementation for User Story 2

- [X] T022 [US2] `src/can_log_analysis_gui/analysis_window.py` に latency 用と jitter 用の設定を足す（列幅、右寄せ開始列、グラフ: latency は txwait と同じ、jitter は件数 0 → NoData、それ以外 → `set_deviation(row.points, IDS_BUS_AXIS_X, IDS_JIT_AXIS_Y)`）。`src/can_log_analysis_gui/main_window.py` の「受信完了時間」「送信ジッター」を有効にする。T021 を通す

**Checkpoint**: US1 と US2 が動く

---

## Phase 5: User Story 3 - CAN バス負荷を見る (Priority: P2)

**Goal**: 要約・折れ線・ECU 表の画面

**Independent Test**: sample で要約と ECU 表が golden/busload.csv と一致し、折れ線と平均の破線が出る

### Tests for User Story 3（先に書いて失敗を確認する）

- [ ] T023 [P] [US3] `tests/gui/test_analysis_windows.py` に CAN バス負荷のテストを足す（FR-040、FR-041、AR-084）: タイトル・要約（2 行目）・列見出し・ECU 表の全セルが `golden("sample_vehicle_16ecu", "busload")` と一致、列幅 100,140,120、右寄せは 2 列目から、`frameGeometry()` が 960×680（枠を含む）、配置は中身の大きさ（`rect()`）で CBusLoadDlg::LayoutContent の式に合う（要約 22、グラフ = 残り × 3 // 5、表は残り）。グラフは Line（区間 500、平均 = analysis.average_pct、y 目盛り 0〜100）。表の行を選んでもグラフは変わらない。ヘッダだけのログ（tmp に作る）のプロジェクトでは NoData

### Implementation for User Story 3

- [ ] T024 [US3] `src/can_log_analysis_gui/analysis_window.py` に `SummaryGraphListWindow`（要約・グラフ・表の配置、送信 0 なら NoData、それ以外 `set_line(section_pct, section_us, average_pct, IDS_BUS_AXIS_X, IDS_BUS_AXIS_Y)`）を実装し、`src/can_log_analysis_gui/main_window.py` の「CAN バス負荷」を有効にする。T023 を通す

**Checkpoint**: 4 画面がそろう

---

## Phase 6: User Story 4 - 大きなログでも固まらずに待てる・やめられる (Priority: P3)

**Goal**: 0.5 秒後の「解析中」ウィンドウ、進捗、中断、応答性

**Independent Test**: 遅いジョブで「解析中」ウィンドウが出て中断でき、300 万行でも GUI が応答する

### Tests for User Story 4（先に書いて失敗を確認する）

- [ ] T025 [P] [US4] `tests/gui/test_progress.py` を書く（FR-012〜FR-014、contracts/gui.md「解析の実行」）: `can_log_analysis_gui.job` の読み込みを monkeypatch で遅くした（progress を何回か呼ぶ間に sleep する）ジョブで、(1) 0.5 秒を過ぎると `ProgressDialog` が出る（タイトル「解析中」、文言「ログを読み込んでいます...」、バーの最大 1000、値 = done × 1000 // total）、(2) 計算中は「集計しています...」とバー 1000、(3) 「中断」→ 文言「中断しています...」、ボタン無効、ジョブが止まったらダイアログが閉じ、解析画面もメッセージも出ない、(4) Esc・閉じるボタンも中断と同じ、Enter では何も起きない、(5) 0.5 秒以内に終わるジョブではダイアログが出ない、(6) ジョブ中はメインウィンドウが入力を受け付けず、終わったら戻る、(7) ジョブ中（「解析中」ウィンドウが出る前と後の両方）にメインウィンドウの `close()` を呼ぶと、ジョブに中断が指示され、スレッドが止まってから閉じ、開いていた解析画面も閉じる。`QThread` が動いたまま破棄されない（Qt の警告「QThread: Destroyed while thread is still running」が出ない。spec FR-016）
- [ ] T026 [P] [US4] `tests/gui/test_gui_perf.py` を書く（`pytestmark = pytest.mark.perf`、SC-003、SC-004、SC-005）: 機能 001 の `tests/perf/test_large_log.py` と同じ方法で 300 万行のプロジェクトを作る（共通の関数にして両方から使う）。(1) 送信待ち時間を開くまで 60 秒以内。(2) ジョブ中に 100 ms の `QTimer` を動かし、間隔の最大が 0.5 秒未満（GUI が固まらない）。(3) 読み込み中（phase が reading）に中断 → 2 秒以内にダイアログが閉じる。(4) 開いた画面で「全体」の行を選び直してからグラフが変わるまで 0.5 秒以内。結果の数値を出力に残す

### Implementation for User Story 4

- [ ] T027 [US4] `src/can_log_analysis_gui/progress_dialog.py` に `ProgressDialog(QDialog)` を実装する（MFC CAnalysisProgressDlg: モーダル、タイトル・文言・バー 0〜1000・「中断」、50 ms のタイマーでジョブの phase と progress を見て更新、中断で文言を IDS_ANALYZING_CANCEL にしてボタン無効、Enter 無視、Esc／閉じる＝中断、ジョブが終わったら閉じる）。`src/can_log_analysis_gui/main_window.py` の `run_analysis` を MFC RunAnalysis の流れにする: 待ちカーソル（`QApplication.setOverrideCursor`）、メインウィンドウと解析画面を `setEnabled(False)`、0.5 秒の単発タイマーで `ProgressDialog` を出す、ジョブ終了でカーソルと入力を戻す。`MainWindow.closeEvent` で、ジョブがあれば `cancel()` してスレッドの終了を待ち（`QThread.wait()`）、開いている解析画面をすべて閉じてから終わる（spec FR-016、contracts/gui.md「解析の実行」7）。T025 を通し、`pytest -m perf tests/gui/test_gui_perf.py -s` で T026 を通す

**Checkpoint**: 大きなログで使える

---

## Phase 7: User Story 5 - 開けない・読めないときに理由がわかる (Priority: P3)

**Goal**: 未選択・ログなし・ログが読めない・プロジェクトが読めないのメッセージ

**Independent Test**: `tests/data/errors/` のプロジェクトでそれぞれのメッセージが出る

### Tests for User Story 5（先に書いて失敗を確認する）

- [ ] T028 [P] [US5] `tests/gui/test_messages.py` を書く（FR-006、FR-010、FR-015、FR-060a）: 起動直後に「解析 > 送信待ち時間」→ `dialogs` に ("information", IDS_LOG_NONE_NOPROJECT)、ジョブなし。`tests/data/errors/no_log.canprj` を開いて解析 → ("information", IDS_LOG_NONE % "no_log.canprj")。`bad_number.canprj` → ("warning", IDS_LOG_READ_ERROR % <ログのフルパス>)、解析画面なし。sample を開いた後に `bad_project.canprj` を開く → ("warning", IDS_LOAD_ERROR % <理由>)、タイトル・表示・開いている解析画面は sample のまま。起動引数に `bad_project.canprj` → メッセージを出して未選択で起動

### Implementation for User Story 5

- [ ] T029 [US5] `src/can_log_analysis_gui/main_window.py` にメッセージを入れる（contracts/gui.md「解析の実行」2・6、「プロジェクトを開いたとき」）: `run_analysis` の前に未選択・ログなし（`project.log_path` がファイルでない）を確かめる、ジョブの read_error で IDS_LOG_READ_ERROR、`open_project` の `ProjectNotFoundError`／`ProjectReadError` で IDS_LOAD_ERROR（理由は例外の文）を出して状態を変えない。メッセージは `app.show_message` 経由。T028 を通す

**Checkpoint**: すべてのユーザーストーリーが動く

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T030 [P] `can_log_analysis_gui.bat` をリポジトリ直下に作る（ASCII のみ、CRLF。research.md R-6）: `.venv\Scripts\can-log-analysis-gui.exe` が `%~dp0` からの相対で存在しなければ英語のメッセージ（「.venv not found. Create it as in specs/001-log-analysis-core-cli/quickstart.md.」）を出して `pause`、あれば `start "" "%~dp0.venv\Scripts\can-log-analysis-gui.exe" %*`。`.gitattributes` に `*.bat text eol=crlf` を足す。`tests/gui/test_launcher.py` で、バッチが ASCII のみ・CRLF・`%~dp0` と `%*` を含むことを確かめる
- [ ] T031 [P] `tests/unit/test_no_gui_import.py` に、`src/can_log_analysis/` のどのファイルも `can_log_analysis_gui` を import しないことを足す（逆向きの依存の禁止。憲章 原則 II）
- [ ] T032 [P] `CLAUDE.md` を更新する: 機能 002（画面 `src/can_log_analysis_gui/`）の追加、起動方法（`can-log-analysis-gui [PROJECT]`、`can_log_analysis_gui.bat`）、画面のテスト（`pytest tests/gui`、offscreen）、`pip install -e ".[dev]"` で PySide6 も入ること
- [ ] T033 `specs/002-analysis-gui/quickstart.md` の 1・2・4・5 を実行する（2 は起動して目で見る代わりに、offscreen ではなく実際の画面で `can-log-analysis-gui tests\data\sample_vehicle_16ecu\sample_vehicle_16ecu.canprj` を起動できることを確かめ、スクリーンショットを撮れれば撮る）。期待どおりでなければ quickstart.md かコードを直す
- [ ] T034 `specs/002-analysis-gui/VERIFIED.md` を記入欄（確認日、確認者、確認した画面 2 つ以上、MFC 版のビルド（`C:\work\claude\can_simulator` の `git rev-parse --short HEAD`）、表・タイトル・メニュー・グラフの軸の範囲と目盛りの結果、比べた条件（画面の拡大率、両方とも初期サイズのままか））だけで作り、利用者（I.H）に MFC 版との見比べを依頼する（SC-002）。依頼文には「目盛りの数はグラフの横幅で決まるので、両方とも開いたときの大きさのまま、同じ拡大率の画面で比べる」と書く。記入されるまで SC-002 は完了としない
- [ ] T035 `pytest`（機能 001 と 002、golden を含む）が全件成功し、`VERIFIED.md` が記入されていることを確かめる（憲章「品質ゲート」）。未記入なら、その旨を利用者に伝えて完了としない

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 → T002 → T003。T004 → T005（T004 は T001 の後なら並行可）
- **Foundational (Phase 2)**: Setup の後。T006 → T008、T007 → T009、T010 は独立、T011 → T013（T008 の後）、T012 → T014
- **US1 (Phase 3)**: Foundational の後。MVP
- **US2・US3**: US1 の `analysis_window.py`・`main_window.py` に足すので US1 の後。US2 と US3 は同じファイルを触るので順番に
- **US4**: US1 の後（`run_analysis` を差し替える）
- **US5**: US1 の後（`main_window.py`）。US4 と同じファイルなので順番に
- **Polish**: すべての後。T035 は T034 の記入も待つ

### Parallel Opportunities

- T004 と T006・T007（別ファイル）
- Phase 2 のテスト T006・T007・T011・T012
- 各ストーリーのテストタスク（[P]）は、同じファイル `tests/gui/test_analysis_windows.py` に足すもの（T016・T021・T023）を除いて並行可
- T030・T031・T032

---

## Parallel Example: Phase 2

```text
Task: "T006 tests/unit/test_plot.py"
Task: "T007 tests/unit/test_project_contents.py"
Task: "T011 tests/gui/test_graph_plan.py"
Task: "T012 tests/gui/test_job.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1・2（PySide6 の導入、コアの追加、グラフとジョブの土台）
2. Phase 3（メインウィンドウ＋送信待ち時間）
3. **止めて確かめる**: sample を開いて送信待ち時間が golden と一致し、MFC 版の画面（目視確認済み）と同じに見える

### Incremental Delivery

1. US1 → 送信待ち時間（MVP）
2. US2 → 受信完了時間・送信ジッター
3. US3 → CAN バス負荷
4. US4 → 解析中ウィンドウと中断
5. US5 → メッセージ
6. Polish → バッチ、CLAUDE.md、quickstart、MFC との目視確認

---

## Notes

- [P] = 別ファイルで、未完了のタスクに依存しない
- 機能 001 のテスト（golden を含む）は、この機能のどの段階でも通り続けること
- 論理的なまとまりごとにコミットする（コミットは利用者の指示があったときだけ）
