"""セルの書式と文言（FR-036、AR-094、contracts/table-csv.md）。"""

import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from can_log_analysis import formatting
from can_log_analysis.formatting import can_id_text, ecu_name, fixed1

RC = Path(__file__).parents[2] / "reference" / "mfc" / "MFCApplication1.rc"


def test_ecu_name():
    assert ecu_name(1) == "ECU 01"
    assert ecu_name(16) == "ECU 16"
    assert ecu_name(100) == "ECU 100"
    assert ecu_name(0) == "ECU 00"


def test_can_id_text():
    assert can_id_text(0x80) == "0x080"
    assert can_id_text(0x7FF) == "0x7FF"
    assert can_id_text(0x0A0) == "0x0A0"
    assert can_id_text(0x1ABCD) == "0x1ABCD"


@pytest.mark.parametrize("value,expected", [
    (126.0, "126.0"), (0.0, "0.0"), (0.05, "0.1"), (0.25, "0.2"), (0.35, "0.3"), (2.675, "2.7"), (-0.05, "-0.1")])
def test_fixed1_rounds_like_printf(value, expected):
    # The binary value is rounded exactly, as the UCRT printf of MFC does (research.md R-4):
    # 0.05 is 0.05000000000000000277 -> 0.1, 0.25 is exact -> 0.2 (half to even), 0.35 is 0.34999999999999997780 -> 0.3
    assert fixed1(value) == expected


def test_decimal_half_up_differs_from_printf():
    # Rounding the decimal text half up would give other cells than MFC, so it must not be used
    def half_up(x):
        return str(Decimal(str(x)).quantize(Decimal("0.1"), ROUND_HALF_UP))

    assert (half_up(0.25), fixed1(0.25)) == ("0.3", "0.2")
    assert (half_up(0.35), fixed1(0.35)) == ("0.4", "0.3")


def rc_strings():
    text = RC.read_text(encoding="utf-16")
    return {m.group(1): m.group(2) for m in re.finditer(r'^\s*(IDS_\w+)\s+"((?:[^"]|"")*)"', text, re.M)}


@pytest.mark.parametrize("name", [
    "IDS_LAT_TITLE", "IDS_LAT_COLUMNS", "IDS_LAT_ALL", "IDS_LAT_NOTE",
    "IDS_BUS_TITLE", "IDS_BUS_SUMMARY", "IDS_BUS_COLUMNS",
    "IDS_WAIT_TITLE", "IDS_WAIT_COLUMNS", "IDS_WAIT_NOTE",
    "IDS_JIT_TITLE", "IDS_JIT_COLUMNS", "IDS_JIT_NOTE",
])
def test_texts_are_the_rc_strings(name):
    assert getattr(formatting, name) == rc_strings()[name]


def test_log_none_is_the_first_sentence_of_the_rc_string():
    first = rc_strings()["IDS_LOG_NONE"].split("\\n")[0]
    assert formatting.IDS_LOG_NONE == first
    assert first == "プロジェクト「%s」のシミュレーションログはありません。"


def test_special_characters():
    assert "µ" in formatting.IDS_LAT_COLUMNS        # µ
    assert "→" in formatting.IDS_LAT_NOTE           # →
    assert "−" in formatting.IDS_JIT_NOTE           # −
    assert "〜" in formatting.IDS_BUS_SUMMARY        # 〜
    assert "　" in formatting.IDS_BUS_SUMMARY        # ideographic space
