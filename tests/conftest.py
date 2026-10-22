"""テスト共通のヘルパ。"""

from pathlib import Path

import pytest

DEFAULT_HEADER = (
    "Timestamp_us,CAN_ID,DLC,Tx_Node,Rx_Node,Tx_Request,Tx_Start,Tx_End,"
    "Rx_Start,Rx_End,Rx_Process,Bus_Load_Pct,Status,Retry_Count,Update_Count"
)

DATA_DIR = Path(__file__).parent / "data"


def write_text(path: Path, text: str) -> None:
    """UTF-8（BOM なし）・LF で書く。"""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


@pytest.fixture
def make_project(tmp_path):
    """ログの行から .canprj と .log.csv を作り、.canprj のパスを返す。"""

    def make(rows, header=DEFAULT_HEADER, name="t.canprj"):
        project = tmp_path / name
        write_text(project, "[Project]\nEcuCount=1\n")
        lines = ([header] if header is not None else []) + list(rows)
        write_text(Path(str(project) + ".log.csv"), "".join(line + "\n" for line in lines))
        return project

    return make


def log_row(can_id="0x080", tx=1, rx=2, req=0, start=0, end=246, rx_end=246, status="SUCCESS"):
    """既定のヘッダに合わせたログの 1 行を作る（使わない列は適当な値）。"""
    return f"{rx_end},{can_id},8,{tx},{rx},{req},{start},{end},{start},{rx_end},{rx_end},0.0,{status},0,0"
