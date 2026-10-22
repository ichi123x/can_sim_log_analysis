"""300 万行のログでの時間とメモリ（SC-003、plan.md Constraints、tasks.md T059）。

`pytest -m perf` のときだけ実行する。時間とメモリは別々のテスト・別々のプロセスで測る。
ログは sample_vehicle_16ecu（16 ECU・31 ID、5 秒分）を時刻をずらして繰り返し、約 300 万行にする。
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest

from conftest import DATA_DIR

pytestmark = pytest.mark.perf

ROWS = 3_000_000
TIME_LIMIT_S = 60.0
MEMORY_LIMIT = 1024 ** 3
SAMPLE = DATA_DIR / "sample_vehicle_16ecu" / "sample_vehicle_16ecu.canprj.log.csv"
SHIFT_US = 5_000_000  # the sample covers 5 s
TIME_COLUMNS = ("Timestamp_us", "Tx_Request", "Tx_Start", "Tx_End", "Rx_Start", "Rx_End", "Rx_Process")


@pytest.fixture(scope="module")
def large_project(tmp_path_factory):
    lines = SAMPLE.read_text(encoding="utf-8").splitlines()
    header = lines[0]
    names = header.split(",")
    time_index = [names.index(n) for n in TIME_COLUMNS]
    rows = [line.split(",") for line in lines[1:] if line]
    folder = tmp_path_factory.mktemp("perf")
    project = folder / "large.canprj"
    project.write_text("[Project]\nEcuCount=16\n", encoding="utf-8")
    written = 0
    with open(str(project) + ".log.csv", "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "\n")
        repeat = 0
        while written < ROWS:
            shift = repeat * SHIFT_US
            out = []
            for cells in rows[:ROWS - written]:
                cells = list(cells)
                for i in time_index:
                    if cells[i]:
                        cells[i] = str(int(cells[i]) + shift)
                out.append(",".join(cells))
            f.write("\n".join(out) + "\n")
            written += len(out)
            repeat += 1
    return project


def test_time_within_a_minute(large_project, tmp_path):
    size_mb = Path(str(large_project) + ".log.csv").stat().st_size / 1e6
    started = time.perf_counter()
    result = subprocess.run([sys.executable, "-m", "can_log_analysis", str(large_project), "-o", str(tmp_path), "-q"],
                            capture_output=True, check=False)
    elapsed = time.perf_counter() - started
    print(f"\n{ROWS} rows, {size_mb:.0f} MB: {elapsed:.1f} s")
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["busload.csv", "jitter.csv", "latency.csv", "txwait.csv"]
    assert elapsed < TIME_LIMIT_S


def test_peak_memory_below_1gb(large_project, tmp_path):
    probe = Path(__file__).with_name("memory_probe.py")
    result = subprocess.run([sys.executable, str(probe), str(large_project), str(tmp_path)],
                            capture_output=True, check=False)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    peak = int(result.stdout.decode().strip())
    print(f"\npeak working set: {peak / 1024 ** 2:.0f} MiB")
    assert peak < MEMORY_LIMIT
