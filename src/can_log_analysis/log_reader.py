"""フレームログ <.canprj のパス>.log.csv の読み込み（MFC ReadLogRecords。FR-004〜FR-007）。

読み方とエラーの文言・行番号は MFC と同じにする（contracts/core-api.md「ログの読み込み」）。
300 万行でも 1 行 1 オブジェクトにせず、列ごとの整数配列に詰める（research.md R-3）。
"""

import os
import re
from array import array
from collections.abc import Callable
from pathlib import Path

from can_log_analysis.errors import LogNotFoundError, LogReadCancelled, LogReadError

SUCCESS = 0
RETRY_SUCCESS = 1  # ARBITRATION_LOST_RETRY
OVERWRITE = 2

_STATUS = {b"SUCCESS": SUCCESS, b"ARBITRATION_LOST_RETRY": RETRY_SUCCESS, b"OVERWRITE": OVERWRITE}
_COLUMNS = (b"CAN_ID", b"Tx_Node", b"Rx_Node", b"Tx_Request", b"Tx_Start", b"Tx_End", b"Rx_End", b"Status")
_CAN_ID = re.compile(rb"0[xX][0-9A-Fa-f]+")
_CHUNK = 4 * 1024 * 1024

ProgressCallback = Callable[[int, int], bool]


class LogRecords:
    """ログのデータ行。i 番目の要素が i 番目のデータ行（MFC std::vector<LogRecord>）。"""

    __slots__ = ("can_id", "tx_node", "rx_node", "tx_request", "tx_start", "tx_end", "rx_end", "status")

    def __init__(self):
        self.can_id = array("q")
        self.tx_node = array("q")
        self.rx_node = array("q")
        self.tx_request = array("q")
        self.tx_start = array("q")
        self.tx_end = array("q")
        self.rx_end = array("q")
        self.status = bytearray()  # SUCCESS / RETRY_SUCCESS / OVERWRITE

    def __len__(self):
        return len(self.status)


def _split_header(line: bytes) -> list[bytes]:
    # MFC SplitCsv (std::getline on ','): an empty line has no cells
    return line.split(b",") if line else []


def _is_number(cell: bytes) -> bool:
    digits = cell[1:] if cell[:1] in (b"+", b"-") else cell
    return bool(digits) and digits.isdigit()


def read_log_records(path: str | os.PathLike, progress: ProgressCallback | None = None) -> LogRecords:
    path = Path(path)
    if not path.is_file():
        raise LogNotFoundError(path)
    try:
        f = open(path, "rb")
    except OSError as e:
        raise LogReadError(path, "cannot open the file") from e
    with f:
        try:
            total = os.fstat(f.fileno()).st_size
        except OSError as e:
            raise LogReadError(path, "cannot open the file") from e
        return _read(f, path, total, progress)


def _read(f, path: Path, total: int, progress: ProgressCallback | None) -> LogRecords:
    records = LogRecords()
    can_id, tx_node, rx_node = records.can_id, records.tx_node, records.rx_node
    tx_request, tx_start, tx_end, rx_end = records.tx_request, records.tx_start, records.tx_end, records.rx_end
    status = records.status
    status_of = _STATUS.get
    can_id_match = _CAN_ID.fullmatch

    columns = None  # positions of _COLUMNS once the header is read
    needed = 0
    line_no = 0
    kept = b""
    bytes_read = 0

    def fail(message):
        raise LogReadError(path, message)

    while True:
        try:
            chunk = f.read(_CHUNK)
        except OSError as e:
            raise LogReadError(path, "cannot read the file") from e
        bytes_read += len(chunk)
        at_end = len(chunk) < _CHUNK
        data = kept + chunk
        lines = data.split(b"\n")
        # the last piece has no line break yet; at the end of the file it is a last line without one
        kept = lines.pop()
        if at_end and kept:
            lines.append(kept)
            kept = b""
        for line in lines:
            line_no += 1
            if line.endswith(b"\r"):
                line = line[:-1]
            if columns is None:
                header = _split_header(line)
                columns = []
                for name in _COLUMNS:
                    if name not in header:
                        fail(f"line 1: no column {name.decode()}")
                    columns.append(header.index(name))
                needed = max(columns) + 1
                c_id, c_tx, c_rx, c_req, c_start, c_end, c_rx_end, c_status = columns
                continue
            if not line:
                continue  # an empty line is skipped
            cells = line.split(b",")
            if len(cells) < needed:
                fail(f"line {line_no}: too few columns")
            cell = cells[c_id]
            if not can_id_match(cell):
                fail(f"line {line_no}: bad CAN_ID")
            values = []
            for index, empty in ((c_tx, 0), (c_rx, 0), (c_req, -1), (c_start, -1), (c_end, -1), (c_rx_end, -1)):
                cell = cells[index]
                if not cell:
                    values.append(empty)
                elif _is_number(cell):
                    values.append(int(cell))
                else:
                    fail(f"line {line_no}: bad number")
            s = status_of(cells[c_status])
            if s is None:
                fail(f"line {line_no}: bad Status")
            can_id.append(int(cells[c_id][2:], 16))
            tx_node.append(values[0])
            rx_node.append(values[1])
            tx_request.append(values[2])
            tx_start.append(values[3])
            tx_end.append(values[4])
            rx_end.append(values[5])
            status.append(s)
        if at_end:
            break
        # after every 4 MB but the last piece, then once at the end (MFC ReadLogRecords)
        if progress is not None and not progress(bytes_read, total):
            raise LogReadCancelled()
    if progress is not None and not progress(bytes_read, total):
        raise LogReadCancelled()
    if columns is None:
        fail("line 1: no header")
    return records
