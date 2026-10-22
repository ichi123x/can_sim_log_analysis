"""analyze_tx_wait（FR-023、FR-024、AR-060、AR-061、AS-001、MFC AnalyzeTxWait）。"""

from can_log_analysis.analysis import analyze_tx_wait
from can_log_analysis.log_reader import read_log_records

from conftest import DATA_DIR, log_row


def analyze(make_project, rows):
    return analyze_tx_wait(read_log_records(str(make_project(rows)) + ".log.csv"))


def summary(row):
    s = row.stats
    return (row.is_all, row.can_id, row.tx_node, s.count, s.min_us, s.mean_us, s.max_us, s.p95_us)


def test_as001():
    a = analyze_tx_wait(read_log_records(DATA_DIR / "as001" / "as001.canprj.log.csv"))
    assert [summary(r) for r in a.rows] == [
        (True, 0, 0, 2, 0, 126.0, 252, 252),
        (False, 0x080, 3, 1, 0, 0.0, 0, 0),
        (False, 0x100, 1, 1, 252, 252.0, 252, 252),
    ]
    assert a.overwrite_count == 0


def test_one_transmission_per_receivers_ar040(make_project):
    rows = [log_row(can_id="0x080", tx=3, rx=rx, req=0, start=40) for rx in (1, 2, 4)]
    assert summary(analyze(make_project, rows).rows[1]) == (False, 0x080, 3, 1, 40, 40.0, 40, 40)


def test_sender_of_an_id_is_the_earliest_transmission_fr024(make_project):
    rows = [log_row(can_id="0x080", tx=5, req=200, start=200), log_row(can_id="0x080", tx=2, req=100, start=100)]
    row = analyze(make_project, rows).rows[1]
    assert (row.can_id, row.tx_node, row.stats.count) == (0x080, 2, 2)


def test_rows_by_can_id(make_project):
    rows = [log_row(can_id="0x300", start=0), log_row(can_id="0x050", start=0), log_row(can_id="0x100", start=0)]
    assert [r.can_id for r in analyze(make_project, rows).rows[1:]] == [0x050, 0x100, 0x300]


def test_negative_wait_is_kept(make_project):
    row = analyze(make_project, [log_row(req=100, start=40)]).rows[1]
    assert (row.stats.min_us, row.stats.mean_us) == (-60, -60.0)


def test_overwrite_count_fr025(make_project):
    rows = [log_row(start=0), log_row(start=10, status="OVERWRITE"), log_row(start=20, status="OVERWRITE")]
    a = analyze(make_project, rows)
    assert a.overwrite_count == 2
    assert a.rows[0].stats.count == 1


def test_header_only_gives_the_all_row_only(make_project):
    assert [summary(r) for r in analyze(make_project, []).rows] == [(True, 0, 0, 0, 0, 0.0, 0, 0)]
