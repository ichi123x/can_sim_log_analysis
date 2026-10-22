"""統計量（MFC ComputeStats。FR-012、AR-042）。"""

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
