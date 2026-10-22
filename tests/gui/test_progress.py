"""「解析中」ウィンドウと中断、解析中の終了（FR-012〜FR-014、FR-016、contracts/gui.md「解析の実行」、MFC RunAnalysis・CAnalysisProgressDlg）。"""

import time

import pytest
from PySide6.QtCore import Qt

from can_log_analysis.errors import LogReadCancelled
from can_log_analysis_gui import job as job_module
from can_log_analysis_gui import texts

from conftest import DATA_DIR

SAMPLE = DATA_DIR / "sample_vehicle_16ecu" / "sample_vehicle_16ecu.canprj"


@pytest.fixture
def slow_read(monkeypatch):
    """読み込みを約 2 秒かける（0.1 秒ごとに progress を 20 回呼ぶ）。"""
    real = job_module.read_log_records

    def read(path, progress=None):
        for i in range(1, 21):
            time.sleep(0.1)
            if progress is not None and not progress(i * 50, 1000):
                raise LogReadCancelled()
        return real(path, progress=progress)

    monkeypatch.setattr(job_module, "read_log_records", read)


@pytest.fixture
def slow_calc(monkeypatch):
    """計算（送信待ち時間）を約 1.5 秒かける。"""
    real = job_module.KINDS["txwait"]

    def calc(records, name):
        time.sleep(1.5)
        return real(records, name)

    monkeypatch.setitem(job_module.KINDS, "txwait", calc)


def start(main_window, dialogs, kind="txwait", project=SAMPLE):
    dialogs.project_path = project
    main_window.actions["load"].trigger()
    main_window.actions[kind].trigger()


def wait_dialog(qtbot, main_window):
    qtbot.waitUntil(lambda: main_window.progress_dialog is not None and main_window.progress_dialog.isVisible(),
                    timeout=5000)
    return main_window.progress_dialog


def test_dialog_after_half_a_second_while_reading_fr013(qtbot, main_window, dialogs, slow_read):
    start(main_window, dialogs)
    started = time.perf_counter()
    dlg = wait_dialog(qtbot, main_window)
    assert time.perf_counter() - started >= 0.45
    assert dlg.windowTitle() == texts.PROGRESS_TITLE == "解析中"
    assert dlg.isModal()
    assert dlg.label.text() == texts.IDS_ANALYZING_READ
    assert (dlg.bar.minimum(), dlg.bar.maximum()) == (0, 1000)
    assert dlg.stop_button.text() == texts.PROGRESS_STOP
    qtbot.waitUntil(lambda: dlg.bar.value() > 0, timeout=3000)
    done, total = main_window.job.progress()
    assert dlg.bar.value() <= done * 1000 // total
    qtbot.waitUntil(lambda: "txwait" in main_window.windows, timeout=20000)
    assert not dlg.isVisible()


def test_calculating_fr013(qtbot, main_window, dialogs, slow_calc):
    start(main_window, dialogs)
    dlg = wait_dialog(qtbot, main_window)
    qtbot.waitUntil(lambda: dlg.label.text() == texts.IDS_ANALYZING_CALC, timeout=5000)
    assert dlg.bar.value() == 1000
    qtbot.waitUntil(lambda: "txwait" in main_window.windows, timeout=20000)


def test_stop_fr014(qtbot, main_window, dialogs, slow_read):
    start(main_window, dialogs)
    dlg = wait_dialog(qtbot, main_window)
    qtbot.mouseClick(dlg.stop_button, Qt.LeftButton)
    assert dlg.label.text() == texts.IDS_ANALYZING_CANCEL == "中断しています..."
    assert not dlg.stop_button.isEnabled()
    qtbot.waitUntil(lambda: main_window.job is None and not dlg.isVisible(), timeout=5000)
    assert main_window.windows == {}
    assert dialogs.messages == []


def test_escape_stops_and_enter_does_nothing_fr014(qtbot, main_window, dialogs, slow_read):
    start(main_window, dialogs)
    dlg = wait_dialog(qtbot, main_window)
    qtbot.keyClick(dlg, Qt.Key_Return)
    assert dlg.stop_button.isEnabled() and dlg.isVisible()
    qtbot.keyClick(dlg, Qt.Key_Escape)
    assert dlg.label.text() == texts.IDS_ANALYZING_CANCEL
    qtbot.waitUntil(lambda: main_window.job is None, timeout=5000)
    assert main_window.windows == {}


def test_close_button_stops_fr014(qtbot, main_window, dialogs, slow_read):
    start(main_window, dialogs)
    dlg = wait_dialog(qtbot, main_window)
    dlg.close()
    assert dlg.label.text() == texts.IDS_ANALYZING_CANCEL
    qtbot.waitUntil(lambda: main_window.job is None, timeout=5000)
    assert main_window.windows == {}


def test_fast_job_shows_no_dialog_fr013(qtbot, main_window, dialogs, wait_window):
    start(main_window, dialogs, project=DATA_DIR / "as001" / "as001.canprj")
    wait_window(main_window, "txwait")
    qtbot.wait(700)
    assert main_window.progress_dialogs_shown == 0


def test_input_is_blocked_during_the_job(qtbot, main_window, dialogs, slow_read):
    start(main_window, dialogs)
    assert not main_window.isEnabled()
    qtbot.waitUntil(lambda: "txwait" in main_window.windows, timeout=20000)
    assert main_window.isEnabled()


@pytest.mark.parametrize("when", ["before_dialog", "with_dialog"])
def test_closing_the_app_during_a_job_fr016(qtbot, main_window, dialogs, slow_read, when):
    dialogs.project_path = SAMPLE
    main_window.actions["load"].trigger()
    main_window.actions["latency"].trigger()
    job = main_window.job
    if when == "with_dialog":
        wait_dialog(qtbot, main_window)
    main_window.close()
    assert job.cancel_requested()
    assert not job.is_running()  # the thread has stopped before the window closed
    assert main_window.job is None
    assert main_window.windows == {}


def test_closing_the_app_closes_the_analysis_windows_fr016(qtbot, main_window, dialogs, wait_window):
    start(main_window, dialogs, project=DATA_DIR / "as001" / "as001.canprj")
    w = wait_window(main_window, "txwait")
    main_window.close()
    assert not w.isVisible()
