# Research: CANログ解析ツールの画面

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-22

## R-1 画面のライブラリとバージョン

- **Decision**: PySide6 6.8 以上（2026-10-22 時点の最新は 6.12.0）。テストは pytest-qt 4.5、画面なしの環境では `QT_QPA_PLATFORM=offscreen`。
  pyproject の `[project.optional-dependencies]` に `gui = ["PySide6>=6.8"]` を足し、`dev` に `pytest-qt` と PySide6 を足す。
  解析コア（`can_log_analysis`）の実行時の依存は標準ライブラリのままにする（機能 001 の R-11、test_no_gui_import）。
- **Rationale**: 憲章「技術的制約」で PySide6 と決めている。6.8 以上は Python 3.12 に対応し、高 DPI の扱い（96 dpi 換算の座標を自動で拡大）が既定で有効なので、
  MFC の `MulDiv(v, dpi, 96)` と同じ効果を Qt の論理座標で得られる。
- **Alternatives considered**: tkinter（表とグラフの見た目・高 DPI が弱い）、PyQt6（ライセンスが GPL/商用で、憲章は PySide6）。

## R-2 グラフの描き方（matplotlib か、自前の描画か）

- **Decision**: matplotlib は使わず、Qt の描画（`QPainter`）で MFC の `CAnalysisGraph::Draw` と同じ手順で描く自前のウィジェットにする。
  目盛り・間引きの計算（MFC `NiceTicks`、`MinMaxPerColumn`、`MaxPerColumn`、`TicksFromZero`、`TicksCovering`、`FormatTick`）は
  Qt に依存しない純粋な関数として解析コア側の新しいモジュール `can_log_analysis/plot.py` に置き、単体テストする。
- **Rationale**:
  - spec FR-050〜FR-052 は、目盛りの刻み・軸の範囲・間引き方を MFC と同じにすることを求める。matplotlib は自分の目盛り決定（AutoLocator）を持ち、
    MFC の NiceTicks と同じにするには結局すべて手で与えることになる。
  - 間引きは「グラフの横幅（ピクセル）1 列ごとの最小〜最大」（MFC MinMaxPerColumn）で、描画先のピクセル幅を知っている自前の描画のほうが素直。
  - 300 万行のログでも描くのは列の数（せいぜい数千）だけなので速い。matplotlib の依存（numpy を含む）も増やさずに済む。
  - 憲章は matplotlib を「想定ライブラリ」として挙げているが必須ではない。依存を足さない方向の変更なので、plan に理由を書けば足りる（憲章「技術的制約」）。
- **Alternatives considered**: matplotlib（上記の理由）、pyqtgraph（目盛りの規則が違い、依存も増える）。

## R-3 解析を画面とは別に動かす方法と、中断（実測付き）

- **Decision**: 解析ジョブ（読み込み＋選んだ 1 つの解析）は `QThread` 上の作業オブジェクトで動かし、結果は Qt のシグナルで GUI スレッドに返す。
  進捗は `read_log_records` の `progress` で受け取り、中断は `progress` が False を返すことで行う（機能 001 FR-007 の `LogReadCancelled`）。
  計算中の中断は MFC と同じく、計算が終わったところで結果を捨てる（計算の途中では止めない）。
- **実測**（2026-10-22、開発 PC、300 万行・305 MB、機能 001 の解析コア）:
  読み込み 7.1 秒（progress の呼び出し 73 回、間隔は最長 0.13 秒）、計算は送信待ち時間 2.1 秒・受信完了時間 1.0 秒・送信ジッター 2.9 秒・CAN バス負荷 0.9 秒。
  → 読み込み中の中断は 0.2 秒以内に効く。計算中の中断は最長約 3 秒待つ。spec SC-003 をこの実測に合わせて直した。
- **応答性**: 解析コアは純粋な Python なので GIL を持ち続けるが、CPython は 5 ms ごと（`sys.getswitchinterval()`）にスレッドを切り替えるので、
  GUI スレッドの再描画・入力処理は止まらない。SC-003 の「0.5 秒以内に再描画」は、解析中に GUI スレッドのタイマーが遅れないことをテストで確かめる。
- **Alternatives considered**: `multiprocessing`（計算も途中で止められるが、300 万行の結果を親プロセスへ渡す費用が大きく、MFC の動きとも違う）、
  解析関数に中断の確認を足す（機能 001 のコアの変更になり、MFC にない動き）。

## R-4 「解析中」ウィンドウを出すまでの 0.5 秒

- **Decision**: ジョブを始めたら待ちカーソル（`QApplication.setOverrideCursor(Qt.WaitCursor)`）にし、メインウィンドウと解析画面の入力を受け付けない状態にして
  0.5 秒の単発タイマーを動かす。0.5 秒以内に終われば「解析中」ウィンドウは出さない。過ぎたらモーダルの「解析中」ウィンドウを出す。
  「解析中」ウィンドウは 50 ms ごと（MFC と同じ）にジョブの状態（段階、読んだバイト数、全体）を見て、文言とバーを更新する。
- **Rationale**: MFC `RunAnalysis` は `job.wait_for(500 ms)` の間 `CWaitCursor` で待ち、その後 `CAnalysisProgressDlg::DoModal`。
  Qt では GUI スレッドを止めずに同じ見え方を作る。
- 文言（`MFCApplication1.rc`）: ウィンドウタイトル「解析中」、IDS_ANALYZING_READ「ログを読み込んでいます...」、IDS_ANALYZING_CALC「集計しています...」、
  IDS_ANALYZING_CANCEL「中断しています...」、ボタン「中断」。バーは 0〜1000（読み込み中は done × 1000 / total、計算中は 1000）。

## R-5 ヒストグラムを速く作る（行を選んでからグラフが変わるまで）

- **Decision**: 機能 001 の `make_histogram` の結果は変えずに、各ビンの件数を `bisect` で数える形に直す（値は昇順に並んでいる前提が既にある）。
  さらに画面側で、行ごとのヒストグラムを最初に作ったときに覚えておく。
- **Rationale**: 300 万件の「全体」行で、今の 1 件ずつ数える方法は約 0.5 秒かかる見込みで、SC-005（0.5 秒以内）にぎりぎり。
  ビンは最大 50 本なので、ビンの境目を二分探索すれば件数は O(50 log n) で出る。結果が同じことは機能 001 の test_histogram と golden で確かめる。
- **Alternatives considered**: numpy.histogram（依存が増え、ビンの端の扱いが MFC と違う）。

## R-6 起動方法とダブルクリック

- **Decision**:
  - `[project.gui-scripts]` に `can-log-analysis-gui = "can_log_analysis_gui.app:main"`。pip が `.venv\Scripts\can-log-analysis-gui.exe` を作る。
    gui-scripts の exe はコンソールを開かない（pythonw と同じ）。`python -m can_log_analysis_gui [PROJECT]` でも起動できる。
  - ダブルクリック用にリポジトリ直下に `can_log_analysis_gui.bat` を置く: `@start "" "%~dp0.venv\Scripts\can-log-analysis-gui.exe" %*`。
    `start` で GUI を切り離すので、バッチのコンソールはすぐ閉じる（一瞬だけ見える）。.canprj をこのバッチにドラッグ＆ドロップすると、そのプロジェクトで起動する。
  - `.venv` がないときはバッチがその旨を出して止まる（quickstart の環境作成へ案内）。
- **Rationale**: spec FR-060a・b（Q2 = B）。.lnk ショートカットは絶対パスを持つのでリポジトリに入れても他の PC で使えない。バッチは相対パス（`%~dp0`）で動く。
- **Alternatives considered**: .lnk を作る PowerShell スクリプト（デスクトップに作れて便利だが、ファイルが 1 つ増えるだけで必須ではない。要望があれば追加）、
  VBScript で完全にコンソールを隠す（Windows で VBScript が段階的に廃止予定）。

## R-7 メインウィンドウの .canprj 表示の書式

- **Decision**: MFC 版の表示に合わせる。
  - 時間（周期、初回オフセット、受信処理遅延、電源投入時刻、初期化時間）は ms で、MFC `FormatMs`（FrameEditDlg.cpp）と同じ:
    整数 ms なら整数、そうでなければ小数 3 桁。列見出しは MFC の IDS_FRAME_COL_*（「No.」「フレーム名」「ID」「DLC」「初回オフセット(ms)」「送信周期(ms)」）に合わせ、
    ECU 一覧と送信 ECU の列は本ツールで名前を決める（MFC は独自描画で列見出しがない）。
  - CAN ID は `0x%03X`、通信速度は MFC SettingsDlg の表記（125 kbps、250 kbps、500 kbps、1 Mbps。それ以外は「<値> bps」）。
  - シミュレーション時間は「<DurationSec> s」。受信フィルタは書かれたとおり（なければ「全受信」）。
- **読み方**: 機能 001 の `open_project` の INI の読み方（configparser、UTF-8）を広げ、`[NodeN]` と `[NodeN.FrameM]` を番号順に並べる。
  値が数値でなければその欄を空欄にする（FR-004e）。この読み取りは表示専用で、解析の計算には使わない（元仕様 AR-003）。
  解析コアの `project.py` に `read_project_contents(project) -> ProjectContents` として足す（Qt に依存しない、単体テストできる）。

## R-8 メッセージの文言とウィンドウタイトル

- **Decision**（すべて `MFCApplication1.rc` のまま）:
  - プロジェクト未選択で解析: IDS_LOG_NONE_NOPROJECT（2 文、情報アイコン）。
  - ログなし: IDS_LOG_NONE（プロジェクトのファイル名入り、2 文、情報アイコン）。
  - ログが読めない: IDS_LOG_READ_ERROR「シミュレーションログを読み込めませんでした。\n<ログのパス>」（警告アイコン）。
  - プロジェクトが読めない: IDS_LOAD_ERROR「プロジェクトを読み込めませんでした。現在の内容は変更していません。\n\n<理由>」（警告アイコン）。
  - ファイル選択の絞り込み: IDS_PROJECT_FILTER（「CAN プロジェクト (*.canprj)」「すべてのファイル (*.*)」）。
  - グラフ: IDS_ANALYSIS_NO_DATA「データがありません」、IDS_LAT_AXIS_X「時間 (µs)」、IDS_LAT_AXIS_Y「件数」、IDS_BUS_AXIS_X「時刻 (ms)」、
    IDS_BUS_AXIS_Y「負荷 (%)」、IDS_JIT_AXIS_Y「ずれ (µs)」、IDS_BUS_AVERAGE「平均」。
  - メニューは IDR_MAINMENU の表示名（アクセスキー付き）。「ファイル > 終了(X)」は本ツールで足す。
- **メインウィンドウのタイトル**: 「CAN ログ解析」、プロジェクトを開いたら「CAN ログ解析 - <ファイル名>」（MFC は「CAN Bus Simulator」で、解析ツールには当たらないため本ツールで決める）。
- 文言は画面のモジュールに .rc からコピーした定数として持ち、機能 001 と同じく、テストで .rc を読んで一致を確かめる。

## R-9 画面のテスト

- **Decision**: pytest-qt（`qtbot`）で、メニュー、プロジェクトの読み込み、解析画面の表の全セル（golden CSV と比較）、行の選択とグラフの切り替え、
  同じ解析の再選択、Esc／Enter、プロジェクトを開き直したときに解析画面が閉じること、「解析中」ウィンドウと中断、メッセージの文言を確かめる。
  メッセージボックスとファイル選択ダイアログは、画面側で差し替えられる関数（例 `app.ask_project_path`、`app.show_message`）を通して呼び、テストで置き換える。
  グラフは描画結果の画像ではなく、描く前に計算する「描画計画」（軸の範囲、目盛り、棒・点・列の座標）をテストする（`plot.py` と、グラフウィジェットの計画を返すメソッド）。
  300 万行での応答性と中断は `-m perf` のテストにする。
- **Rationale**: 画像の比較はフォントや DPI で変わり壊れやすい。MFC と同じであるべきなのは数値（目盛りと範囲と間引き）なので、そこを直接確かめる。

## R-10 機能 001 との境界

- **Decision**: 画面は新しいパッケージ `can_log_analysis_gui` にし、解析コア `can_log_analysis` を import する。逆向きの import はしない（test_no_gui_import が守る）。
  解析コアへの追加は 3 つだけ: `plot.py`（目盛り・間引き、R-2）、`project.py` の `read_project_contents`（R-7）、`make_histogram` の高速化（R-5、結果は不変）。
  いずれも Qt に依存せず、機能 001 のテスト（golden を含む）がそのまま通ること。
