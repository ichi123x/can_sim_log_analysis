"""解析画面（MFC AnalysisDlg.cpp の CAnalysisDlgBase と CTxWaitDlg ほか。contracts/gui.md「解析画面」）。

表の列見出し・セルは機能 001 の Table をそのまま表示する（FR-024、FR-025）。
大きさは MFC と同じく枠を含めたウィンドウ全体（FR-022）。配置は中身の大きさで MFC と同じ式（FR-030）。
"""

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QAbstractItemView, QLabel, QTableWidget, QTableWidgetItem, QWidget

from can_log_analysis.stats import make_histogram
from can_log_analysis_gui import texts
from can_log_analysis_gui.graph import GraphWidget

MIN_SIZE = QSize(520, 400)


def place_window(size: QSize, owner: QRect, work: QRect) -> QRect:
    """MFC CAnalysisDlgBase::OnInitDialog: 枠を含めた矩形を owner の中央に置き、作業領域の右・下・左・上の順にはみ出しを直す。"""
    center = owner.center()
    x = center.x() - size.width() // 2
    y = center.y() - size.height() // 2
    w, h = size.width(), size.height()
    work_right = work.x() + work.width()
    work_bottom = work.y() + work.height()
    if x + w > work_right:
        x = work_right - w
    if y + h > work_bottom:
        y = work_bottom - h
    if x < work.x():
        x = work.x()
    if y < work.y():
        y = work.y()
    return QRect(x, y, w, h)


def frame_extra(widget: QWidget) -> QSize:
    """枠（タイトルバーと縁）の分の大きさ。表示前は 0。"""
    outer, inner = widget.frameGeometry(), widget.geometry()
    return QSize(outer.width() - inner.width(), outer.height() - inner.height())


def apply_frame_size(widget: QWidget, size: QSize, minimum: QSize):
    """枠を含めた大きさで初期サイズと最小サイズを決める（FR-022）。"""
    extra = frame_extra(widget)
    widget.setMinimumSize(minimum - extra)
    widget.resize(size - extra)


class AnalysisWindow(QWidget):
    """解析画面の共通部分: 表、Esc で閉じる（Enter では閉じない）、枠込みの大きさ、メインウィンドウ中央の配置。"""

    closed = Signal(str)

    initial_size = QSize(900, 640)
    widths = ()
    numeric_from = 2

    def __init__(self, kind: str, analysis, table, owner: QWidget):
        super().__init__(owner, Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.kind = kind
        self.analysis = analysis
        self.table = table
        self._owner = owner
        self.setWindowTitle(table.title)
        self.table_widget = self._make_table(table)
        self.graph = GraphWidget(self)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.close)
        self._placed = False

    def _make_table(self, table) -> QTableWidget:
        t = QTableWidget(len(table.rows), len(table.columns), self)
        t.setHorizontalHeaderLabels(table.columns)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setShowGrid(True)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(t.fontMetrics().height() + 6)  # compact rows as the MFC list
        t.horizontalHeader().setStretchLastSection(False)
        for c in range(len(table.columns)):
            align = (Qt.AlignRight if c >= self.numeric_from else Qt.AlignLeft) | Qt.AlignVCenter
            t.horizontalHeaderItem(c).setTextAlignment(align)
            if c < len(self.widths):
                t.setColumnWidth(c, self.widths[c])
        for r, row in enumerate(table.rows):
            for c, text in enumerate(row):
                item = QTableWidgetItem(text)
                item.setTextAlignment((Qt.AlignRight if c >= self.numeric_from else Qt.AlignLeft) | Qt.AlignVCenter)
                t.setItem(r, c, item)
        return t

    def selected_row(self) -> int:
        rows = self.table_widget.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    def showEvent(self, event):
        super().showEvent(event)
        if not self._placed:
            self._placed = True
            apply_frame_size(self, self.initial_size, MIN_SIZE)
            owner = self._owner.frameGeometry() if self._owner is not None else self.frameGeometry()
            work = self.screen().availableGeometry()
            self.move(place_window(self.initial_size, owner, work).topLeft())

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.accept()  # Enter does not close the window (MFC OnOK)
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed.emit(self.kind)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.layout_content(self.width(), self.height())

    def layout_content(self, cx: int, cy: int):
        raise NotImplementedError


class ListNoteGraphWindow(AnalysisWindow):
    """表・注記・グラフの画面（送信待ち時間・受信完了時間・送信ジッター。MFC LayoutListNoteGraph）。"""

    def __init__(self, kind, analysis, table, owner):
        super().__init__(kind, analysis, table, owner)
        self.note_label = QLabel(table.note, self)
        self.note_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._histograms = {}
        self.table_widget.itemSelectionChanged.connect(self._on_selection)
        if table.rows:
            self.table_widget.selectRow(0)
        else:
            self.graph.set_no_data(texts.IDS_ANALYSIS_NO_DATA)

    def layout_content(self, cx, cy):
        margin, note_h = 8, 22
        width = max(0, cx - 2 * margin)
        inner = max(0, cy - 2 * margin - note_h - margin)
        list_h = inner * 2 // 5
        self.table_widget.setGeometry(margin, margin, width, list_h)
        note_top = margin + list_h + 4
        self.note_label.setGeometry(margin, note_top, width, note_h)
        graph_top = note_top + note_h + 4
        self.graph.setGeometry(margin, graph_top, width, max(0, cy - margin - graph_top))

    def _on_selection(self):
        row = self.selected_row()
        if row >= 0:
            self.show_row(row)

    def show_row(self, index: int):
        raise NotImplementedError

    def _show_histogram(self, index: int, stats):
        """件数 0 → データなし。それ以外は行のヒストグラム（行ごとに覚えておく。research.md R-5）。"""
        if stats.count == 0:
            self.graph.set_no_data(texts.IDS_ANALYSIS_NO_DATA)
            return
        histogram = self._histograms.get(index)
        if histogram is None:
            histogram = self._histograms[index] = make_histogram(stats.values)
        self.graph.set_bars(histogram, texts.IDS_LAT_AXIS_X, texts.IDS_LAT_AXIS_Y)


class TxWaitWindow(ListNoteGraphWindow):
    """送信待ち時間（MFC CTxWaitDlg）。"""

    widths = (90, 90, 80, 100, 100, 100, 100)
    numeric_from = 2

    def show_row(self, index):
        self._show_histogram(index, self.analysis.rows[index].stats)


WINDOWS = {"txwait": TxWaitWindow}
