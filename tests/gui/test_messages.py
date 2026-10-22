"""開けない・読めないときのメッセージ（FR-006、FR-010、FR-015、FR-060a、MFC RunAnalysis・IDS_LOAD_ERROR、US5）。"""

from can_log_analysis_gui import texts
from can_log_analysis_gui.main_window import MainWindow

from conftest import DATA_DIR

SAMPLE = DATA_DIR / "sample_vehicle_16ecu" / "sample_vehicle_16ecu.canprj"
ERRORS = DATA_DIR / "errors"


def load(main_window, dialogs, project):
    dialogs.project_path = project
    main_window.actions["load"].trigger()


def test_no_project_fr010(main_window, dialogs):
    main_window.actions["txwait"].trigger()
    assert dialogs.messages == [("information", texts.IDS_LOG_NONE_NOPROJECT)]
    assert main_window.job is None
    assert main_window.isEnabled()


def test_no_log_fr010(main_window, dialogs):
    load(main_window, dialogs, ERRORS / "no_log.canprj")
    main_window.actions["busload"].trigger()
    assert dialogs.messages == [("information", texts.IDS_LOG_NONE % "no_log.canprj")]
    assert main_window.job is None


def test_log_cannot_be_read_fr015(qtbot, main_window, dialogs):
    project = ERRORS / "bad_number.canprj"
    load(main_window, dialogs, project)
    main_window.actions["jitter"].trigger()
    qtbot.waitUntil(lambda: main_window.job is None, timeout=10000)
    assert dialogs.messages == [("warning", texts.IDS_LOG_READ_ERROR % (str(project) + ".log.csv"))]
    assert main_window.windows == {}
    assert main_window.isEnabled()


def test_project_cannot_be_read_keeps_the_current_one_fr006(qtbot, main_window, dialogs, wait_window):
    load(main_window, dialogs, SAMPLE)
    main_window.actions["txwait"].trigger()
    w = wait_window(main_window, "txwait")
    load(main_window, dialogs, ERRORS / "bad_project.canprj")
    assert len(dialogs.messages) == 1
    icon, text = dialogs.messages[0]
    assert icon == "warning"
    head = texts.IDS_LOAD_ERROR.split("%s")[0]
    assert text.startswith(head) and len(text) > len(head)  # the reason follows
    assert main_window.project.name == "sample_vehicle_16ecu.canprj"
    assert main_window.windowTitle() == "CAN ログ解析 - sample_vehicle_16ecu.canprj"
    assert main_window.project_view.name_value.text() == "sample_vehicle_16ecu.canprj"
    assert main_window.windows == {"txwait": w}


def test_missing_project_fr006(main_window, dialogs, tmp_path):
    load(main_window, dialogs, tmp_path / "none.canprj")
    assert [icon for icon, _ in dialogs.messages] == ["warning"]
    assert main_window.project is None


def test_bad_project_on_the_command_line_fr060a(qtbot, dialogs):
    window = MainWindow(project=str(ERRORS / "bad_project.canprj"))
    qtbot.addWidget(window)
    assert [icon for icon, _ in dialogs.messages] == ["warning"]
    assert window.project is None
    assert window.windowTitle() == "CAN ログ解析"
