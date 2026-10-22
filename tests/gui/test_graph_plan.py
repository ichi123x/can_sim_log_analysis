"""グラフの描画計画（FR-032、FR-033、FR-041、FR-050〜FR-052、contracts/gui.md「グラフの描き方」、MFC CAnalysisGraph::Draw）。

画像ではなく、描く前に決める範囲・目盛り・図形の座標を確かめる。
"""

import pytest

from can_log_analysis.analysis import JitterPoint
from can_log_analysis.plot import max_per_column, min_max_per_column, nice_ticks, ticks_covering
from can_log_analysis.stats import Histogram
from can_log_analysis_gui.graph import Bars, Deviation, GraphWidget, Line, NoData, make_plan


def test_no_data():
    plan = make_plan(NoData("データがありません"), 1000, 500)
    assert plan.no_data_text == "データがありません"
    assert plan.plot is None and plan.bars == [] and plan.polyline == []


def test_bars_one_bin_fr032():
    plan = make_plan(Bars(Histogram(start_us=0, width_us=1, counts=[50]), "時間 (µs)", "件数"), 1000, 500)
    assert plan.plot == (70, 32, 910, 422)  # 70 left, 32 top, 20 right, 46 bottom
    assert (plan.x_range, plan.y_range) == ((0.0, 1.0), (0.0, 50.0))
    assert [v for v, _ in plan.y_ticks] == [0, 10, 20, 30, 40, 50]
    assert [t for _, t in plan.y_ticks] == ["0", "10", "20", "30", "40", "50"]
    assert [v for v, _ in plan.x_ticks] == pytest.approx(nice_ticks(0, 1, max(2, 910 // 90)))
    assert plan.bars == [(70, 32, 909, 422)]  # a 1 px gap on the right; the count 50 reaches the top
    assert (plan.x_label, plan.y_label) == ("時間 (µs)", "件数")


def test_bars_skip_empty_bins_and_narrow_bars_have_no_gap():
    plan = make_plan(Bars(Histogram(start_us=0, width_us=10, counts=[3, 0, 1]), "x", "y"), 1000, 500)
    assert len(plan.bars) == 2
    plan = make_plan(Bars(Histogram(start_us=0, width_us=1, counts=[1] * 500), "x", "y"), 1000, 500)
    assert all(w >= 1 for _, _, w, _ in plan.bars)
    widths = {w for _, _, w, _ in plan.bars}
    assert widths <= {1, 2}  # 910 px for 500 bins: no gap is taken off


def test_deviation_points_fr033():
    points = [JitterPoint(10000, -100), JitterPoint(20000, 0), JitterPoint(30000, 100)]
    plan = make_plan(Deviation(points, "時刻 (ms)", "ずれ (µs)"), 1000, 500)
    assert [v for v, _ in plan.y_ticks] == ticks_covering(-100, 100, 5)
    assert plan.x_range == (0.0, 30.0)
    assert plan.zero_line is not None
    assert len(plan.points) == 3 and len(plan.polyline) == 3
    assert plan.columns == []


def test_deviation_all_zero():
    plan = make_plan(Deviation([JitterPoint(1000, 0), JitterPoint(2000, 0)], "x", "y"), 1000, 500)
    assert [v for v, _ in plan.y_ticks] == [-1, 0, 1]


def test_deviation_more_points_than_columns_ar073():
    points = [JitterPoint(t * 10000, (t % 7) - 3) for t in range(1, 500)]
    plan = make_plan(Deviation(points, "x", "y"), 300, 300)
    width = plan.plot[2]
    assert len(points) > width
    expected = [c for c in min_max_per_column(points, 0, points[-1].time_us, width) if c.has]
    assert len(plan.columns) == len(expected)
    assert plan.points == []


def test_line_fr041():
    pct = [float(i % 40) for i in range(500)]
    plan = make_plan(Line(pct, 10000, 19.0, "時刻 (ms)", "負荷 (%)"), 1000, 500)
    assert [v for v, _ in plan.y_ticks] == [0, 20, 40, 60, 80, 100]
    assert plan.x_range == (0.0, 5000.0)
    assert len(plan.polyline) == len(max_per_column(pct, plan.plot[2]))
    y, text = plan.average
    assert text == "平均 19.0%"
    assert plan.plot[1] <= y <= plan.plot[1] + plan.plot[3]


def test_line_values_over_100_are_drawn_at_100():
    plan = make_plan(Line([150.0, 0.0], 10000, 75.0, "x", "y"), 1000, 500)
    assert plan.polyline[0][1] == plan.plot[1]  # top of the plot


def test_too_small_plot_draws_nothing():
    plan = make_plan(Bars(Histogram(start_us=0, width_us=1, counts=[5]), "x", "y"), 100, 500)
    assert plan.plot is None and plan.bars == []


def test_widget_uses_the_same_plan(qtbot):
    widget = GraphWidget()
    qtbot.addWidget(widget)
    widget.set_bars(Histogram(start_us=0, width_us=1, counts=[50]), "x", "y")
    assert widget.plan(1000, 500) == make_plan(Bars(Histogram(start_us=0, width_us=1, counts=[50]), "x", "y"), 1000, 500)
    widget.set_no_data("データがありません")
    assert widget.plan(1000, 500).no_data_text == "データがありません"
    widget.resize(400, 300)
    widget.grab()  # paints without errors
