"""解析画面（MFC AnalysisDlg.cpp の CAnalysisDlgBase と CTxWaitDlg ほか。contracts/gui.md「解析画面」）。

表の列見出し・セルは機能 001 の Table をそのまま表示する（FR-024、FR-025）。
大きさは MFC と同じく枠を含めたウィンドウ全体（FR-022）。配置は中身の大きさで MFC と同じ式（FR-030）。
"""

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QWidget

from can_log_analysis.stats import make_histogram
from can_log_analysis_gui import texts
from can_log_analysis_gui.graph import GraphWidget

MIN_SIZE = QSize(520, 400)


def dialog_font() -> QFont:
    """MFC の解析画面のフォント（MFCApplication1.rc の IDD_ANALYSIS_*: FONT 9, "MS UI Gothic"）。表・見出し・注記に使う。"""
    font = QFont("MS UI Gothic")
    font.setPointSize(9)
    font.setWeight(QFont.Weight.Normal)
    return font


# The MFC list draws the selected row in the system highlight colour (white text) while its window is active and,
# with LVS_SHOWSELALWAYS, in grey otherwise. Qt's windows11 style draws a pale grey row instead, so set it here.
LIST_SELECTION_STYLE = (
    "QTableView { outline: 0; }"  # no frame around the current cell (MFC selects whole rows)
    "QTableView::item:selected, QTableView::item:selected:focus"
    " { background: palette(highlight); color: palette(highlighted-text); }"
    "QTableView::item:selected:!active { background: palette(button); color: palette(text); }"
)


def list_row_height(font: QFont) -> int:
    """MFC のリスト（LVS_REPORT＋グリッド線）と同じ詰め方の行の高さ（125% で約 19 px）。"""
    return QFontMetrics(font).height() + 3


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
        self.setFont(dialog_font())
        self.setWindowTitle(table.title)
        self.table_widget = self._make_table(table)
        self.graph = GraphWidget(self)
        self._placed = False

    def _make_table(self, table) -> QTableWidget:
        t = QTableWidget(len(table.rows), len(table.columns), self)
        t.setHorizontalHeaderLabels(table.columns)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setShowGrid(True)
        font = dialog_font()
        t.setFont(font)
        t.setStyleSheet(LIST_SELECTION_STYLE)
        rows = t.verticalHeader()
        rows.setVisible(False)
        rows.setMinimumSectionSize(1)
        rows.setSectionResizeMode(QHeaderView.Fixed)
        rows.setDefaultSectionSize(list_row_height(font))
        header = t.horizontalHeader()
        header.setFont(font)  # the MFC list header is not bold
        header.setStretchLastSection(False)
        header.setHighlightSections(False)  # a selected row must not make the header bold
        for c in range(len(table.columns)):
            align = (Qt.AlignRight if c >= self.numeric_from else Qt.AlignLeft) | Qt.AlignVCenter
            t.horizontalHeaderItem(c).setTextAlignment(align)
            t.horizontalHeaderItem(c).setFont(font)
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
        # The key events of the list and the graph come up to here when they do not use them.
        # (A QShortcut only works while the window is active; MFC handles Esc as a key of the dialog.)
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.accept()  # Enter does not close the window (MFC OnOK)
            return
        if event.key() == Qt.Key_Escape:
            event.accept()
            self.close()  # MFC OnCancel
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
        self.table_widget.setFocus()  # MFC m_list.SetFocus(): the selected row is shown highlighted

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


class LatencyWindow(ListNoteGraphWindow):
    """受信完了時間（MFC CLatencyDlg）。"""

    widths = (90, 90, 80, 100, 100, 100, 100)
    numeric_from = 2

    def show_row(self, index):
        self._show_histogram(index, self.analysis.rows[index].stats)


class JitterWindow(ListNoteGraphWindow):
    """送信ジッター（MFC CJitterDlg）。グラフは選んだ CAN ID のずれの時系列。"""

    widths = (90, 90, 90, 80, 100, 100, 110)
    numeric_from = 2

    def show_row(self, index):
        row = self.analysis.rows[index]
        if row.count == 0:
            self.graph.set_no_data(texts.IDS_ANALYSIS_NO_DATA)
        else:
            self.graph.set_deviation(row.points, texts.IDS_BUS_AXIS_X, texts.IDS_JIT_AXIS_Y)


class BusLoadWindow(AnalysisWindow):
    """CAN バス負荷（MFC CBusLoadDlg）: 上に要約 1 行、中央に区間ごとの負荷率の折れ線、下に ECU の表。
    表の行を選んでもグラフは変わらない。開いたときは行を選ばない（CreateContent は SetFocus だけ）。"""

    initial_size = QSize(960, 680)
    widths = (100, 140, 120)
    numeric_from = 1

    def __init__(self, kind, analysis, table, owner):
        super().__init__(kind, analysis, table, owner)
        self.summary_label = QLabel(table.note, self)
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.note_label = self.summary_label  # the line under the title, as in the other windows
        if analysis.transmission_count == 0:
            self.graph.set_no_data(texts.IDS_ANALYSIS_NO_DATA)
        else:
            self.graph.set_line(analysis.section_pct, analysis.section_us, analysis.average_pct,
                                texts.IDS_BUS_AXIS_X, texts.IDS_BUS_AXIS_Y)
        self.table_widget.setFocus()

    def layout_content(self, cx, cy):
        # CBusLoadDlg::LayoutContent
        margin, summary_h = 8, 22
        width = max(0, cx - 2 * margin)
        self.summary_label.setGeometry(margin, margin, width, summary_h)
        top = margin + summary_h + 4
        rest = max(0, cy - margin - top - 6)
        graph_h = rest * 3 // 5
        self.graph.setGeometry(margin, top, width, graph_h)
        list_top = top + graph_h + 6
        self.table_widget.setGeometry(margin, list_top, width, max(0, cy - margin - list_top))


WINDOWS = {"txwait": TxWaitWindow, "latency": LatencyWindow, "jitter": JitterWindow, "busload": BusLoadWindow}
