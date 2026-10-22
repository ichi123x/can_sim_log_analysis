"""analyze_jitter（FR-026〜FR-028、FR-030、AR-070〜AR-072、MFC AnalyzeJitter）。"""

import math
import statistics

from can_log_analysis.analysis import JitterPoint, analyze_jitter
from can_log_analysis.log_reader import read_log_records

from conftest import log_row


def analyze(make_project, rows):
    return analyze_jitter(read_log_records(str(make_project(rows)) + ".log.csv"))


def sends(can_id, tx, pairs, rx=2, status="SUCCESS"):
    return [log_row(can_id=can_id, tx=tx, rx=rx, req=req, start=start, status=status) for req, start in pairs]


def test_us2_scenario1_fr026(make_project):
    row = analyze(make_project, sends("0x100", 1, [(0, 0), (10000, 10100), (20000, 20000)])).rows[0]
    assert (row.can_id, row.tx_node, row.period_us, row.count, row.min_us, row.max_us) == (0x100, 1, 10000, 2, -100, 100)
    assert row.std_dev_us == 100.0
    assert row.points == [JitterPoint(10100, 100), JitterPoint(20000, -100)]


def test_sent_once_fr028(make_project):
    row = analyze(make_project, sends("0x100", 1, [(0, 0)])).rows[0]
    assert (row.period_us, row.count, row.min_us, row.max_us, row.std_dev_us, row.points) == (0, 0, 0, 0, 0.0, [])


def test_period_is_the_most_frequent_interval_smaller_on_tie_fr027(make_project):
    row = analyze(make_project, sends("0x100", 1, [(0, 0), (10000, 10000), (22500, 22500)])).rows[0]
    assert row.period_us == 10000
    # intervals 12500, 10000, 12500 -> 12500 is the most frequent
    row = analyze(make_project, sends("0x100", 1, [(0, 0), (12500, 12500), (22500, 22500), (35000, 35000)])).rows[0]
    assert row.period_us == 12500


def test_rows_by_can_id(make_project):
    rows = sends("0x300", 2, [(0, 0), (10, 10)]) + sends("0x050", 1, [(0, 0), (10, 10)])
    assert [r.can_id for r in analyze(make_project, rows).rows] == [0x050, 0x300]


def test_one_transmission_per_receivers(make_project):
    rows = []
    for req, start in [(0, 0), (10000, 10050)]:
        rows += [log_row(can_id="0x100", tx=1, rx=rx, req=req, start=start) for rx in (2, 3, 4)]
    row = analyze(make_project, rows).rows[0]
    assert (row.count, row.points) == (1, [JitterPoint(10050, 50)])


def test_overwritten_transmission_is_not_jitter_ar070(make_project):
    # the second request is discarded; the request interval grows to 20000 and the start interval with it
    rows = sends("0x100", 1, [(0, 0)]) + sends("0x100", 1, [(10000, 10000)], status="OVERWRITE") + \
        sends("0x100", 1, [(20000, 20000)])
    row = analyze(make_project, rows).rows[0]
    assert (row.count, row.min_us, row.max_us, row.period_us) == (1, 0, 0, 20000)


def test_std_dev_is_summed_in_time_order_r4(make_project):
    starts = [0, 10003, 20001, 30007, 40000, 50011, 60002]
    rows = sends("0x100", 1, [(i * 10000, s) for i, s in enumerate(starts)])
    row = analyze(make_project, rows).rows[0]
    deviations = [p.deviation_us for p in row.points]
    mean = float(sum(deviations)) / len(deviations)
    squares = 0.0
    for v in deviations:
        d = float(v) - mean
        squares += d * d
    assert row.std_dev_us == math.sqrt(squares / len(deviations))
    assert math.isclose(row.std_dev_us, statistics.pstdev(deviations))
