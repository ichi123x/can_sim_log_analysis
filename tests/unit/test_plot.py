"""グラフの目盛りと間引き（FR-050、FR-051、FR-033、FR-041、MFC NiceTicks・MinMaxPerColumn・MaxPerColumn、
AnalysisDlg.cpp の TicksFromZero・TicksCovering・FormatTick）。"""

import pytest

from can_log_analysis.analysis import JitterPoint
from can_log_analysis.plot import (ColumnRange, format_tick, max_per_column, min_max_per_column, nice_ticks,
                                   ticks_covering, ticks_from_zero)


def test_nice_ticks():
    assert nice_ticks(0, 100, 5) == [0, 20, 40, 60, 80, 100]
    assert nice_ticks(0, 37, 4) == [0, 10, 20, 30]
    assert nice_ticks(0, 1, 8) == pytest.approx([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    assert nice_ticks(-178, 178, 5) == [-100, 0, 100]


def test_nice_ticks_degenerate():
    assert nice_ticks(5, 5, 4) == [5]
    assert nice_ticks(5, 1, 4) == [5]
    assert nice_ticks(0, 10, 0) == [0]


def test_nice_ticks_snaps_near_zero_to_zero():
    ticks = nice_ticks(-0.3, 0.3, 3)
    assert 0.0 in ticks
    assert all(t == 0.0 or abs(t) > 1e-12 for t in ticks)


def test_ticks_from_zero():
    assert ticks_from_zero(37, 4) == [0, 10, 20, 30, 40]
    assert ticks_from_zero(50, 5) == [0, 10, 20, 30, 40, 50]
    assert ticks_from_zero(0.0, 1) == [0, 1]


def test_ticks_covering():
    assert ticks_covering(-178, 178, 5) == [-200, -100, 0, 100, 200]
    assert ticks_covering(3, 3, 5) == [3, 3]
    assert ticks_covering(0, 100, 5) == [0, 20, 40, 60, 80, 100]


@pytest.mark.parametrize("value,text", [(20.0, "20"), (0.0, "0"), (0.2, "0.2"), (12.5, "12.5"), (2.5e-5, "2.5e-05"),
                                        (-100.0, "-100"), (5000.0, "5000")])
def test_format_tick(value, text):
    assert format_tick(value) == text


def test_min_max_per_column():
    points = [JitterPoint(0, 3), JitterPoint(5, -1), JitterPoint(10, 7)]
    assert min_max_per_column(points, 0, 10, 2) == [ColumnRange(True, -1, 3), ColumnRange(True, 7, 7)]


def test_min_max_per_column_empty_columns_and_clamping():
    points = [JitterPoint(0, 1), JitterPoint(99, 2)]
    cols = min_max_per_column(points, 0, 99, 4)
    assert [c.has for c in cols] == [True, False, False, True]
    assert min_max_per_column(points, 0, 99, 0) == []
    # a point outside [t0, t1] goes to the nearest end column
    assert min_max_per_column([JitterPoint(500, 9)], 0, 99, 4)[3] == ColumnRange(True, 9, 9)


def test_max_per_column():
    assert max_per_column([1, 5, 2, 8, 3, 4], 3) == [5, 8, 4]
    assert max_per_column([1, 2], 3) == [1, 2]
    assert max_per_column([1, 2, 3], 0) == [1, 2, 3]
    assert max_per_column([1, 9, 2, 3, 4], 2) == [9, 4]  # columns [0, 2) and [2, 5)
