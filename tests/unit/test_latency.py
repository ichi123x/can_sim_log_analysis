"""analyze_latency（FR-020、FR-021、AR-050、AR-051、AS-001、MFC AnalyzeLatency）。"""

from can_log_analysis.analysis import analyze_latency
from can_log_analysis.log_reader import read_log_records

from conftest import DATA_DIR, log_row


def analyze(make_project, rows):
    return analyze_latency(read_log_records(str(make_project(rows)) + ".log.csv"))


def summary(row):
    s = row.stats
    return (row.tx_node, row.rx_node, s.count, s.min_us, s.mean_us, s.max_us, s.p95_us)


def test_as001():
    a = analyze_latency(read_log_records(DATA_DIR / "as001" / "as001.canprj.log.csv"))
    assert [summary(r) for r in a.rows] == [
        (0, 0, 3, 246, 330.0, 498, 498),
        (1, 5, 1, 498, 498.0, 498, 498),
        (3, 1, 1, 246, 246.0, 246, 246),
        (3, 5, 1, 246, 246.0, 246, 246),
    ]
    assert a.overwrite_count == 0


def test_overwrite_rows_are_counted_not_used_fr010(make_project):
    rows = [
        log_row(tx=1, rx=2, req=0, rx_end=100),
        log_row(tx=1, rx=2, req=0, rx_end=900, status="OVERWRITE"),
        log_row(tx=1, rx=3, req=0, rx_end=900, status="OVERWRITE"),
    ]
    a = analyze(make_project, rows)
    assert a.overwrite_count == 2
    assert [summary(r) for r in a.rows] == [(0, 0, 1, 100, 100.0, 100, 100), (1, 2, 1, 100, 100.0, 100, 100)]


def test_rows_without_receiver_or_times_are_left_out_ar050(make_project):
    rows = [
        log_row(tx=1, rx=0, req=0, rx_end=100),
        log_row(tx=1, rx="", req=0, rx_end=100),
        log_row(tx=1, rx=2, req=0, rx_end=""),
        log_row(tx=1, rx=2, req="", rx_end=100),
        log_row(tx=1, rx=2, req=10, rx_end=60),
    ]
    a = analyze(make_project, rows)
    assert [summary(r) for r in a.rows] == [(0, 0, 1, 50, 50.0, 50, 50), (1, 2, 1, 50, 50.0, 50, 50)]


def test_retried_frames_count_once_per_receiver(make_project):
    rows = [log_row(tx=1, rx=2, req=0, rx_end=500, status="ARBITRATION_LOST_RETRY")]
    assert summary(analyze(make_project, rows).rows[1]) == (1, 2, 1, 500, 500.0, 500, 500)


def test_header_only_gives_the_all_row_only(make_project):
    a = analyze(make_project, [])
    assert [summary(r) for r in a.rows] == [(0, 0, 0, 0, 0.0, 0, 0)]
