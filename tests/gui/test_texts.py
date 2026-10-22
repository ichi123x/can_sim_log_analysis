"""画面の文言が MFC 版のリソースと同じこと（research.md R-8、憲章 原則 I）。"""

import re
from pathlib import Path

import pytest

from can_log_analysis_gui import texts

RC = Path(__file__).parents[2] / "reference" / "mfc" / "MFCApplication1.rc"


@pytest.fixture(scope="module")
def rc():
    return RC.read_text(encoding="utf-16")


def rc_string(rc, name):
    m = re.search(rf'^\s*{name}\s+"((?:[^"]|"")*)"', rc, re.M)
    assert m, name
    return m.group(1).replace('""', '"').replace("\\n", "\n")


def menu_texts(rc):
    start = rc.index("IDR_MAINMENU MENU")
    end = rc.index("\nEND", rc.index("BEGIN", start))
    block = rc[start:end]
    return re.findall(r'(?:POPUP|MENUITEM)\s+"([^"]*)"', block)


@pytest.mark.parametrize("name", [
    "IDS_LOG_NONE_NOPROJECT", "IDS_LOG_NONE", "IDS_LOG_READ_ERROR", "IDS_LOAD_ERROR", "IDS_PROJECT_FILTER",
    "IDS_PROJECT_PATH_LABEL", "IDS_ANALYSIS_NO_DATA", "IDS_LAT_AXIS_X", "IDS_LAT_AXIS_Y", "IDS_BUS_AXIS_X",
    "IDS_BUS_AXIS_Y", "IDS_JIT_AXIS_Y", "IDS_BUS_AVERAGE", "IDS_ANALYZING_READ", "IDS_ANALYZING_CALC",
    "IDS_ANALYZING_CANCEL",
])
def test_strings_are_the_rc_strings(rc, name):
    assert getattr(texts, name) == rc_string(rc, name)


@pytest.mark.parametrize("name", [
    "MENU_FILE", "MENU_LOAD_PROJECT", "MENU_ANALYSIS", "MENU_TXWAIT", "MENU_LATENCY", "MENU_JITTER", "MENU_BUSLOAD",
])
def test_menu_texts_are_in_the_rc_menu(rc, name):
    assert getattr(texts, name) in menu_texts(rc)


def test_analysis_menu_order_is_the_rc_order(rc):
    items = menu_texts(rc)
    start = items.index(texts.MENU_ANALYSIS)
    assert items[start + 1:start + 5] == [texts.MENU_TXWAIT, texts.MENU_LATENCY, texts.MENU_JITTER, texts.MENU_BUSLOAD]


def test_progress_dialog_texts(rc):
    start = rc.index("IDD_ANALYSIS_PROGRESS DIALOGEX")
    block = rc[start:rc.index("\nEND", start)]
    assert re.search(r'CAPTION\s+"([^"]*)"', block).group(1) == texts.PROGRESS_TITLE
    assert re.search(r'PUSHBUTTON\s+"([^"]*)"', block).group(1) == texts.PROGRESS_STOP


def test_exit_is_added_by_this_tool():
    # not in the MFC menu; spec Assumptions (元仕様 AR-090)
    assert texts.MENU_EXIT == "終了(&X)"


def test_qt_project_filter():
    assert texts.qt_project_filter() == "CAN プロジェクト (*.canprj);;すべてのファイル (*.*)"
