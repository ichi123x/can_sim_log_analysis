"""解析ジョブ: ログの読み込みと 1 つの解析を QThread で動かす（MFC RunAnalysis の std::async 部分。research.md R-3）。

状態: reading → calculating → done／cancelled／read_error。中断は読み込み中なら progress が False を返して止め、
計算中は MFC と同じく計算が終わってから結果を捨てる。
"""

import threading

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot

from can_log_analysis.analysis import analyze_bus_load, analyze_jitter, analyze_latency, analyze_tx_wait
from can_log_analysis.errors import LogNotFoundError, LogReadCancelled, LogReadError
from can_log_analysis.log_reader import read_log_records
from can_log_analysis.tables import bus_load_table, jitter_table, latency_table, tx_wait_table


def _make(analyze, table):
    def run(records, project_name):
        analysis = analyze(records)
        return analysis, table(analysis, project_name)

    return run


# kind -> (records, project name) -> (analysis, Table)
KINDS = {
    "txwait": _make(analyze_tx_wait, tx_wait_table),
    "latency": _make(analyze_latency, latency_table),
    "jitter": _make(analyze_jitter, jitter_table),
    "busload": _make(analyze_bus_load, bus_load_table),
}


class _Worker(QObject):
    finished = Signal(str, object)

    def __init__(self, job):
        super().__init__()
        self._job = job

    @Slot()
    def run(self):
        state, result = self._job._run()
        self.finished.emit(state, result)


class AnalysisJob(QObject):
    """1 回の「解析」メニュー選択。finished(state, result) を GUI スレッドに出す。
    result は done なら (Analysis, Table)、read_error ならメッセージ（"<ログのパス>: line N: ..."）、それ以外は None。"""

    finished = Signal(str, object)

    def __init__(self, project, kind: str, parent=None):
        super().__init__(parent)
        self.project = project
        self.kind = kind
        self._lock = threading.Lock()
        self._phase = "reading"
        self._done = 0
        self._total = 0
        self._cancel = False
        self._thread = None
        self._worker = None
        self.state = None

    # ---- read from the GUI thread ----

    def phase(self) -> str:
        with self._lock:
            return self._phase

    def progress(self) -> tuple[int, int]:
        with self._lock:
            return self._done, self._total

    def cancel_requested(self) -> bool:
        with self._lock:
            return self._cancel

    def cancel(self):
        with self._lock:
            self._cancel = True

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def start(self):
        self._thread = QThread()
        self._worker = _Worker(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)  # queued: arrives on the GUI thread
        # direct: the worker thread stops its own event loop at once, so the GUI thread can wait() for it
        # in _on_finished (a queued quit would wait for the GUI thread and deadlock)
        self._worker.finished.connect(self._thread.quit, Qt.DirectConnection)
        self._thread.start()

    def wait(self, ms: int = -1) -> bool:
        """スレッドが止まるまで待つ。"""
        if self._thread is None:
            return True
        return self._thread.wait() if ms < 0 else self._thread.wait(ms)

    @Slot(str, object)
    def _on_finished(self, state, result):
        self.state = state
        self.finished.emit(state, result)

    # ---- on the worker thread ----

    def _progress(self, done: int, total: int) -> bool:
        with self._lock:
            self._done = done
            self._total = total
            return not self._cancel

    def _run(self):
        try:
            records = read_log_records(self.project.log_path, progress=self._progress)
        except LogReadCancelled:
            return "cancelled", None
        except (LogReadError, LogNotFoundError) as e:
            message = e.message if isinstance(e, LogReadError) else "cannot open the file"
            return "read_error", f"{self.project.log_path}: {message}"
        with self._lock:
            self._phase = "calculating"
        result = KINDS[self.kind](records, self.project.name)
        if self.cancel_requested():
            return "cancelled", None
        return "done", result
