"""MFC 版から作った正解 CSV との文字列一致（SC-001、SC-002、FR-040、憲章 原則 I）。

正解は tools/mfc_golden（reference/mfc/CanSim/LogAnalysis.cpp をそのままビルド）で作る。
合わないときは Python 側を直し、正解 CSV は直さない。
"""

import pytest

from can_log_analysis.cli import main

from conftest import DATA_DIR

LOGS = ["as001", "sample_vehicle_16ecu"]
KINDS = ["latency", "busload", "txwait", "jitter"]


def read_as_is(path):
    # newline="" keeps CR LF as it is, so a line-ending difference is caught too
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("log", LOGS)
def test_matches_mfc_golden(tmp_path, log, kind):
    project = DATA_DIR / log / f"{log}.canprj"
    assert main([str(project), "-a", kind, "-o", str(tmp_path)]) == 0
    # read both as UTF-8 text and compare as they are (no newline or space normalisation)
    actual = read_as_is(tmp_path / f"{kind}.csv")
    expected = read_as_is(DATA_DIR / log / "golden" / f"{kind}.csv")
    if actual != expected:
        a, e = actual.split("\n"), expected.split("\n")
        first = next((i for i in range(max(len(a), len(e))) if i >= len(a) or i >= len(e) or a[i] != e[i]))
        pytest.fail(f"line {first + 1} differs:\n  python: {a[first] if first < len(a) else '<none>'}\n"
                    f"  mfc:    {e[first] if first < len(e) else '<none>'}")
