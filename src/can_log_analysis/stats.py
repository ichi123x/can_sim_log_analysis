"""統計量（MFC ComputeStats。FR-012、AR-042）。"""

import math
from array import array
from dataclasses import dataclass, field


@dataclass
class Stats:
    count: int = 0
    min_us: int = 0
    max_us: int = 0
    mean_us: float = 0.0
    p95_us: int = 0
    values: array = field(default_factory=lambda: array("q"))  # ascending; array, not list (research.md R-3)


def compute_stats(values: array) -> Stats:
    """値を昇順に並べ、件数・最小・最大・平均・95%（最近順位法）を求める。件数 0 ならすべて 0。"""
    ordered = array("q", sorted(values))
    count = len(ordered)
    if count == 0:
        return Stats(values=ordered)
    # MFC sums the values as doubles; every partial sum of integers below 2^53 is exact, so this is the same
    mean = float(sum(ordered)) / count
    rank = (count * 95 + 99) // 100  # ceil(0.95 n), exact in integers
    return Stats(count=count, min_us=ordered[0], max_us=ordered[-1], mean_us=mean, p95_us=ordered[rank - 1],
                 values=ordered)


# ---- ヒストグラム（MFC MakeHistogram、NiceCeil。FR-013、AR-043） ----

@dataclass
class Histogram:
    start_us: int = 0      # left edge of bin 0
    width_us: int = 1      # 1, 2 or 5 x 10^m
    counts: list[int] = field(default_factory=list)  # bin i: [start + i width, start + (i + 1) width)


def nice_ceil(x: float) -> float:
    """1・2・5 × 10^m のうち x 以上で最小の値（x > 0）。MFC NiceCeil と同じ計算と許容（1e-9）。"""
    p = math.pow(10.0, math.floor(math.log10(x)))
    m = x / p
    if m <= 1.0 + 1e-9:
        step = 1.0
    elif m <= 2.0 + 1e-9:
        step = 2.0
    elif m <= 5.0 + 1e-9:
        step = 5.0
    else:
        step = 10.0
    return step * p


def _llround(x: float) -> int:
    # std::llround rounds half away from zero; the widths are positive
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def make_histogram(sorted_values) -> Histogram:
    """およそ clamp(ceil(sqrt(n)), 10, 50) 本の、きりのよい幅のビン。件数の合計は n。値がなければ空、全部同じなら 1 本。"""
    h = Histogram()
    if len(sorted_values) == 0:
        return h
    lo = sorted_values[0]
    hi = sorted_values[-1]
    if hi == lo:
        h.start_us = lo
        h.width_us = 1
        h.counts = [len(sorted_values)]
        return h
    n = float(len(sorted_values))
    target = max(10, min(50, int(math.ceil(math.sqrt(n)))))
    h.width_us = max(1, _llround(nice_ceil(float(hi - lo) / target)))
    h.start_us = (lo // h.width_us) * h.width_us  # floor division, also for negative values
    bins = (hi - h.start_us) // h.width_us + 1
    counts = [0] * bins
    for v in sorted_values:
        counts[(v - h.start_us) // h.width_us] += 1
    h.counts = counts
    return h