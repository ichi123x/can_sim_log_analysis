"""解析画面のグラフ（MFC AnalysisDlg.cpp の CAnalysisGraph。contracts/gui.md「グラフの描き方」）。

make_plan が範囲・目盛り・図形の座標を決め（テストはここを確かめる）、GraphWidget はそれを QPainter で描くだけ。
目盛りと間引きの計算は解析コアの can_log_analysis.plot（MFC と同じ式）。
"""

import math
from dataclasses import dataclass, field

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from can_log_analysis.formatting import fixed1
from can_log_analysis.plot import (format_tick, max_per_column, min_max_per_column, nice_ticks, ticks_covering,
                                   ticks_from_zero)
from can_log_analysis_gui import texts

# plot area margins (96 dpi; Qt scales logical pixels)
_LEFT, _TOP, _RIGHT, _BOTTOM = 70, 32, 20, 46

# the colours and text size of MFC AnalysisDlg.cpp (kGraphBack ... kTextPx)
_BACK = QColor(255, 255, 255)
_FRAME = QColor(160, 160, 160)
_GRID = QColor(225, 225, 225)
_TEXT = QColor(60, 60, 60)
_DATA = QColor(30, 110, 200)
_ZERO = QColor(150, 150, 150)
_AVERAGE = QColor(240, 140, 0)
_TEXT_PX = 12  # Meiryo UI


# ---- what the graph shows (MFC CAnalysisGraph modes) ----

@dataclass(frozen=True)
class NoData:
    text: str


@dataclass(frozen=True)
class Bars:
    histogram: object  # can_log_analysis.stats.Histogram
    x_label: str
    y_label: str


@dataclass(frozen=True)
class Deviation:
    points: list  # JitterPoint, by time
    x_label: str
    y_label: str


@dataclass(frozen=True)
class Line:
    pct: list[float]
    section_us: int
    average_pct: float
    x_label: str
    y_label: str


@dataclass
class Plan:
    plot: tuple[int, int, int, int] | None = None  # left, top, width, height
    x_range: tuple[float, float] = (0.0, 1.0)
    y_range: tuple[float, float] = (0.0, 1.0)
    x_ticks: list[tuple[float, str]] = field(default_factory=list)
    y_ticks: list[tuple[float, str]] = field(default_factory=list)
    bars: list[tuple[int, int, int, int]] = field(default_factory=list)  # x, y, width, height
    points: list[tuple[int, int]] = field(default_factory=list)
    polyline: list[tuple[int, int]] = field(default_factory=list)
    columns: list[tuple[int, int, int]] = field(default_factory=list)  # x, y of the min, y of the max
    zero_line: int | None = None
    average: tuple[int, str] | None = None  # y, text
    no_data_text: str | None = None
    x_label: str = ""
    y_label: str = ""


def _lround(x: float) -> int:
    # std::lround: half away from zero
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def make_plan(content, width: int, height: int) -> Plan:
    """MFC CAnalysisGraph::Draw と同じ手順で、描く前の範囲・目盛り・図形を決める。"""
    if isinstance(content, NoData):
        return Plan(no_data_text=content.text)
    plan = Plan(x_label=content.x_label, y_label=content.y_label)
    left, top = _LEFT, _TOP
    right, bottom = width - _RIGHT, height - _BOTTOM
    plot_w, plot_h = right - left, bottom - top
    if plot_w < 40 or plot_h < 30:
        return plan

    if isinstance(content, Deviation):
        last_us = lo = hi = 0
        for p in content.points:
            last_us = max(last_us, p.time_us)
            lo = min(lo, p.deviation_us)
            hi = max(hi, p.deviation_us)
        x_lo, x_hi = 0.0, (last_us / 1000.0 if last_us > 0 else 1.0)
        y_ticks = [-1.0, 0.0, 1.0] if lo == hi else ticks_covering(float(lo), float(hi), 5)
        y_lo, y_hi = y_ticks[0], y_ticks[-1]
    elif isinstance(content, Bars):
        h = content.histogram
        x_lo = float(h.start_us)
        x_hi = x_lo + float(h.width_us) * len(h.counts)
        max_count = max([1] + list(h.counts))
        y_ticks = ticks_from_zero(float(max_count), min(5, max_count))
        y_lo, y_hi = 0.0, y_ticks[-1]
    else:
        x_lo, x_hi = 0.0, content.section_us * len(content.pct) / 1000.0
        y_ticks = [0, 20, 40, 60, 80, 100]
        y_lo, y_hi = 0.0, 100.0

    def x_px(x):
        return left + _lround((x - x_lo) / (x_hi - x_lo) * plot_w)

    def y_px(y):
        return bottom - _lround((y - y_lo) / (y_hi - y_lo) * plot_h)

    plan.plot = (left, top, plot_w, plot_h)
    plan.x_range = (x_lo, x_hi)
    plan.y_range = (float(y_lo), float(y_hi))
    plan.y_ticks = [(t, format_tick(t)) for t in y_ticks]
    plan.x_ticks = [(t, format_tick(t)) for t in nice_ticks(x_lo, x_hi, max(2, plot_w // 90))]

    if isinstance(content, Deviation):
        plan.zero_line = y_px(0.0)
        points = content.points
        if len(points) <= plot_w:
            plan.points = [(x_px(p.time_us / 1000.0), y_px(float(p.deviation_us))) for p in points]
            plan.polyline = list(plan.points)
        else:
            # more points than columns: the smallest to the largest of each column (neither dips nor peaks are lost)
            last_us = max(p.time_us for p in points)
            for c, col in enumerate(min_max_per_column(points, 0, last_us, plot_w)):
                if not col.has:
                    continue
                y_min, y_max = y_px(float(col.min_us)), y_px(float(col.max_us))
                plan.columns.append((left + c, y_min, y_max))
                plan.polyline.append((left + c, (y_min + y_max) // 2))
    elif isinstance(content, Bars):
        h = content.histogram
        for i, count in enumerate(h.counts):
            if count == 0:
                continue
            edge = x_lo + float(h.width_us) * i
            x0, x1 = x_px(edge), x_px(edge + float(h.width_us))
            if x1 - x0 > 2:
                x1 -= 1  # a thin gap between bars
            y = y_px(float(count))
            plan.bars.append((x0, y, max(1, x1 - x0), bottom - y))
    else:
        # one point per column at most, keeping the peak of each column
        values = max_per_column(content.pct, plot_w)
        n = len(values)
        for i, v in enumerate(values):
            plan.polyline.append((left + int((i + 0.5) * plot_w / n), y_px(min(v, 100.0))))
        plan.average = (y_px(content.average_pct), f"{texts.IDS_BUS_AVERAGE} {fixed1(content.average_pct)}%")
    return plan


class GraphWidget(QWidget):
    """MFC CAnalysisGraph。set_* で内容を決め、paintEvent で make_plan の結果を描く。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._content = NoData(texts.IDS_ANALYSIS_NO_DATA)
        self.setMinimumSize(1, 1)

    def content(self):
        return self._content

    def set_no_data(self, text: str):
        self._set(NoData(text))

    def set_bars(self, histogram, x_label: str, y_label: str):
        self._set(Bars(histogram, x_label, y_label) if histogram.counts else NoData(self._no_data_text()))

    def set_line(self, pct, section_us: int, average_pct: float, x_label: str, y_label: str):
        self._set(Line(list(pct), section_us, average_pct, x_label, y_label) if pct else NoData(self._no_data_text()))

    def set_deviation(self, points, x_label: str, y_label: str):
        self._set(Deviation(list(points), x_label, y_label) if points else NoData(self._no_data_text()))

    def plan(self, width: int, height: int) -> Plan:
        return make_plan(self._content, width, height)

    def _no_data_text(self):
        return self._content.text if isinstance(self._content, NoData) else texts.IDS_ANALYSIS_NO_DATA

    def _set(self, content):
        self._content = content
        self.update()

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        plan = self.plan(w, h)
        p = QPainter(self)
        p.fillRect(0, 0, w, h, _BACK)
        font = QFont("Meiryo UI")
        font.setPixelSize(_TEXT_PX)
        p.setFont(font)
        p.setPen(_FRAME)
        p.drawRect(0, 0, w - 1, h - 1)
        p.setPen(_TEXT)
        if plan.no_data_text is not None:
            p.drawText(QRect(0, 0, w, h), Qt.AlignCenter, plan.no_data_text)
            return
        if plan.plot is None:
            return
        left, top, pw, ph = plan.plot
        right, bottom = left + pw, top + ph
        y_lo, y_hi = plan.y_range
        x_lo, x_hi = plan.x_range

        for value, text in plan.y_ticks:
            y = bottom - _lround((value - y_lo) / (y_hi - y_lo) * ph)
            p.setPen(_GRID)
            p.drawLine(left, y, right, y)
            p.setPen(_TEXT)
            p.drawText(QRect(0, y - 9, left - 6, 18), Qt.AlignRight | Qt.AlignVCenter, text)
        for value, text in plan.x_ticks:
            x = left + _lround((value - x_lo) / (x_hi - x_lo) * pw)
            p.setPen(_TEXT)
            p.drawLine(x, bottom, x, bottom + 4)
            p.drawText(QRect(x - 50, bottom + 5, 100, 18), Qt.AlignHCenter | Qt.AlignTop, text)

        if plan.zero_line is not None:
            p.setPen(_ZERO)
            p.drawLine(left, plan.zero_line, right, plan.zero_line)
        p.setPen(QPen(_DATA, 1))
        for (x0, y0), (x1, y1) in zip(plan.polyline, plan.polyline[1:]):
            p.drawLine(x0, y0, x1, y1)
        for x, y in plan.points:
            p.fillRect(x - 1, y - 1, 3, 3, _DATA)
        for x, y_min, y_max in plan.columns:
            p.drawLine(x, y_min, x, y_max)
        for x, y, bw, bh in plan.bars:
            p.fillRect(x, y, bw, bh, _DATA)
        if plan.average is not None:
            y, text = plan.average
            pen = QPen(_AVERAGE, 1, Qt.DashLine)
            p.setPen(pen)
            p.drawLine(left, y, right, y)
            rect = QRect(right - 160, y - 20, 156, 18)
            p.fillRect(p.boundingRect(rect, Qt.AlignRight | Qt.AlignBottom, text), _BACK)
            p.setPen(_AVERAGE)
            p.drawText(rect, Qt.AlignRight | Qt.AlignBottom, text)

        p.setPen(_TEXT)
        p.drawLine(left, top, left, bottom)
        p.drawLine(left, bottom, right, bottom)
        p.drawText(QRect(left, bottom + 24, pw, max(0, h - 2 - (bottom + 24))), Qt.AlignCenter, plan.x_label)
        p.drawText(QRect(6, 4, left + 200 - 6, max(0, top - 12 - 4)), Qt.AlignLeft | Qt.AlignTop, plan.y_label)
