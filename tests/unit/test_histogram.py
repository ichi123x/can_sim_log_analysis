"""make_histogram（FR-013、AR-043、MFC MakeHistogram / NiceCeil）。"""

from array import array

from can_log_analysis.stats import make_histogram, nice_ceil


def hist(values):
    return make_histogram(array("q", sorted(values)))


def test_0_to_99():
    h = hist(range(100))
    assert (h.start_us, h.width_us, h.counts) == (0, 10, [10] * 10)


def test_all_equal_values_one_bin():
    h = hist([246, 246, 246])
    assert (h.start_us, h.width_us, h.counts) == (246, 1, [3])


def test_no_values():
    h = hist([])
    assert h.counts == []


def test_negative_start_is_floored():
    # 29 values -13..15: target 10 bins, (15 - -13) / 10 = 2.8 -> width 5, start floor(-13 / 5) * 5 = -15
    h = hist(range(-13, 16))
    assert (h.start_us, h.width_us) == (-15, 5)
    assert h.counts == [3, 5, 5, 5, 5, 5, 1]


def test_target_is_capped_at_50_bins():
    # ceil(sqrt(10000)) = 100 -> 50; 9999 / 50 = 199.98 -> width 200
    h = hist(range(10000))
    assert (h.start_us, h.width_us, h.counts) == (0, 200, [200] * 50)


def test_target_is_at_least_10_bins():
    # 20 values from 0 to 37: ceil(sqrt(20)) = 5 -> 10; 37 / 10 = 3.7 -> width 5
    values = [0, 37] + list(range(1, 19))
    h = hist(values)
    assert (h.start_us, h.width_us) == (0, 5)
    assert len(h.counts) == 8
    assert sum(h.counts) == 20


def test_counts_add_up():
    values = [3, 3, 7, 100, 250, 251, 999, 1000]
    assert sum(hist(values).counts) == len(values)


def test_nice_ceil():
    assert [nice_ceil(x) for x in (0.3, 1.0, 1.5, 2.0, 2.01, 3.7, 5.0, 7.0, 199.98, 1000.0)] == \
        [0.5, 1.0, 2.0, 2.0, 5.0, 5.0, 5.0, 10.0, 200.0, 1000.0]
