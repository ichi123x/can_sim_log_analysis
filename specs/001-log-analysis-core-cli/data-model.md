# Data Model: CANログ解析コアとコマンドライン

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-22

MFC 版 `reference/mfc/CanSim/LogAnalysis.h` の構造体と 1 対 1 に対応させる（右端の列）。
時刻・時間はすべて µs の整数。名前は Python の流儀（snake_case）にする。

## Project（.canprj）

| 属性 | 型 | 説明 |
|---|---|---|
| path | Path | .canprj のパス |
| name | str | パスの最後の `\` または `/` より後ろ（拡張子付き）。表題に使う。MFC `ProjectFileName()` |
| log_path | Path | `str(path) + ".log.csv"`。MFC `LogPathFor` |

- 検査: path が存在し、UTF-8 の INI として読めること。値は検査しない（research R-9）。

## LogRecords（ログ行の集まり） ↔ `std::vector<LogRecord>`

1 行 1 オブジェクトにせず、列ごとの整数配列で持つ（research R-3）。i 番目の要素が i 番目のデータ行。

| 列 | 型 | 空欄のとき | 対応 |
|---|---|---|---|
| can_id | array('q') | （エラー） | `LogRecord::CanId` |
| tx_node | array('q') | 0 | `TxNode` |
| rx_node | array('q') | 0 | `RxNode` |
| tx_request | array('q') | −1 | `TxRequestUs` |
| tx_start | array('q') | −1 | `TxStartUs` |
| tx_end | array('q') | −1 | `TxEndUs` |
| rx_end | array('q') | −1 | `RxEndUs` |
| status | bytearray | （エラー） | `Status`（0 = SUCCESS、1 = ARBITRATION_LOST_RETRY、2 = OVERWRITE） |

- `len(records)` はデータ行の数（空行は含まない）。
- 読み込みの規則とエラーは [contracts/core-api.md](contracts/core-api.md) の `read_log_records`。

## Transmission（1 回の送信） ↔ `Transmission`

| 属性 | 型 |
|---|---|
| can_id | int |
| tx_node | int |
| tx_request | int |
| tx_start | int |

- 送信待ち時間・ジッタ用。OVERWRITE でなく、tx_request ≥ 0 かつ tx_start ≥ 0 の行から、キー (can_id, tx_start, tx_node) が
  最初に出た行で作る。(can_id, tx_start, tx_node) の昇順に並べる（research R-5）。
- バス負荷は別のまとめ方（キー (tx_node, can_id, tx_start)、条件 tx_start ≥ 0 かつ tx_end > tx_start）を使う。

## Stats（統計行の共通部分） ↔ `ComputeStats` の出力

| 属性 | 型 | 規則 |
|---|---|---|
| count | int | 値の件数 |
| min_us / max_us | int | 件数 0 なら 0 |
| mean_us | float | `float(sum) / count`、件数 0 なら 0.0 |
| p95_us | int | 昇順の `(count * 95 + 99) // 100` 番目（1 始まり）、件数 0 なら 0 |
| values | array('q') | 昇順に並べた値（ヒストグラム用）。メモリのため `list[int]` にしない（research R-3） |

## LatencyRow / LatencyAnalysis ↔ `LatencyRow` / `LatencyAnalysis`

| 属性 | 型 | 説明 |
|---|---|---|
| LatencyRow.tx_node, rx_node | int | 「全体」の行は 0 / 0 |
| LatencyRow.stats | Stats | |
| LatencyAnalysis.rows | list[LatencyRow] | [0] = 全体、続いて (tx_node, rx_node) 昇順 |
| LatencyAnalysis.overwrite_count | int | OVERWRITE の行数 |

## TxWaitRow / TxWaitAnalysis ↔ `TxWaitRow` / `TxWaitAnalysis`

| 属性 | 型 | 説明 |
|---|---|---|
| TxWaitRow.is_all | bool | 「全体」の行 |
| TxWaitRow.can_id, tx_node | int | tx_node はその ID の最初の送信（送信開始が最も早い）の送信ノード |
| TxWaitRow.stats | Stats | |
| TxWaitAnalysis.rows | list[TxWaitRow] | [0] = 全体、続いて can_id 昇順 |
| TxWaitAnalysis.overwrite_count | int | |

## JitterPoint / JitterRow / JitterAnalysis ↔ 同名

| 属性 | 型 | 説明 |
|---|---|---|
| JitterPoint.time_us | int | 後の送信の tx_start |
| JitterPoint.deviation_us | int | (start[k] − start[k−1]) − (request[k] − request[k−1]) |
| JitterRow.can_id, tx_node | int | |
| JitterRow.period_us | int | 送信要求の間隔の最頻値（同数なら小さいほう）。送信 1 回なら 0 |
| JitterRow.count | int | 送信回数 − 1 |
| JitterRow.min_us, max_us | int | count 0 なら 0 |
| JitterRow.std_dev_us | float | 母標準偏差（加算の順は research R-4）。count 0 なら 0.0 |
| JitterRow.points | list[JitterPoint] | 時刻順 |
| JitterAnalysis.rows | list[JitterRow] | can_id 昇順 |

## BusLoadAnalysis / EcuBusUsage ↔ 同名

| 属性 | 型 | 説明 |
|---|---|---|
| section_us | int | 10000 固定 |
| range_us | int | 送信がなければ 10000、あれば ceil(最後の tx_end / 10000) × 10000 |
| section_pct | list[float] | 区間ごとの `100.0 * busy / section_us` |
| average_pct | float | `100.0 * total / range_us` |
| max_pct / max_section | float / int | 最大の負荷率と、それが最初に現れた区間（0 始まり）。全部 0 なら 0.0 / 0 |
| ecus | list[EcuBusUsage] | 送信したノードだけ、ノード番号順 |
| transmission_count | int | まとめた送信の数 |
| EcuBusUsage.node, frame_count, busy_us | int | |
| EcuBusUsage.usage_pct | float | `100.0 * busy_us / range_us` |

## Histogram ↔ `Histogram`

| 属性 | 型 | 説明 |
|---|---|---|
| start_us | int | ビン 0 の左端 |
| width_us | int | 1・2・5 × 10^m（≥ 1） |
| counts | list[int] | ビン i は [start + i·width, start + (i+1)·width)。値がなければ空 |

## Table（出力の共通形）

| 属性 | 型 | 説明 |
|---|---|---|
| kind | str | `latency` / `busload` / `txwait` / `jitter`（出力ファイル名にも使う） |
| title | str | 例 `受信完了時間 - sample_vehicle_16ecu.canprj` |
| note | str | 注記（バス負荷は要約 1 行） |
| columns | list[str] | 列見出し |
| rows | list[list[str]] | セルの文字列（空欄は `""`） |

- セルに `,`・`"`・CR・LF を含んではならない（含めば書き出し時にエラー。contracts/table-csv.md）。
- 解析結果 → Table の変換規則（書式文字列、空欄の条件）は [contracts/table-csv.md](contracts/table-csv.md)。

## 関係

```text
Project ──log_path──▶ LogRecords ──┬─▶ LatencyAnalysis ─▶ Table(latency)
                                    ├─▶ BusLoadAnalysis ─▶ Table(busload)
                                    └─▶ Transmission[] ─┬─▶ TxWaitAnalysis ─▶ Table(txwait)
                                                         └─▶ JitterAnalysis ─▶ Table(jitter)
Stats.values ─▶ Histogram（画面機能が使う）
```
