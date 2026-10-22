"""MFC 版 CAN バスシミュレータのフレームログを解析する（contracts/core-api.md）。

画面に依存しない解析コア。コマンドライン（can_log_analysis.cli）と画面機能から使う。
"""

from can_log_analysis.analysis import (
    BusLoadAnalysis, EcuBusUsage, JitterAnalysis, JitterPoint, JitterRow, LatencyAnalysis, LatencyRow, Transmission,
    TxWaitAnalysis, TxWaitRow, analyze_bus_load, analyze_jitter, analyze_latency, analyze_tx_wait,
    collect_transmissions)
from can_log_analysis.errors import (
    CanLogAnalysisError, LogNotFoundError, LogReadCancelled, LogReadError, ProjectNotFoundError, ProjectReadError)
from can_log_analysis.formatting import can_id_text, ecu_name, fixed1, period_text
from can_log_analysis.log_reader import LogRecords, read_log_records
from can_log_analysis.project import Project, open_project
from can_log_analysis.stats import Histogram, Stats, make_histogram
from can_log_analysis.tables import (
    Table, bus_load_table, jitter_table, latency_table, tx_wait_table, write_table_csv)

__all__ = [
    "open_project", "Project",
    "read_log_records", "LogRecords",
    "analyze_latency", "analyze_tx_wait", "analyze_jitter", "analyze_bus_load", "collect_transmissions",
    "LatencyAnalysis", "LatencyRow", "TxWaitAnalysis", "TxWaitRow", "JitterAnalysis", "JitterRow", "JitterPoint",
    "BusLoadAnalysis", "EcuBusUsage", "Transmission",
    "Stats", "Histogram", "make_histogram",
    "Table", "latency_table", "bus_load_table", "tx_wait_table", "jitter_table", "write_table_csv",
    "ecu_name", "can_id_text", "fixed1", "period_text",
    "CanLogAnalysisError", "ProjectNotFoundError", "ProjectReadError", "LogNotFoundError", "LogReadError",
    "LogReadCancelled",
]
