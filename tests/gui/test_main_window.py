"""メインウィンドウ（FR-001〜FR-005、FR-060a、contracts/gui.md「メインウィンドウ」、US1）。"""

from PySide6.QtWidgets import QAbstractItemView

from can_log_analysis_gui import texts
from can_log_analysis_gui.main_window import MainWindow
from can_log_analysis_gui.project_view import format_bit_rate, format_ms

from conftest import DATA_DIR

SAMPLE = DATA_DIR / "sample_vehicle_16ecu" / "sample_vehicle_16ecu.canprj"


def menu_items(window):
    out = []
    for menu_action in window.menuBar().actions():
        out.append(menu_action.text())
        out.append([("---" if a.isSeparator() else a.text()) for a in menu_action.menu().actions()])
    return out


def cells(table, row):
    return [table.item(row, c).text() if table.item(row, c) else "" for c in range(table.columnCount())]


def test_title_and_menus_fr001_fr003(main_window):
    assert main_window.windowTitle() == "CAN ログ解析"
    assert menu_items(main_window) == [
        texts.MENU_FILE, [texts.MENU_LOAD_PROJECT, "---", texts.MENU_EXIT],
        texts.MENU_ANALYSIS, [texts.MENU_TXWAIT, texts.MENU_LATENCY, texts.MENU_JITTER, "---", texts.MENU_BUSLOAD],
    ]


def test_no_project_yet_fr004a(main_window):
    assert main_window.project is None
    assert main_window.project_view.name_value.text() == "プロジェクトが開かれていません"
    assert main_window.project_view.ecu_table.rowCount() == 0


def test_load_project_from_the_menu_fr002_fr004(main_window, dialogs):
    dialogs.project_path = SAMPLE
    main_window.actions["load"].trigger()
    assert main_window.windowTitle() == "CAN ログ解析 - sample_vehicle_16ecu.canprj"
    view = main_window.project_view
    assert view.name_value.text() == "sample_vehicle_16ecu.canprj"
    assert view.path_value.text() == str(SAMPLE)
    assert view.log_value.text() == "sample_vehicle_16ecu.canprj.log.csv（1.4 MB）"
    assert (view.bit_rate_value.text(), view.ecu_count_value.text(), view.duration_value.text()) == \
        ("500 kbps", "16", "5 s")
    assert view.ecu_table.rowCount() == 16
    assert cells(view.ecu_table, 0) == ["ECU 01", "ECM Engine Control Module", "エンジン", "0x0A8,0x0E0,0x380,0x3E8",
                                        "", "", ""]
    assert view.frame_table.rowCount() == 31
    assert cells(view.frame_table, 0) == ["ECU 01", "1", "EngineRPM_ThrottlePos", "0x0C0", "8", "5", "10"]
    for table in (view.ecu_table, view.frame_table):
        assert table.editTriggers() == QAbstractItemView.NoEditTriggers


def test_project_without_log(main_window, dialogs):
    dialogs.project_path = DATA_DIR / "errors" / "no_log.canprj"
    main_window.actions["load"].trigger()
    assert main_window.project_view.log_value.text() == "なし"


def test_cancelled_file_dialog_keeps_the_state(main_window, dialogs):
    dialogs.project_path = None
    main_window.actions["load"].trigger()
    assert main_window.project is None


def test_start_folder_is_the_last_project_folder(main_window, dialogs):
    dialogs.project_path = SAMPLE
    main_window.actions["load"].trigger()
    main_window.actions["load"].trigger()
    assert dialogs.start_dirs[-1] == str(SAMPLE.parent)


def test_project_from_the_command_line_fr060a(qtbot, dialogs):
    window = MainWindow(project=str(SAMPLE))
    qtbot.addWidget(window)
    assert window.windowTitle() == "CAN ログ解析 - sample_vehicle_16ecu.canprj"
    assert window.project_view.frame_table.rowCount() == 31


def test_formats_r7():
    assert [format_ms(v) for v in (10000, 5000, 12500, 1, 0, None)] == ["10", "5", "12.500", "0.001", "0", ""]
    assert [format_bit_rate(v) for v in (125000, 250000, 500000, 1000000, 83333, None)] == \
        ["125 kbps", "250 kbps", "500 kbps", "1 Mbps", "83333 bps", ""]
