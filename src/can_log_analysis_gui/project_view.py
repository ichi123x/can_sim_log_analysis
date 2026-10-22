"""メインウィンドウの本体: プロジェクトの情報と .canprj の内容（FR-004、contracts/gui.md「メインウィンドウ」、research.md R-7）。

表示だけで、編集・保存はしない。解析の計算には使わない（元仕様 AR-003）。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QSplitter,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from can_log_analysis.formatting import can_id_text, ecu_name
from can_log_analysis_gui import texts

NO_PROJECT = "プロジェクトが開かれていません"
NO_LOG = "なし"
ALL_FRAMES = "全受信"

ECU_COLUMNS = ["ECU", "名前", "ラベル", "受信フィルタ", "受信処理遅延(ms)", "電源投入(ms)", "初期化時間(ms)"]
ECU_NUMERIC_FROM = 4
# MFC IDS_FRAME_COL_* (No., フレーム名, ID, DLC, 初回オフセット(ms), 送信周期(ms)) after the sending ECU
FRAME_COLUMNS = ["送信 ECU", "No.", "フレーム名", "ID", "DLC", "初回オフセット(ms)", "送信周期(ms)"]
FRAME_NUMERIC = {1, 4, 5, 6}

_BIT_RATES = {125000: "125 kbps", 250000: "250 kbps", 500000: "500 kbps", 1000000: "1 Mbps"}  # MFC SettingsDlg


def format_ms(us: int | None) -> str:
    """MFC FormatMs（FrameEditDlg.cpp）: 整数 ms なら整数、それ以外は小数 3 桁。None は空欄。"""
    if us is None:
        return ""
    if us % 1000 == 0:
        ms = abs(us) // 1000
        return "%d" % (ms if us >= 0 else -ms)
    return "%.3f" % (us / 1000.0)


def format_bit_rate(bps: int | None) -> str:
    if bps is None:
        return ""
    return _BIT_RATES.get(bps, f"{bps} bps")


def _text(value) -> str:
    return "" if value is None else str(value)


def _make_table(columns, numeric) -> QTableWidget:
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(table.fontMetrics().height() + 6)
    for c in numeric:
        table.horizontalHeaderItem(c).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return table


def _fill(table: QTableWidget, rows, numeric):
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            item = QTableWidgetItem(text)
            item.setTextAlignment((Qt.AlignRight if c in numeric else Qt.AlignLeft) | Qt.AlignVCenter)
            table.setItem(r, c, item)
    table.resizeColumnsToContents()


class ProjectView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name_value = QLabel(NO_PROJECT)
        self.path_value = QLabel()
        self.log_value = QLabel()
        for label in (self.name_value, self.path_value, self.log_value):
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        project_box = QGroupBox("プロジェクト")
        form = QFormLayout(project_box)
        form.addRow(texts.IDS_PROJECT_PATH_LABEL, self.name_value)
        form.addRow("パス：", self.path_value)
        form.addRow("ログ：", self.log_value)

        self.bit_rate_value = QLabel()
        self.ecu_count_value = QLabel()
        self.duration_value = QLabel()
        network_box = QGroupBox("ネットワーク")
        form = QFormLayout(network_box)
        form.addRow("通信速度：", self.bit_rate_value)
        form.addRow("ECU 数：", self.ecu_count_value)
        form.addRow("シミュレーション時間：", self.duration_value)

        top = QHBoxLayout()
        top.addWidget(project_box, 3)
        top.addWidget(network_box, 1)

        self.ecu_table = _make_table(ECU_COLUMNS, range(ECU_NUMERIC_FROM, len(ECU_COLUMNS)))
        self.frame_table = _make_table(FRAME_COLUMNS, FRAME_NUMERIC)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._titled("ECU", self.ecu_table))
        splitter.addWidget(self._titled("送信フレーム", self.frame_table))

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)

    @staticmethod
    def _titled(title, table):
        box = QGroupBox(title)
        QVBoxLayout(box).addWidget(table)
        return box

    def show_project(self, project, contents):
        """project が None なら未選択の表示にする。"""
        if project is None:
            self.name_value.setText(NO_PROJECT)
            for label in (self.path_value, self.log_value, self.bit_rate_value, self.ecu_count_value,
                          self.duration_value):
                label.setText("")
            _fill(self.ecu_table, [], ())
            _fill(self.frame_table, [], ())
            return
        self.name_value.setText(project.name)
        self.path_value.setText(str(project.path))
        log = project.log_path
        self.log_value.setText(f"{log.name}（{log.stat().st_size / 1e6:.1f} MB）" if log.is_file() else NO_LOG)
        self.bit_rate_value.setText(format_bit_rate(contents.bit_rate_bps))
        self.ecu_count_value.setText(_text(contents.ecu_count))
        self.duration_value.setText("" if contents.duration_sec is None else f"{contents.duration_sec} s")

        senders = {e.section_no: e for e in contents.ecus}

        def ecu_label(ecu):
            return "" if ecu is None or ecu.node_id is None else ecu_name(ecu.node_id)

        ecu_rows = [[ecu_label(e), e.name, e.label, ALL_FRAMES if e.rx_filter is None else e.rx_filter,
                     format_ms(e.receive_delay_us), format_ms(e.power_on_time_us), format_ms(e.init_duration_us)]
                    for e in contents.ecus]
        frame_rows = [[ecu_label(senders.get(f.node_section_no)), str(f.frame_no), f.name,
                       "" if f.can_id is None else can_id_text(f.can_id), _text(f.dlc),
                       format_ms(f.initial_offset_us), format_ms(f.period_us)]
                      for f in contents.frames]
        _fill(self.ecu_table, ecu_rows, set(range(ECU_NUMERIC_FROM, len(ECU_COLUMNS))))
        _fill(self.frame_table, frame_rows, FRAME_NUMERIC)
