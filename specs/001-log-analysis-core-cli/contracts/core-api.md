# Contract: 解析コアの公開 API（パッケージ `can_log_analysis`）

画面機能（次の機能）とコマンドラインとテストが使う関数。GUI ライブラリを import してはならない（FR-039）。
型は [data-model.md](../data-model.md)。右端は対応する MFC の関数。

## プロジェクト

```python
def open_project(path: str | os.PathLike) -> Project
```

- path がなければ `ProjectNotFoundError`、UTF-8 の INI として読めなければ `ProjectReadError`。
- ログの有無は調べない（`read_log_records` が `LogNotFoundError` を出す）。— MFC `LogPathFor`、`ProjectFileName`

## ログの読み込み

```python
ProgressCallback = Callable[[int, int], bool]   # (読んだバイト数, 全体のバイト数) -> 続けるなら True

def read_log_records(path: str | os.PathLike,
                     progress: ProgressCallback | None = None) -> LogRecords
```

MFC `ReadLogRecords` と同じ規則:

1. ファイルがなければ `LogNotFoundError`、開けなければ `LogReadError("cannot open the file")`、
   読み込み中の I/O エラーは `LogReadError("cannot read the file")`。
2. 4 MB ずつ読み、`\n` で行に分ける。最後の行に `\n` がなくても読む。行番号は 1 から数え、空行も 1 行と数える。
3. 行末の `\r` を 1 つだけ除く。
4. 1 行目はヘッダ。`,` で分けた名前に `CAN_ID`, `Tx_Node`, `Rx_Node`, `Tx_Request`, `Tx_Start`, `Tx_End`, `Rx_End`, `Status`
   が完全一致で含まれること（前後の空白は除かない）。この順で探し、最初に見つからなかった名前で
   `LogReadError("line 1: no column <名前>")`。
5. 2 行目以降: 空行は飛ばす。`,` で分けたセルの数が「使う列の位置の最大 + 1」より少なければ `line N: too few columns`。
6. CAN_ID は `0x` または `0X` に 16 進数字 1 文字以上が続くこと。でなければ `line N: bad CAN_ID`。
7. Tx_Node, Rx_Node, Tx_Request, Tx_Start, Tx_End, Rx_End は、空なら既定値（0, 0, −1, −1, −1, −1）。
   空でなければ「先頭に `+` か `-` が 1 つあってもよく、残りが 1 文字以上の ASCII 数字だけ」であること。でなければ `line N: bad number`。
8. Status は `SUCCESS`、`ARBITRATION_LOST_RETRY`、`OVERWRITE` のどれか（完全一致）。でなければ `line N: bad Status`。
9. 検査の順は CAN_ID → 6 つの数値（Tx_Node から Rx_End の順）→ Status。最初の誤りで止める。
10. ファイルが空（1 行もない）なら `line 1: no header`。
11. `progress` は 4 MB 読むごと（最後の塊を除く）と、読み終えたときに 1 回呼ぶ。False を返したら `LogReadCancelled` を出す。

例外はすべて `CanLogAnalysisError` を基底とする。`LogReadError.message` は MFC と同じ英文（`line N: ...` 等）。

## 解析

```python
def analyze_latency(records: LogRecords) -> LatencyAnalysis      # MFC AnalyzeLatency
def analyze_tx_wait(records: LogRecords) -> TxWaitAnalysis       # MFC AnalyzeTxWait
def analyze_jitter(records: LogRecords) -> JitterAnalysis        # MFC AnalyzeJitter
def analyze_bus_load(records: LogRecords) -> BusLoadAnalysis     # MFC AnalyzeBusLoad
def collect_transmissions(records: LogRecords) -> tuple[list[Transmission], int]  # (送信, OVERWRITE 行数)  MFC CollectTransmissions
def make_histogram(sorted_values: Sequence[int]) -> Histogram    # MFC MakeHistogram（Stats.values の array('q') をそのまま渡せる）
```

- 定義は spec の FR-010〜FR-035 と research R-4、R-5。
- どの関数も records を変更しない。例外を出さない（入力は `read_log_records` で検査済み）。

## 表への変換

```python
def latency_table(a: LatencyAnalysis, project_name: str) -> Table
def bus_load_table(a: BusLoadAnalysis, project_name: str) -> Table
def tx_wait_table(a: TxWaitAnalysis, project_name: str) -> Table
def jitter_table(a: JitterAnalysis, project_name: str) -> Table

def ecu_name(node: int) -> str          # "ECU %02d"
def can_id_text(can_id: int) -> str     # "0x%03X"
def fixed1(value: float) -> str         # "%.1f"
def period_text(period_us: int) -> str  # 整数 ms か "%.3f"

def write_table_csv(table: Table, out: TextIO) -> None
```

- 書式と文言は [table-csv.md](table-csv.md)。画面機能も同じ関数でセル文字列を作る（FR-039）。

## グラフの間引き（AR-073、AR-084 の `MinMaxPerColumn`、`MaxPerColumn`、`NiceTicks`）

本機能では作らない。画面機能で追加する。
