"""analyze_bus_load（FR-031〜FR-035、AR-080〜AR-083、MFC AnalyzeBusLoad）。"""

from can_log_analysis.analysis import analyze_bus_load
from can_log_analysis.log_reader import read_log_records

from conftest import DATA_DIR, log_row


def analyze(make_project, rows):
    return analyze_bus_load(read_log_records(str(make_project(rows)) + ".log.csv"))


def test_as001_us3_scenario1():
    a = analyze_bus_load(read_log_records(DATA_DIR / "as001" / "as001.canprj.log.csv"))
    assert (a.section_us, a.range_us, a.transmission_count) == (10000, 10010000, 2)
    assert [(e.node, e.frame_count, e.busy_us) for e in a.ecus] == [(1, 1, 246), (3, 1, 246)]
    assert a.max_section == 1000
    assert a.max_pct == 100.0 * 492 / 10000


def test_transmission_over_a_section_boundary_us3_scenario2_fr032(make_project):
    a = analyze(make_project, [log_row(start=9990, end=10010)])
    assert a.range_us == 20000
    assert a.section_pct == [100.0 * 10 / 10000, 100.0 * 10 / 10000]
    assert a.section_pct[0] == 0.1


def test_no_transmissions_us3_scenario3(make_project):
    a = analyze(make_project, [])
    assert (a.range_us, a.average_pct, a.max_pct, a.max_section, a.ecus, a.transmission_count) == \
        (10000, 0.0, 0.0, 0, [], 0)
    assert a.section_pct == [0.0]


def test_rows_left_out_and_request_not_needed_r5(make_project):
    rows = [
        log_row(tx=1, start=100, end=100),             # Tx_End == Tx_Start
        log_row(tx=1, start=200, end=150),             # Tx_End < Tx_Start
        log_row(tx=1, start="", end=300),              # no Tx_Start
        log_row(tx=1, start=400, end=500, status="OVERWRITE"),
        log_row(tx=2, req="", start=1000, end=1250),   # no Tx_Request: still on the bus
    ]
    a = analyze(make_project, rows)
    assert a.transmission_count == 1
    assert [(e.node, e.frame_count, e.busy_us) for e in a.ecus] == [(2, 1, 250)]


def test_receivers_of_one_transmission_count_once_with_the_first_end(make_project):
    rows = [log_row(can_id="0x080", tx=1, rx=rx, start=0, end=end) for rx, end in ((2, 246), (3, 999), (4, 246))]
    a = analyze(make_project, rows)
    assert a.transmission_count == 1
    assert a.ecus[0].busy_us == 246


def test_first_section_with_the_maximum_fr033(make_project):
    rows = [log_row(can_id="0x080", start=1000, end=2000), log_row(can_id="0x100", start=21000, end=22000)]
    a = analyze(make_project, rows)
    assert a.section_pct == [10.0, 0.0, 10.0]
    assert (a.max_pct, a.max_section) == (10.0, 0)


def test_percentages_multiply_then_divide_fr033_fr035(make_project):
    rows = [log_row(tx=1, can_id="0x080", start=0, end=333), log_row(tx=2, can_id="0x100", start=5000, end=5111)]
    a = analyze(make_project, rows)
    assert a.average_pct == 100.0 * 444 / 10000
    assert [e.usage_pct for e in a.ecus] == [100.0 * 333 / 10000, 100.0 * 111 / 10000]
    assert [e.node for e in a.ecus] == [1, 2]
