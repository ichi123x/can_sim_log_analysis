"""メインウィンドウ（MFC MFCApplication1Dlg のメニュー・RunAnalysis・CloseResultWindows。contracts/gui.md）。"""

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow

from can_log_analysis.errors import ProjectNotFoundError, ProjectReadError
from can_log_analysis.project import open_project, read_project_contents
from can_log_analysis_gui import texts
from can_log_analysis_gui.analysis_window import MIN_SIZE, WINDOWS, apply_frame_size
from can_log_analysis_gui.job import AnalysisJob
from can_log_analysis_gui.progress_dialog import ProgressDialog
from can_log_analysis_gui.project_view import ProjectView

INITIAL_SIZE = QSize(900, 600)
PROGRESS_AFTER_MS = 500  # MFC RunAnalysis: job.wait_for(500 ms) before CAnalysisProgressDlg


class MainWindow(QMainWindow):
    def __init__(self, project=None):
        super().__init__()
        self.setWindowTitle(texts.APP_TITLE)
        self.project = None
        self.contents = None
        self.windows = {}  # kind -> AnalysisWindow (0 or 1 per kind)
        self.job = None
        self.progress_dialog = None
        self.progress_dialogs_shown = 0
        self._progress_timer = QTimer(self)
        self._progress_timer.setSingleShot(True)
        self._progress_timer.timeout.connect(self._show_progress)
        self._last_dir = ""
        self._sized = False
        self.actions = {}
        self._make_menus()
        self.project_view = ProjectView(self)
        self.setCentralWidget(self.project_view)
        if project is not None:
            self.open_project(project)

    def _make_menus(self):
        bar = self.menuBar()
        file_menu = bar.addMenu(texts.MENU_FILE)
        self.actions["load"] = self._action(file_menu, texts.MENU_LOAD_PROJECT, self.ask_and_open_project)
        self.actions["load"].setShortcut(QKeySequence.Open)
        file_menu.addSeparator()
        self.actions["exit"] = self._action(file_menu, texts.MENU_EXIT, self.close)
        analysis_menu = bar.addMenu(texts.MENU_ANALYSIS)
        for kind, text in (("txwait", texts.MENU_TXWAIT), ("latency", texts.MENU_LATENCY),
                           ("jitter", texts.MENU_JITTER)):
            self.actions[kind] = self._action(analysis_menu, text, lambda checked=False, k=kind: self.run_analysis(k))
        analysis_menu.addSeparator()
        self.actions["busload"] = self._action(analysis_menu, texts.MENU_BUSLOAD,
                                               lambda checked=False: self.run_analysis("busload"))

    def _action(self, menu, text, slot) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def showEvent(self, event):
        super().showEvent(event)
        if not self._sized:
            self._sized = True
            apply_frame_size(self, INITIAL_SIZE, MIN_SIZE)

    # ---- project ----

    def ask_and_open_project(self):
        from can_log_analysis_gui import app  # replaceable dialogs (tests)

        path = app.ask_project_path(self, self._last_dir)
        if path:
            self.open_project(path)

    def open_project(self, path) -> bool:
        """読めなければ IDS_LOAD_ERROR を出し、それまでのプロジェクトと解析画面をそのまま残す（FR-006）。"""
        try:
            project = open_project(path)
            contents = read_project_contents(project)
        except ProjectNotFoundError as e:
            self._message("warning", texts.IDS_LOAD_ERROR % f"ファイルがありません: {e.path}")
            return False
        except ProjectReadError as e:
            self._message("warning", texts.IDS_LOAD_ERROR % e)
            return False
        self.close_analysis_windows()
        self.project = project
        self.contents = contents
        self._last_dir = str(project.path.parent)
        self.project_view.show_project(project, contents)
        self.setWindowTitle(f"{texts.APP_TITLE} - {project.name}")
        return True

    def close_analysis_windows(self):
        """MFC CloseResultWindows: プロジェクトが変わったら解析画面をすべて閉じる。"""
        for window in list(self.windows.values()):
            window.close()
        self.windows.clear()

    # ---- analysis ----

    def run_analysis(self, kind: str):
        window = self.windows.get(kind)
        if window is not None:
            window.raise_()
            window.activateWindow()
            return
        if self.job is not None:
            return
        # MFC RunAnalysis: the same notices as "ログ表示 > シミュレーションログ"
        if self.project is None:
            self._message("information", texts.IDS_LOG_NONE_NOPROJECT)
            return
        if not self.project.log_path.is_file():
            self._message("information", texts.IDS_LOG_NONE % self.project.name)
            return
        self.job = AnalysisJob(self.project, kind, self)
        self.job.finished.connect(self._on_job_finished)
        self._begin_wait()
        self.job.start()
        self._progress_timer.start(PROGRESS_AFTER_MS)

    def _begin_wait(self):
        # MFC: CWaitCursor and the main thread waiting; nothing else can be done meanwhile
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.setEnabled(False)  # also disables the analysis windows (children of this window)

    def _end_wait(self):
        self._progress_timer.stop()
        if self.progress_dialog is not None:
            self.progress_dialog.finish()
            self.progress_dialog = None
        self.setEnabled(True)
        QApplication.restoreOverrideCursor()

    def _show_progress(self):
        if self.job is None:
            return
        # no parent: a child of this (disabled) window would be disabled too; centred on this window instead
        dialog = ProgressDialog(self.job)
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.adjustSize()
        rect = dialog.frameGeometry()
        rect.moveCenter(self.frameGeometry().center())
        dialog.move(rect.topLeft())
        self.progress_dialog = dialog
        self.progress_dialogs_shown += 1
        dialog.show()

    def _on_job_finished(self, state, result):
        job = self.job
        if job is None or self.sender() is not job:
            return  # a job given up when the window was closed
        job.wait()
        self.job = None
        self._end_wait()
        if state == "done":
            analysis, table = result
            self._open_window(job.kind, analysis, table)
        elif state == "read_error":
            # MFC shows the log path only, not the line (the CLI shows it: can-log-analysis PROJECT)
            self._message("warning", texts.IDS_LOG_READ_ERROR % job.project.log_path)
        # cancelled: no window and no message (MFC)

    def _message(self, icon, text):
        from can_log_analysis_gui import app  # replaceable dialogs (tests)

        app.show_message(self, icon, text)

    def closeEvent(self, event):
        """MFC と同じく解析中は閉じられない（入力を受け付けない）が、閉じる要求が届いたら中断して止まるのを待つ（FR-016）。"""
        job = self.job
        if job is not None:
            job.cancel()
            job.wait()  # at most one calculation (about 3 s for 3 million rows)
            self.job = None
            self._end_wait()
        self.close_analysis_windows()  # MFC OnDestroy: CloseResultWindows
        super().closeEvent(event)

    def _open_window(self, kind, analysis, table):
        window = WINDOWS[kind](kind, analysis, table, self)
        window.closed.connect(self._on_window_closed)
        self.windows[kind] = window
        window.show()

    def _on_window_closed(self, kind):
        self.windows.pop(kind, None)
