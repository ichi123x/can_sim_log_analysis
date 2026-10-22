"""解析コアの公開 API（FR-030、FR-033、FR-039、contracts/core-api.md、US5）。"""

import can_log_analysis
from can_log_analysis import analyze_bus_load, analyze_jitter, analyze_latency, analyze_tx_wait, read_log_records

from conftest import DATA_DIR

PUBLIC = [
    "open_project", "read_log_records", "analyze_latency", "analyze_tx_wait", "analyze_jitter", "analyze_bus_load",
    "collect_transmissions", "make_histogram", "latency_table", "bus_load_table", "tx_wait_table", "jitter_table",
    "ecu_name", "can_id_text", "fixed1", "period_text", "write_table_csv",
    "CanLogAnalysisError", "ProjectNotFoundError", "ProjectReadError", "LogNotFoundError", "LogReadError",
    "LogReadCancelled",
]

SAMPLE = DATA_DIR / "sample_vehicle_16ecu" / "sample_vehicle_16ecu.canprj.log.csv"


def test_public_names():
    for name in PUBLIC:
        assert hasattr(can_log_analysis, name), name
    assert set(PUBLIC) <= set(can_log_analysis.__all__)


def test_data_for_the_graphs_fr030_fr033():
    records = read_log_records(SAMPLE)
    row = analyze_jitter(records).rows[0]
    assert len(row.points) == row.count > 0
    assert all(a.time_us <= b.time_us for a, b in zip(row.points, row.points[1:]))
    bus = analyze_bus_load(records)
    assert len(bus.section_pct) == bus.range_us // bus.section_us


def test_analyses_do_not_change_the_records():
    records = read_log_records(SAMPLE)
    columns = ("can_id", "tx_node", "rx_node", "tx_request", "tx_start", "tx_end", "rx_end", "status")
    before = {c: bytes(getattr(records, c)) for c in columns}
    for analyze in (analyze_latency, analyze_tx_wait, analyze_jitter, analyze_bus_load):
        analyze(records)
    assert {c: bytes(getattr(records, c)) for c in columns} == before
