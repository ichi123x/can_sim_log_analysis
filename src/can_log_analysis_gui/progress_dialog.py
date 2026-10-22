"""「解析中」ウィンドウ（MFC CAnalysisProgressDlg、IDD_ANALYSIS_PROGRESS。contracts/gui.md「解析の実行」4）。

モーダル。50 ms ごとにジョブの段階と進捗を見て、文言とバー（0〜1000）を更新する。
「中断」・Esc・閉じるボタンで中断を指示する（止まるまで閉じない）。Enter では何もしない。
ジョブが終わったらメインウィンドウが finish() で閉じる。
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from can_log_analysis_gui import texts
from can_log_analysis_gui.analysis_window import dialog_font


class ProgressDialog(QDialog):
    def __init__(self, job, parent=None):
        super().__init__(parent)
        self.setWindowTitle(texts.PROGRESS_TITLE)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setModal(True)
        self.setFont(dialog_font())
        self._job = job
        self._finished = False
        self._stopping = False
        self._phase = None

        self.label = QLabel(texts.IDS_ANALYZING_READ)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.stop_button = QPushButton(texts.PROGRESS_STOP)
        self.stop_button.setAutoDefault(False)
        self.stop_button.setDefault(False)
        self.stop_button.clicked.connect(self.stop)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.stop_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.bar)
        layout.addLayout(buttons)
        self.setFixedWidth(330)  # IDD_ANALYSIS_PROGRESS is 220 dialog units wide

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(50)
        self.refresh()

    def refresh(self):
        if self._stopping:
            return  # "中断しています..." stays until the job has stopped
        phase = self._job.phase()
        if phase != self._phase:
            self._phase = phase
            self.label.setText(texts.IDS_ANALYZING_READ if phase == "reading" else texts.IDS_ANALYZING_CALC)
        if phase == "reading":
            done, total = self._job.progress()
            self.bar.setValue(done * 1000 // total if total > 0 else 0)
        else:
            self.bar.setValue(1000)

    def stop(self):
        if self._stopping:
            return
        self._stopping = True
        self._job.cancel()
        self.label.setText(texts.IDS_ANALYZING_CANCEL)
        self.stop_button.setEnabled(False)

    def finish(self):
        """ジョブが終わった（どの結果でも）。"""
        self._finished = True
        self._timer.stop()
        super().done(0)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.accept()  # Enter does nothing (MFC OnOK)
            return
        if event.key() == Qt.Key_Escape:
            self.stop()  # Esc asks the job to stop (MFC OnCancel)
            event.accept()
            return
        super().keyPressEvent(event)

    def reject(self):
        self.stop()  # stays open until the job has stopped

    def closeEvent(self, event):
        if self._finished:
            event.accept()
            return
        self.stop()
        event.ignore()
