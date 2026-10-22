"""300 万行のログでの画面の応答性・中断・開くまでの時間（SC-003、SC-004、SC-005、research.md R-3）。

`pytest -m perf` のときだけ実行する。ログは機能 001 の性能テストと同じ作り方（conftest.make_large_project）。
"""

import time

import pytest
from PySide6.QtCore import Qt, QTimer

from conftest import make_large_project

pytestmark = pytest.mark.perf


@pytest.fixture(scope="module")
def large_project(tmp_path_factory):
    return make_large_project(tmp_path_factory.mktemp("guiperf"))


def open_project(main_window, dialogs, project):
    dialogs.project_path = project
    main_window.actions["load"].trigger()


def test_opens_within_a_minute_and_stays_responsive_sc003_sc004(qtbot, main_window, dialogs, large_project):
    open_project(main_window, dialogs, large_project)
    ticks = []

    def tick():
        job = main_window.job
        ticks.append((time.perf_counter(), job.phase() if job is not None else "-"))

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(100)
    started = time.perf_counter()
    main_window.actions["txwait"].trigger()
    qtbot.waitUntil(lambda: "txwait" in main_window.windows, timeout=90000)
    elapsed = time.perf_counter() - started
    timer.stop()
    gaps = sorted(((b - a, phase) for (a, _), (b, phase) in zip(ticks, ticks[1:])), reverse=True)
    print(f"\nopened in {elapsed:.1f} s, timer ticks {len(ticks)}, largest gaps "
          f"{[(round(g, 2), p) for g, p in gaps[:5]]}")
    assert elapsed < 60.0
    # SC-003 asks for 0.5 s; the 100 ms timer is kept within about 0.2 s (sorting per CAN ID, freeing big lists in
    # parts, no cyclic GC during the job). 0.3 s leaves room for the machine's own hiccups.
    assert gaps[0][0] < 0.3


def test_stop_while_reading_within_two_seconds_sc003(qtbot, main_window, dialogs, large_project):
    open_project(main_window, dialogs, large_project)
    main_window.actions["jitter"].trigger()
    qtbot.waitUntil(lambda: main_window.progress_dialog is not None and main_window.progress_dialog.isVisible(),
                    timeout=5000)
    dlg = main_window.progress_dialog
    qtbot.waitUntil(lambda: main_window.job.progress()[0] > 0, timeout=5000)
    assert main_window.job.phase() == "reading"
    started = time.perf_counter()
    qtbot.mouseClick(dlg.stop_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: main_window.job is None and not dlg.isVisible(), timeout=10000)
    elapsed = time.perf_counter() - started
    print(f"\nstopped in {elapsed:.2f} s")
    assert elapsed < 2.0
    assert main_window.windows == {}


def test_graph_of_the_largest_row_within_half_a_second_sc005(qtbot, main_window, dialogs, large_project):
    open_project(main_window, dialogs, large_project)
    main_window.actions["latency"].trigger()
    qtbot.waitUntil(lambda: "latency" in main_window.windows, timeout=90000)
    w = main_window.windows["latency"]
    w._histograms.clear()  # measure the first drawing of the all row, not the cached one
    w.table_widget.selectRow(1)
    started = time.perf_counter()
    w.table_widget.selectRow(0)
    w.graph.repaint()
    elapsed = time.perf_counter() - started
    print(f"\nall row ({w.analysis.rows[0].stats.count} values) in {elapsed:.3f} s")
    assert elapsed < 0.5
