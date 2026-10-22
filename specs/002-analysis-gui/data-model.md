# Data Model: CANログ解析ツールの画面

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-22

機能 001 の型（`Project`、`LogRecords`、各 `*Analysis`、`Table`、`Histogram`。[001 data-model](../001-log-analysis-core-cli/data-model.md)）はそのまま使う。
ここではこの機能で足すものだけを書く。

## 解析コアに足すもの（Qt に依存しない）

### ProjectContents（`can_log_analysis.project.read_project_contents`）

メインウィンドウの表示用（FR-004）。.canprj に項目がない・数値でないときは `None`（画面では空欄）。

| 属性 | 型 | .canprj |
|---|---|---|
| bit_rate_bps | int \| None | [Network] BitRateBps |
| ecu_count | int \| None | [Project] EcuCount |
| duration_sec | int \| None | [Project] DurationSec |
| ecus | list[EcuInfo] | [NodeN]（N の昇順） |
| frames | list[FrameInfo] | [NodeN.FrameM]（N、M の昇順） |

| EcuInfo | 型 | .canprj |
|---|---|---|
| section_no | int | [NodeN] の N |
| node_id | int \| None | NodeId |
| name | str | Name（なければ ""） |
| label | str | Label（なければ ""） |
| rx_filter | str \| None | RxFilter（なければ None = 全受信） |
| receive_delay_us, power_on_time_us, init_duration_us | int \| None | ReceiveDelayUs、PowerOnTimeUs、InitDurationUs |

| FrameInfo | 型 | .canprj |
|---|---|---|
| node_section_no | int | [NodeN.FrameM] の N |
| frame_no | int | M |
| name | str | Name |
| can_id | int \| None | CanId（`0x` 付き 16 進） |
| dlc | int \| None | Dlc |
| period_us, initial_offset_us | int \| None | PeriodUs、InitialOffsetUs |

- 送信 ECU の表示名は、同じ N の EcuInfo の `ECU %02d`（NodeId）と Name から作る（画面側）。
- 表示の書式（ms、kbps）は contracts/gui.md「メインウィンドウ」。

### plot.py（MFC LogAnalysis.cpp のグラフ用の関数と AnalysisDlg.cpp の目盛りの関数）

| 関数 | 対応 | 説明 |
|---|---|---|
| `nice_ticks(lo, hi, approx_count) -> list[float]` | NiceTicks | lo〜hi を 1・2・5 × 10^m の刻みで約 approx_count 区間。hi ≤ lo なら [lo] |
| `ticks_from_zero(hi, approx_count)` | TicksFromZero（AnalysisDlg.cpp） | 0 から hi 以上まで |
| `ticks_covering(lo, hi, approx_count)` | TicksCovering（同） | lo〜hi を覆うように両端を 1 刻み延ばす |
| `format_tick(value) -> str` | FormatTick（同） | 整数なら `%.0f`、それ以外は `%g` |
| `min_max_per_column(points, t0, t1, columns) -> list[ColumnRange]` | MinMaxPerColumn | 列 c = (time − t0) × columns ÷ span（整数除算、0〜columns−1 に丸める） |
| `max_per_column(values, columns) -> list[float]` | MaxPerColumn | 値が列より多いとき列ごとの最大 |

| ColumnRange | 型 |
|---|---|
| has | bool |
| min_us, max_us | int |

## 画面（`can_log_analysis_gui`）

### AppState（メインウィンドウが持つ）

| 属性 | 型 | 説明 |
|---|---|---|
| project | Project \| None | 開いているプロジェクト。未選択は None |
| contents | ProjectContents \| None | 表示用 |
| windows | dict[kind, AnalysisWindow] | 開いている解析画面。kind は `txwait`／`latency`／`jitter`／`busload`。種類ごとに 0 か 1 |
| job | AnalysisJob \| None | 実行中のジョブ（同時に 1 つ） |

- プロジェクトを開いたら windows をすべて閉じて空にする（FR-005）。読めなければ project・contents は前のまま（FR-006）。

### AnalysisJob（状態遷移）

```text
reading ──(読み込み完了)──▶ calculating ──(計算完了)──▶ done
   │                            │
   ├──(読み込みエラー)──▶ read_error
   └──(中断: progress が False)──▶ cancelled ◀──(中断指示あり・計算完了)──┘
```

| 属性 | 型 | 説明 |
|---|---|---|
| kind | str | 解析の種類 |
| phase | reading / calculating | 「解析中」ウィンドウの文言とバー |
| done_bytes, total_bytes | int | 読み込みの進捗 |
| cancel_requested | bool | 「中断」で True。progress が False を返す |
| result | (Analysis, Table) \| None | done のとき |

- 結果: done → 解析画面を開く。cancelled → 何も出さない。read_error → IDS_LOG_READ_ERROR。

### AnalysisWindow

| 属性 | 型 | 説明 |
|---|---|---|
| kind | str | |
| analysis | 機能 001 の *Analysis | 解析結果 |
| table | Table | 表・注記・タイトル（Table.title） |
| selected_row | int | 選んでいる行（開いたとき 0。バス負荷は選択でグラフが変わらない） |
| histogram_cache | dict[int, Histogram] | 行ごとのヒストグラム（R-5） |

### GraphContent（グラフウィジェットに渡す内容。MFC CAnalysisGraph の Mode）

| 種類 | 内容 |
|---|---|
| NoData | 文言（「データがありません」） |
| Bars | Histogram、横軸名、縦軸名 |
| Deviation | list[JitterPoint]、横軸名、縦軸名 |
| Line | 区間ごとの負荷率、区間幅 µs、平均 %、横軸名、縦軸名 |

- 描画計画（テスト用）: プロット領域、x・y の範囲、目盛りの値と文字、データの図形（棒の矩形、点・線、列ごとの縦線、平均線）。
  プロット領域はウィジェットの矩形から左 70・上 32・右 20・下 46（96 dpi 換算）を除いたもの（MFC と同じ）。
