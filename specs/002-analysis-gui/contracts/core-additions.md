# Contract: 解析コア（can_log_analysis）への追加

機能 001 の [core-api.md](../../001-log-analysis-core-cli/contracts/core-api.md) に足す関数。どれも Qt に依存しない（test_no_gui_import の対象）。
機能 001 のテスト（golden を含む）はそのまま通ること。

## can_log_analysis.plot（MFC の目盛り・間引き。research R-2）

```python
def nice_ticks(lo: float, hi: float, approx_count: int) -> list[float]        # MFC NiceTicks
def ticks_from_zero(hi: float, approx_count: int) -> list[float]              # AnalysisDlg.cpp TicksFromZero
def ticks_covering(lo: float, hi: float, approx_count: int) -> list[float]    # AnalysisDlg.cpp TicksCovering
def format_tick(value: float) -> str                                          # AnalysisDlg.cpp FormatTick
def min_max_per_column(points: Sequence[JitterPoint], t0: int, t1: int, columns: int) -> list[ColumnRange]  # MinMaxPerColumn
def max_per_column(values: Sequence[float], columns: int) -> list[float]      # MaxPerColumn
```

- 計算は MFC と同じ式・同じ許容（1e-9）・同じ整数除算。`nice_ticks` の刻みは `stats.nice_ceil` を使う。
- `format_tick`: `abs(v - round(v)) < 1e-9` なら `"%.0f" % v`、それ以外は `"%g" % v`（C の printf と同じ結果）。

## can_log_analysis.project.read_project_contents（research R-7）

```python
def read_project_contents(project: Project) -> ProjectContents
```

- `open_project` と同じ読み方（configparser、UTF-8、interpolation なし）。読めなければ `ProjectReadError`。
- セクション `[NodeN]`、`[NodeN.FrameM]`（N、M は 10 進の整数）を番号順に集める。キー名は大文字小文字を区別しない（configparser の既定）。
- 値が数値として読めないときは None（エラーにしない）。CanId は `0x`／`0X` 付きの 16 進。
- 解析の計算には使わない（元仕様 AR-003）。

## can_log_analysis.stats.make_histogram（高速化。research R-5）

- 入出力は変えない。各ビンの件数を `bisect.bisect_left` でビンの境目を探して数える（値は昇順）。
- 機能 001 の test_histogram と golden がそのまま通ることで結果が変わらないことを確かめる。
