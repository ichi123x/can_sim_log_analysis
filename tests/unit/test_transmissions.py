"""collect_transmissions（FR-010、FR-011、AR-040、AR-041、MFC CollectTransmissions、research.md R-5）。"""

from can_log_analysis.analysis import Transmission, collect_transmissions
from can_log_analysis.log_reader import read_log_records

from conftest import log_row


def collect(make_project, rows):
    project = make_project(rows)
    return collect_transmissions(read_log_records(str(project) + ".log.csv"))


def test_rows_of_one_transmission_become_one_ar040(make_project):
    rows = [log_row(can_id="0x080", tx=3, rx=rx, req=10, start=20) for rx in (1, 2, 4)]
    transmissions, overwrites = collect(make_project, rows)
    assert transmissions == [Transmission(can_id=0x080, tx_node=3, tx_request=10, tx_start=20)]
    assert overwrites == 0


def test_sorted_by_can_id_then_start_then_node(make_project):
    rows = [
        log_row(can_id="0x100", tx=1, req=0, start=500),
        log_row(can_id="0x080", tx=2, req=0, start=300),
        log_row(can_id="0x100", tx=1, req=0, start=100),
        log_row(can_id="0x080", tx=1, req=0, start=300),
    ]
    transmissions, _ = collect(make_project, rows)
    assert [(t.can_id, t.tx_start, t.tx_node) for t in transmissions] == [
        (0x080, 300, 1), (0x080, 300, 2), (0x100, 100, 1), (0x100, 500, 1)]


def test_first_row_of_a_transmission_is_kept_r5(make_project):
    rows = [log_row(can_id="0x080", tx=1, req=5, start=20), log_row(can_id="0x080", tx=1, req=7, start=20)]
    transmissions, _ = collect(make_project, rows)
    assert [t.tx_request for t in transmissions] == [5]


def test_overwrite_rows_are_counted_and_left_out_ar041(make_project):
    rows = [
        log_row(can_id="0x080", start=0),
        log_row(can_id="0x080", start=1000, status="OVERWRITE"),
        log_row(can_id="0x080", start=2000, status="OVERWRITE"),
    ]
    transmissions, overwrites = collect(make_project, rows)
    assert [t.tx_start for t in transmissions] == [0]
    assert overwrites == 2


def test_rows_without_request_or_start_are_left_out(make_project):
    rows = [log_row(start=0), log_row(req="", start=100), log_row(req=200, start="")]
    transmissions, _ = collect(make_project, rows)
    assert [t.tx_start for t in transmissions] == [0]


def test_rows_without_receiver_are_transmissions(make_project):
    transmissions, _ = collect(make_project, [log_row(rx="", start=0), log_row(rx=0, start=100)])
    assert [t.tx_start for t in transmissions] == [0, 100]
