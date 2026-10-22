"""テスト共通のヘルパ。"""

import os
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


# ---- 画面（機能 002）のテスト用。Qt は fixture の中でだけ import する ----

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # before any QApplication is made


def read_golden(log, kind):
    """tests/data/<log>/golden/<kind>.csv を (title, note, columns, rows) にする。"""
    with open(DATA_DIR / log / "golden" / f"{kind}.csv", encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")[:-1]
    return lines[0], lines[1], lines[2].split(","), [line.split(",") for line in lines[3:]]


@pytest.fixture
def golden():
    return read_golden


class DialogStub:
    """ファイル選択とメッセージを差し替える。選ばせるパスを project_path に入れ、出たメッセージを messages に記録する。"""

    def __init__(self):
        self.project_path = None
        self.start_dirs = []
        self.messages = []  # (icon, text)


@pytest.fixture
def dialogs(monkeypatch):
    from can_log_analysis_gui import app

    stub = DialogStub()

    def ask_project_path(parent, start_dir):
        stub.start_dirs.append(start_dir)
        return None if stub.project_path is None else str(stub.project_path)

    def show_message(parent, icon, text):
        stub.messages.append((icon, text))

    monkeypatch.setattr(app, "ask_project_path", ask_project_path)
    monkeypatch.setattr(app, "show_message", show_message)
    return stub


@pytest.fixture
def main_window(qtbot, dialogs):
    from can_log_analysis_gui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


@pytest.fixture
def wait_window(qtbot):
    """main_window.windows に kind の解析画面ができるまで待ち、それを返す。"""

    def wait(window, kind, timeout=10000):
        qtbot.waitUntil(lambda: kind in window.windows, timeout=timeout)
        return window.windows[kind]

    return wait


# ---- 300 万行のログ（性能テスト用。機能 001 の tests/perf と機能 002 の tests/gui/test_gui_perf.py で共通） ----

LARGE_TIME_COLUMNS = ("Timestamp_us", "Tx_Request", "Tx_Start", "Tx_End", "Rx_Start", "Rx_End", "Rx_Process")


def make_large_project(folder, rows=3_000_000):
    """sample_vehicle_16ecu（16 ECU・31 ID、5 秒分）を時刻を 5 秒ずつずらして繰り返し、rows 行のログを作る。.canprj のパスを返す。"""
    sample = DATA_DIR / "sample_vehicle_16ecu" / "sample_vehicle_16ecu.canprj.log.csv"
    lines = sample.read_text(encoding="utf-8").splitlines()
    header = lines[0]
    names = header.split(",")
    time_index = [names.index(n) for n in LARGE_TIME_COLUMNS]
    sample_rows = [line.split(",") for line in lines[1:] if line]
    project = Path(folder) / "large.canprj"
    project.write_text("[Project]\nEcuCount=16\n", encoding="utf-8")
    written = 0
    with open(str(project) + ".log.csv", "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "\n")
        repeat = 0
        while written < rows:
            shift = repeat * 5_000_000
            out = []
            for cells in sample_rows[:rows - written]:
                cells = list(cells)
                for i in time_index:
                    if cells[i]:
                        cells[i] = str(int(cells[i]) + shift)
                out.append(",".join(cells))
            f.write("\n".join(out) + "\n")
            written += len(out)
            repeat += 1
    return project