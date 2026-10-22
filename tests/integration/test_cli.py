"""コマンドライン（FR-001、FR-037、FR-038、contracts/cli.md、AS-001）。"""

import subprocess
import sys

from can_log_analysis.cli import main

from conftest import DATA_DIR

AS001 = DATA_DIR / "as001" / "as001.canprj"
GOLDEN = DATA_DIR / "as001" / "golden"


def golden(kind):
    return (GOLDEN / f"{kind}.csv").read_text(encoding="utf-8")


def test_stdout_in_menu_order_fr037(capsys):
    # the order of the MFC "解析" menu (MFCApplication1.rc IDR_MAINMENU), not the order of -a
    assert main([str(AS001), "-a", "latency", "-a", "txwait"]) == 0
    out = capsys.readouterr()
    assert out.out == golden("txwait") + "\n" + golden("latency")
    assert out.err == ""


def test_one_analysis(capsys):
    assert main([str(AS001), "--analysis", "txwait"]) == 0
    assert capsys.readouterr().out == golden("txwait")


def test_output_dir_writes_only_the_chosen_tables(tmp_path, capsys):
    out_dir = tmp_path / "out" / "nested"
    assert main([str(AS001), "-a", "latency", "-a", "txwait", "-o", str(out_dir)]) == 0
    assert sorted(p.name for p in out_dir.iterdir()) == ["latency.csv", "txwait.csv"]
    for kind in ("latency", "txwait"):
        assert (out_dir / f"{kind}.csv").read_bytes() == (GOLDEN / f"{kind}.csv").read_bytes()
    assert capsys.readouterr().out == ""


def test_jitter_comes_before_busload(capsys):
    assert main([str(AS001), "-a", "busload", "-a", "jitter"]) == 0
    assert capsys.readouterr().out == golden("jitter") + "\n" + golden("busload")


def test_all_four_in_menu_order(capsys):
    assert main([str(AS001)]) == 0
    expected = "\n".join(golden(kind) for kind in ("txwait", "latency", "jitter", "busload"))
    assert capsys.readouterr().out == expected


def test_all_with_output_dir(tmp_path):
    assert main([str(AS001), "-a", "busload", "-a", "all", "-o", str(tmp_path)]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["busload.csv", "jitter.csv", "latency.csv", "txwait.csv"]


def test_python_m_gives_the_same_utf8_output():
    result = subprocess.run(
        [sys.executable, "-m", "can_log_analysis", str(AS001), "-a", "latency", "-a", "txwait"],
        capture_output=True, check=False)
    assert result.returncode == 0
    assert result.stdout.decode("utf-8") == golden("txwait") + "\n" + golden("latency")
    assert b"\r" not in result.stdout
