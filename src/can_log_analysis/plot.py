"""グラフの目盛りと間引き（MFC LogAnalysis.cpp の NiceTicks・MinMaxPerColumn・MaxPerColumn と、
AnalysisDlg.cpp の TicksFromZero・TicksCovering・FormatTick）。

画面（機能 002）が使う。Qt に依存しない。式・許容（1e-9）・整数除算は MFC と同じ。
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from can_log_analysis.stats import nice_ceil


@dataclass(frozen=True)
class ColumnRange:
    has: bool = False
    min_us: int = 0
    max_us: int = 0


def nice_ticks(lo: float, hi: float, approx_count: int) -> list[float]:
    """lo〜hi を 1・2・5 × 10^m の刻みで約 approx_count 区間に分ける目盛り。hi ≤ lo なら [lo]。"""
    if not hi > lo or approx_count <= 0:
        return [lo]
    step = nice_ceil((hi - lo) / approx_count)
    first = math.ceil(lo / step - 1e-9)
    ticks = []
    i = 0
    while (first + i) * step <= hi + step * 1e-9:
        t = (first + i) * step
        ticks.append(0.0 if abs(t) < step * 1e-9 else t)
        i += 1
    return ticks


def ticks_from_zero(hi: float, approx_count: int) -> list[float]:
    """0 から始まり hi 以上に届く目盛り（件数・負荷用）。"""
    ticks = nice_ticks(0.0, max(hi, 1.0), approx_count)
    if len(ticks) >= 2 and ticks[-1] < hi:
        ticks.append(ticks[-1] + (ticks[1] - ticks[0]))
    return ticks


def ticks_covering(lo: float, hi: float, approx_count: int) -> list[float]:
    """lo〜hi（lo ≤ 0 ≤ hi）を覆うように、両端を刻みいっぱいまで延ばした目盛り。"""
    ticks = nice_ticks(lo, hi, approx_count)
    if len(ticks) < 2:
        return [lo, hi]
    step = ticks[1] - ticks[0]
    if ticks[0] > lo + step * 1e-9:
        ticks.insert(0, ticks[0] - step)
    if ticks[-1] < hi - step * 1e-9:
        ticks.append(ticks[-1] + step)
    return ticks


def format_tick(value: float) -> str:
    """整数なら "%.0f"、それ以外は "%g"（C の printf と同じ結果）。"""
    if abs(value - round(value)) < 1e-9:
        return "%.0f" % value
    return "%g" % value


def min_max_per_column(points: Sequence, t0: int, t1: int, columns: int) -> list[ColumnRange]:
    """[t0, t1] を columns 列に分け、列ごとにずれの最小と最大を残す（山も谷も消さない）。points は JitterPoint の並び。"""
    if columns <= 0:
        return []
    has = [False] * columns
    lows = [0] * columns
    highs = [0] * columns
    span = max(1, t1 - t0 + 1)
    for p in points:
        c = _trunc_div((p.time_us - t0) * columns, span)
        c = max(0, min(c, columns - 1))
        v = p.deviation_us
        if not has[c]:
            has[c] = True
            lows[c] = highs[c] = v
        else:
            if v < lows[c]:
                lows[c] = v
            if v > highs[c]:
                highs[c] = v
    return [ColumnRange(has[c], lows[c], highs[c]) for c in range(columns)]


def max_per_column(values: Sequence[float], columns: int) -> list[float]:
    """値が列より多いとき、列ごとにその範囲の最大値（山を消さない）。そうでなければ値そのもの。"""
    n = len(values)
    if columns <= 0 or n <= columns:
        return list(values)
    out = []
    for c in range(columns):
        begin = c * n // columns
        end = (c + 1) * n // columns
        out.append(max(values[begin:end]))
    return out


def _trunc_div(a: int, b: int) -> int:
    # C++ integer division truncates toward zero
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q
