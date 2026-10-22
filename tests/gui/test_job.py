"""解析ジョブ（FR-012〜FR-015、data-model.md「AnalysisJob」、research.md R-3）。"""

import threading

from can_log_analysis.analysis import TxWaitAnalysis
from can_log_analysis.project import open_project
from can_log_analysis_gui import job as job_module
from can_log_analysis_gui.job import AnalysisJob

from conftest import DATA_DIR

AS001 = DATA_DIR / "as001" / "as001.canprj"


def run(qtbot, job):
    with qtbot.waitSignal(job.finished, timeout=10000) as blocker:
        job.start()
    job.wait()
    return blocker.args


def test_done_with_the_table(qtbot, golden):
    job = AnalysisJob(open_project(AS001), "txwait")
    state, result = run(qtbot, job)
    assert state == "done"
    analysis, table = result
    assert isinstance(analysis, TxWaitAnalysis)
    title, note, columns, rows = golden("as001", "txwait")
    assert (table.title, table.note, table.columns, table.rows) == (title, note, columns, rows)
    assert job.phase() == "calculating"
    done, total = job.progress()
    assert done == total > 0


def test_runs_off_the_gui_thread(qtbot, monkeypatch):
    seen = []
    real = job_module.KINDS["latency"]

    def recording(records, name):
        seen.append(threading.get_ident())
        return real(records, name)

    monkeypatch.setitem(job_module.KINDS, "latency", recording)
    state, _ = run(qtbot, AnalysisJob(open_project(AS001), "latency"))
    assert state == "done"
    assert seen and seen[0] != threading.get_ident()


def test_cancel_before_reading(qtbot):
    job = AnalysisJob(open_project(AS001), "txwait")
    job.cancel()
    state, result = run(qtbot, job)
    assert (state, result) == ("cancelled", None)


def test_cancel_while_calculating_waits_for_the_calculation(qtbot, monkeypatch):
    job = AnalysisJob(open_project(AS001), "jitter")
    real = job_module.KINDS["jitter"]
    calculated = []

    def cancelled_meanwhile(records, name):
        job.cancel()
        result = real(records, name)
        calculated.append(True)
        return result

    monkeypatch.setitem(job_module.KINDS, "jitter", cancelled_meanwhile)
    state, result = run(qtbot, job)
    assert calculated == [True]
    assert (state, result) == ("cancelled", None)


def test_read_error(qtbot):
    job = AnalysisJob(open_project(DATA_DIR / "errors" / "bad_number.canprj"), "txwait")
    state, result = run(qtbot, job)
    assert state == "read_error"
    assert result.endswith("bad_number.canprj.log.csv: line 5: bad number")
