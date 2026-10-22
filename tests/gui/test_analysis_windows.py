"""解析画面（FR-005、FR-011、FR-020〜FR-025、FR-030〜FR-032、SC-001、contracts/gui.md「解析画面」）。"""

import pytest
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics

from can_log_analysis_gui.analysis_window import LIST_SELECTION_STYLE, place_window
from can_log_analysis_gui.graph import Bars, Deviation, Line, NoData

from conftest import DATA_DIR

SAMPLE = DATA_DIR / "sample_vehicle_16ecu" / "sample_vehicle_16ecu.canprj"
AS001 = DATA_DIR / "as001" / "as001.canprj"


def open_and_run(main_window, dialogs, wait_window, project, kind):
    dialogs.project_path = project
    main_window.actions["load"].trigger()
    main_window.actions[kind].trigger()
    return wait_window(main_window, kind)


def table_cells(w):
    t = w.table_widget
    return [[t.item(r, c).text() for c in range(t.columnCount())] for r in range(t.rowCount())]


def headers(w):
    t = w.table_widget
    return [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]


# ---- 送信待ち時間（US1） ----

def test_txwait_table_matches_golden_sc001(main_window, dialogs, wait_window, golden):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "txwait")
    title, note, columns, rows = golden("sample_vehicle_16ecu", "txwait")
    assert w.windowTitle() == title == "送信待ち時間 - sample_vehicle_16ecu.canprj"
    assert w.note_label.text() == note
    assert headers(w) == columns
    assert table_cells(w) == rows
    assert len(rows) == 32


def test_txwait_columns_fr024(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "txwait")
    t = w.table_widget
    assert [t.columnWidth(c) for c in range(7)] == [90, 90, 80, 100, 100, 100, 100]
    for c in range(7):
        right = bool(t.item(1, c).textAlignment() & Qt.AlignRight)
        assert right == (c >= 2), c
    assert t.selectionMode() == t.SelectionMode.SingleSelection
    assert t.selectionBehavior() == t.SelectionBehavior.SelectRows


def test_first_row_selected_with_its_histogram_fr031(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "txwait")
    assert w.selected_row() == 0
    content = w.graph.content()
    assert isinstance(content, Bars)
    assert sum(content.histogram.counts) == 4015
    assert (content.x_label, content.y_label) == ("時間 (µs)", "件数")


def test_selecting_a_row_changes_the_graph_fr031(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "txwait")
    row = [r[0] for r in table_cells(w)].index("0x1A0")
    w.table_widget.selectRow(row)
    content = w.graph.content()
    assert (content.histogram.start_us, content.histogram.width_us, content.histogram.counts) == (0, 1, [50])


def test_empty_all_row_has_no_data(qtbot, main_window, dialogs, wait_window, make_project):
    project = make_project([])  # header only
    w = open_and_run(main_window, dialogs, wait_window, project, "txwait")
    assert isinstance(w.graph.content(), NoData)
    assert w.graph.content().text == "データがありません"


def test_choosing_the_same_analysis_again_raises_it_fr011(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "txwait")
    main_window.actions["txwait"].trigger()
    assert main_window.job is None  # no new analysis
    assert list(main_window.windows) == ["txwait"]
    assert main_window.windows["txwait"] is w


def test_escape_closes_enter_does_not_fr023(qtbot, main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "txwait")
    qtbot.keyClick(w, Qt.Key_Return)
    assert w.isVisible()
    qtbot.keyClick(w, Qt.Key_Escape)
    qtbot.waitUntil(lambda: "txwait" not in main_window.windows)


def test_opening_another_project_closes_the_windows_fr005(qtbot, main_window, dialogs, wait_window):
    open_and_run(main_window, dialogs, wait_window, SAMPLE, "txwait")
    dialogs.project_path = AS001
    main_window.actions["load"].trigger()
    qtbot.waitUntil(lambda: not main_window.windows)


def test_sizes_include_the_frame_fr022(qtbot, main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "txwait")
    assert w.frameGeometry().size() == QSize(900, 640)
    w.resize(10, 10)  # below the minimum
    qtbot.waitUntil(lambda: w.frameGeometry().size() == QSize(520, 400))


def test_layout_list_note_graph_fr030(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "txwait")
    width, height = w.rect().width(), w.rect().height()
    inner = max(0, height - 2 * 8 - 22 - 8)
    list_h = inner * 2 // 5
    assert w.table_widget.geometry() == QRect(8, 8, width - 16, list_h)
    note_top = 8 + list_h + 4
    assert w.note_label.geometry() == QRect(8, note_top, width - 16, 22)
    graph_top = note_top + 22 + 4
    assert w.graph.geometry() == QRect(8, graph_top, width - 16, height - 8 - graph_top)


def test_place_window_centres_on_the_owner_fr022():
    owner = QRect(100, 100, 1200, 800)
    work = QRect(0, 0, 1920, 1040)
    rect = place_window(QSize(900, 640), owner, work)
    assert rect.size() == QSize(900, 640)
    assert abs(rect.center().x() - owner.center().x()) <= 1 and abs(rect.center().y() - owner.center().y()) <= 1


def test_place_window_keeps_inside_the_work_area_fr022():
    work = QRect(0, 0, 1920, 1040)
    rect = place_window(QSize(900, 640), QRect(1500, 800, 400, 200), work)  # owner near the bottom right
    assert work.contains(rect)
    assert (rect.right(), rect.bottom()) == (work.right(), work.bottom())
    rect = place_window(QSize(900, 640), QRect(-300, -200, 400, 200), work)  # near the top left
    assert rect.topLeft() == QPoint(0, 0)


def test_window_is_placed_by_place_window(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "txwait")
    expected = place_window(QSize(900, 640), main_window.frameGeometry(), w.screen().availableGeometry())
    assert w.frameGeometry().topLeft() == expected.topLeft()


# ---- 受信完了時間・送信ジッター（US2） ----

def test_latency_table_matches_golden_sc001(main_window, dialogs, wait_window, golden):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "latency")
    title, note, columns, rows = golden("sample_vehicle_16ecu", "latency")
    assert (w.windowTitle(), w.note_label.text(), headers(w), table_cells(w)) == (title, note, columns, rows)
    t = w.table_widget
    assert [t.columnWidth(c) for c in range(7)] == [90, 90, 80, 100, 100, 100, 100]
    content = w.graph.content()
    assert isinstance(content, Bars)
    assert sum(content.histogram.counts) == int(rows[0][2])  # the all row
    assert (content.x_label, content.y_label) == ("時間 (µs)", "件数")


def test_jitter_table_matches_golden_sc001(main_window, dialogs, wait_window, golden):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "jitter")
    title, note, columns, rows = golden("sample_vehicle_16ecu", "jitter")
    assert (w.windowTitle(), w.note_label.text(), headers(w), table_cells(w)) == (title, note, columns, rows)
    t = w.table_widget
    assert [t.columnWidth(c) for c in range(7)] == [90, 90, 90, 80, 100, 100, 110]
    for c in range(7):
        assert bool(t.item(0, c).textAlignment() & Qt.AlignRight) == (c >= 2), c


def test_jitter_first_row_is_a_time_series_fr033(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "jitter")
    assert w.selected_row() == 0 and table_cells(w)[0][0] == "0x050"
    content = w.graph.content()
    assert isinstance(content, Deviation)
    assert len(content.points) == 49
    assert (content.x_label, content.y_label) == ("時刻 (ms)", "ずれ (µs)")


def test_jitter_sent_once_has_no_data(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, AS001, "jitter")
    assert [r[3] for r in table_cells(w)] == ["0", "0"]
    for row in range(2):
        w.table_widget.selectRow(row)
        assert isinstance(w.graph.content(), NoData)


def test_jitter_more_points_than_columns_ar073(qtbot, main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "jitter")
    w.resize(10, 10)  # down to the minimum size
    qtbot.waitUntil(lambda: w.frameGeometry().size() == QSize(520, 400))
    w.table_widget.selectRow([r[0] for r in table_cells(w)].index("0x0A0"))
    content = w.graph.content()
    plan = w.graph.plan(w.graph.width(), w.graph.height())
    assert len(content.points) == 499 > plan.plot[2]
    assert plan.columns and not plan.points


def test_windows_are_modeless_fr020(main_window, dialogs, wait_window):
    a = open_and_run(main_window, dialogs, wait_window, SAMPLE, "txwait")
    main_window.actions["jitter"].trigger()
    b = wait_window(main_window, "jitter")
    assert a.isVisible() and b.isVisible()
    assert not a.isModal() and not b.isModal()
    a.table_widget.selectRow(3)
    b.table_widget.selectRow(2)
    assert (a.selected_row(), b.selected_row()) == (3, 2)

# ---- リストの見た目（MFC: FONT 9, "MS UI Gothic"、見出しは標準の太さ、開いたら 1 行目を選んでフォーカス） ----

@pytest.mark.parametrize("kind", ["txwait", "latency", "jitter"])
def test_list_font_and_row_height_like_mfc(main_window, dialogs, wait_window, kind):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, kind)
    t = w.table_widget
    for widget in (t, t.horizontalHeader(), w.note_label):
        assert widget.font().family() == "MS UI Gothic", widget
        assert widget.font().pointSize() == 9, widget
    assert t.horizontalHeader().font().weight() == QFont.Weight.Normal
    for c in range(t.columnCount()):
        assert not t.horizontalHeaderItem(c).font().bold()
    row_h = t.rowHeight(0)
    assert row_h == QFontMetrics(t.font()).height() + 3  # about 19 px at 125 %, as the MFC list
    assert all(t.rowHeight(r) == row_h for r in range(t.rowCount()))


@pytest.mark.parametrize("kind", ["txwait", "latency", "jitter"])
def test_first_row_selected_and_list_focused_like_mfc(main_window, dialogs, wait_window, kind):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, kind)
    assert w.selected_row() == 0
    assert w.focusWidget() is w.table_widget  # MFC m_list.SetFocus(): the selection is shown highlighted
    # the selected row in the highlight colour, grey when the window is inactive (LVS_SHOWSELALWAYS); no cell frame
    assert w.table_widget.styleSheet() == LIST_SELECTION_STYLE
    assert "palette(highlight)" in LIST_SELECTION_STYLE and "outline: 0" in LIST_SELECTION_STYLE

# ---- CAN バス負荷（US3） ----

def test_busload_matches_golden_fr040(main_window, dialogs, wait_window, golden):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "busload")
    title, summary, columns, rows = golden("sample_vehicle_16ecu", "busload")
    assert w.windowTitle() == title == "CAN バス負荷 - sample_vehicle_16ecu.canprj"
    assert w.summary_label.text() == summary
    assert (headers(w), table_cells(w)) == (columns, rows)
    t = w.table_widget
    assert [t.columnWidth(c) for c in range(3)] == [100, 140, 120]
    for c in range(3):
        assert bool(t.item(0, c).textAlignment() & Qt.AlignRight) == (c >= 1), c


def test_busload_graph_is_the_load_line_fr041(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "busload")
    content = w.graph.content()
    assert isinstance(content, Line)
    assert len(content.pct) == 500 and content.section_us == 10000
    assert content.average_pct == w.analysis.average_pct
    assert (content.x_label, content.y_label) == ("時刻 (ms)", "負荷 (%)")
    plan = w.graph.plan(w.graph.width(), w.graph.height())
    assert [v for v, _ in plan.y_ticks] == [0, 20, 40, 60, 80, 100]
    assert plan.average[1] == f"平均 {w.summary_label.text().split()[1][:-1]}%"  # 平均負荷 19.0% -> 平均 19.0%


def test_busload_selecting_a_row_keeps_the_graph(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "busload")
    before = w.graph.content()
    w.table_widget.selectRow(3)
    assert w.graph.content() is before


def test_busload_opens_without_a_selection_like_mfc(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "busload")
    assert w.selected_row() == -1  # CBusLoadDlg::CreateContent selects nothing
    assert w.focusWidget() is w.table_widget


def test_busload_without_transmissions_has_no_data(main_window, dialogs, wait_window, make_project):
    w = open_and_run(main_window, dialogs, wait_window, make_project([]), "busload")
    assert isinstance(w.graph.content(), NoData)
    assert w.table_widget.rowCount() == 0


def test_busload_size_and_layout_fr022_fr040(qtbot, main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "busload")
    assert w.frameGeometry().size() == QSize(960, 680)
    width, height = w.rect().width(), w.rect().height()
    assert w.summary_label.geometry() == QRect(8, 8, width - 16, 22)
    top = 8 + 22 + 4
    rest = max(0, height - 8 - top - 6)
    graph_h = rest * 3 // 5
    assert w.graph.geometry() == QRect(8, top, width - 16, graph_h)
    list_top = top + graph_h + 6
    assert w.table_widget.geometry() == QRect(8, list_top, width - 16, height - 8 - list_top)
    w.resize(10, 10)
    qtbot.waitUntil(lambda: w.frameGeometry().size() == QSize(520, 400))


def test_busload_list_font_like_mfc(main_window, dialogs, wait_window):
    w = open_and_run(main_window, dialogs, wait_window, SAMPLE, "busload")
    t = w.table_widget
    for widget in (t, t.horizontalHeader(), w.summary_label):
        assert (widget.font().family(), widget.font().pointSize()) == ("MS UI Gothic", 9)
    assert t.rowHeight(0) == QFontMetrics(t.font()).height() + 3
    assert t.styleSheet() == LIST_SELECTION_STYLE