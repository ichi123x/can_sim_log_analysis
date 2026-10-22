"""起動（FR-060a、contracts/gui.md「起動」）と、テストで差し替えるダイアログ。

can-log-analysis-gui [PROJECT]   /   python -m can_log_analysis_gui [PROJECT]
"""

import sys

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from can_log_analysis_gui import texts


def ask_project_path(parent, start_dir: str) -> str | None:
    """「プロジェクト読込み」のファイル選択。選ばなければ None。"""
    path, _ = QFileDialog.getOpenFileName(parent, texts.MENU_LOAD_PROJECT.replace("(&O)...", ""), start_dir,
                                          texts.qt_project_filter())
    return path or None


def show_message(parent, icon: str, text: str):
    """icon は "information" か "warning"（MFC MB_ICONINFORMATION / MB_ICONWARNING）。"""
    box = QMessageBox.information if icon == "information" else QMessageBox.warning
    box(parent, texts.APP_TITLE, text)


def main(argv=None) -> int:
    from can_log_analysis_gui.main_window import MainWindow

    args = sys.argv[1:] if argv is None else list(argv)
    app = QApplication.instance() or QApplication([sys.argv[0]] if sys.argv else ["can-log-analysis-gui"])
    window = MainWindow(project=args[0] if args else None)
    window.show()
    return app.exec()
