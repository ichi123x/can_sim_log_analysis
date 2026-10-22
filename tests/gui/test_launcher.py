"""ダブルクリック用のバッチファイル（FR-060b、research.md R-6）。"""

from pathlib import Path

BAT = Path(__file__).parents[2] / "can_log_analysis_gui.bat"


def test_batch_file_is_ascii_with_crlf():
    data = BAT.read_bytes()
    assert all(b < 128 for b in data)  # cmd reads it in the console code page
    assert b"\r\n" in data and data.count(b"\n") == data.count(b"\r\n")


def test_batch_file_starts_the_gui_from_the_repository_venv():
    text = BAT.read_text(encoding="ascii")
    assert '"%~dp0.venv\\Scripts\\can-log-analysis-gui.exe" %*' in text  # relative to the batch file; passes a dropped .canprj
    assert 'start ""' in text  # detached, so the console window closes at once
    assert "pause" in text  # the message stays when .venv is missing
