"""メインウィンドウ（MFC MFCApplication1Dlg のメニュー・RunAnalysis・CloseResultWindows。contracts/gui.md）。"""

from PySide6.QtCore import QSize
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow

from can_log_analysis.project import open_project, read_project_contents
from can_log_analysis_gui import texts
from can_log_analysis_gui.analysis_window import MIN_SIZE, WINDOWS, apply_frame_size
from can_log_analysis_gui.job import AnalysisJob
from can_log_analysis_gui.project_view import ProjectView

INITIAL_SIZE = QSize(900, 600)


class MainWindow(QMainWindow):
    def __init__(self, project=None):
        super().__init__()
        self.setWindowTitle(texts.APP_TITLE)
        self.project = None
        self.contents = None
        self.windows = {}  # kind -> AnalysisWindow (0 or 1 per kind)
        self.job = None
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
        project = open_project(path)
        contents = read_project_contents(project)
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
        if self.job is not None or self.project is None:
            return
        self.job = AnalysisJob(self.project, kind, self)
        self.job.finished.connect(self._on_job_finished)
        self.job.start()

    def _on_job_finished(self, state, result):
        job = self.job
        job.wait()
        self.job = None
        if state == "done":
            analysis, table = result
            self._open_window(job.kind, analysis, table)

    def _open_window(self, kind, analysis, table):
        window = WINDOWS[kind](kind, analysis, table, self)
        window.closed.connect(self._on_window_closed)
        self.windows[kind] = window
        window.show()

    def _on_window_closed(self, kind):
        self.windows.pop(kind, None)
