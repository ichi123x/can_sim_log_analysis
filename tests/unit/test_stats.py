"""compute_stats（FR-012、AR-042、MFC ComputeStats）。"""

from array import array

from can_log_analysis.stats import compute_stats


def stats(values):
    return compute_stats(array("q", values))


def test_sorted_values_are_kept_as_array():
    s = stats([5, 1, 3])
    assert isinstance(s.values, array) and s.values.typecode == "q"
    assert list(s.values) == [1, 3, 5]


def test_count_min_max_mean():
    s = stats([246, 498, 246])
    assert (s.count, s.min_us, s.max_us, s.mean_us) == (3, 246, 498, 330.0)


def test_p95_nearest_rank_ar042():
    assert stats(range(1, 21)).p95_us == 19      # ceil(0.95 * 20) = 19
    assert stats(range(1, 101)).p95_us == 95     # ceil(0.95 * 100) = 95
    assert stats(range(1, 102)).p95_us == 96     # ceil(0.95 * 101) = 96
    assert stats([7]).p95_us == 7
    assert stats([246, 246, 498]).p95_us == 498  # ceil(2.85) = 3


def test_mean_is_sum_over_count():
    assert stats([0, 252]).mean_us == 126.0
    assert stats([1, 2]).mean_us == 1.5
    assert stats([-3, 1]).mean_us == -1.0


def test_no_values_are_all_zero_ar042():
    s = stats([])
    assert (s.count, s.min_us, s.max_us, s.mean_us, s.p95_us) == (0, 0, 0, 0.0, 0)
    assert len(s.values) == 0
