"""コマンドラインの進捗・--quiet・Ctrl+C（FR-042〜FR-044、contracts/cli.md「進捗」、research.md R-12）。"""

import io
import itertools

import pytest

from can_log_analysis import cli
from can_log_analysis.cli import main

from conftest import DATA_DIR

AS001 = DATA_DIR / "as001" / "as001.canprj"
GOLDEN = DATA_DIR / "as001" / "golden"
READ = "ログを読み込んでいます... "
CALC = "集計しています..."


@pytest.fixture
def slow(monkeypatch):
    """Every call of the clock is one second later, so the 0.5 s limit is always exceeded."""
    monkeypatch.setattr(cli, "_now", itertools.count(1.0, 1.0).__next__)


@pytest.fixture
def fast(monkeypatch):
    monkeypatch.setattr(cli, "_now", lambda: 0.0)


def golden_all():
    return "\n".join((GOLDEN / f"{k}.csv").read_text(encoding="utf-8") for k in ("txwait", "latency", "jitter", "busload"))


def test_progress_after_half_a_second_fr042(capsys, slow):
    assert main([str(AS001)]) == 0
    out = capsys.readouterr()
    assert out.err == f"{READ}100%\n{CALC}\n"
    assert out.out == golden_all()  # no progress in the tables (FR-043)


def test_no_progress_within_half_a_second_fr042(capsys, fast):
    assert main([str(AS001)]) == 0
    out = capsys.readouterr()
    assert out.err == ""
    assert out.out == golden_all()


def test_quiet_fr043(capsys, slow):
    assert main([str(AS001), "--quiet"]) == 0
    assert capsys.readouterr().err == ""
    assert main([str(AS001), "-q"]) == 0
    assert capsys.readouterr().err == ""


def test_output_files_have_no_progress_fr043(capsys, slow, tmp_path):
    assert main([str(AS001), "-o", str(tmp_path)]) == 0
    assert capsys.readouterr().err == f"{READ}100%\n{CALC}\n"
    for k in ("latency", "busload", "txwait", "jitter"):
        assert (tmp_path / f"{k}.csv").read_bytes() == (GOLDEN / f"{k}.csv").read_bytes()


def test_same_percent_is_not_repeated(slow):
    err = io.StringIO()
    progress = cli._Progress(err, start=0.0)
    for done in (10, 10, 20, 21, 1000):
        assert progress.read(done, 1000) is True
    assert err.getvalue() == f"{READ}1%\n{READ}2%\n{READ}100%\n"


def test_terminal_overwrites_the_line(slow):
    class Tty(io.StringIO):
        def isatty(self):
            return True

    err = Tty()
    progress = cli._Progress(err, start=0.0)
    progress.read(500, 1000)
    progress.read(1000, 1000)
    progress.calc()
    progress.end()
    assert err.getvalue() == f"\r{READ}50%\r{READ}100%\n{CALC}\n"


def test_empty_log_counts_as_100_percent(slow):
    err = io.StringIO()
    cli._Progress(err, start=0.0).read(0, 0)
    assert err.getvalue() == f"{READ}100%\n"


def test_ctrl_c_while_reading_fr044(capsys, monkeypatch, tmp_path, fast):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "read_log_records", interrupted)
    out_dir = tmp_path / "out"
    assert main([str(AS001), "-o", str(out_dir)]) == 130
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err.splitlines()[-1] == "中断しました。"
    assert not out_dir.exists()


def test_ctrl_c_while_calculating_fr044(capsys, monkeypatch, tmp_path, slow):
    def interrupted(records, name):
        raise KeyboardInterrupt

    monkeypatch.setitem(cli._KINDS, "jitter", interrupted)
    out_dir = tmp_path / "out"
    assert main([str(AS001), "-o", str(out_dir)]) == 130
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err == f"{READ}100%\n{CALC}\n中断しました。\n"
    assert not out_dir.exists()


def test_ctrl_c_without_output_dir_prints_no_table(capsys, monkeypatch, fast):
    def interrupted(records, name):
        raise KeyboardInterrupt

    monkeypatch.setitem(cli._KINDS, "txwait", interrupted)
    assert main([str(AS001)]) == 130
    assert capsys.readouterr().out == ""
