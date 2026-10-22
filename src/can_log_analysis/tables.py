"""表（MFC の解析画面の表）と表 CSV（contracts/table-csv.md）。"""

from dataclasses import dataclass, field
from typing import TextIO

from can_log_analysis import formatting as f
from can_log_analysis.analysis import LatencyAnalysis, TxWaitAnalysis

_FORBIDDEN = (",", '"', "\r", "\n")


@dataclass
class Table:
    kind: str           # latency / busload / txwait / jitter
    title: str
    note: str           # the note under the table; the summary line for busload
    columns: list[str]
    rows: list[list[str]] = field(default_factory=list)


def _line(cells: list[str]) -> str:
    for cell in cells:
        if any(c in cell for c in _FORBIDDEN):
            raise ValueError(f"a cell contains a comma, a quote or a line break: {cell!r}")
    return ",".join(cells) + "\n"


def write_table_csv(table: Table, out: TextIO) -> None:
    """1 行目が表題、2 行目が注記、3 行目が列見出し、4 行目以降が表の行。
    out は newline="\\n"（または ""）で開いておくこと（改行は LF）。"""
    text = _line([table.title]) + _line([table.note]) + _line(table.columns)
    text += "".join(_line(row) for row in table.rows)
    out.write(text)


def latency_table(a: LatencyAnalysis, project_name: str) -> Table:
    """MFC CLatencyDlg::CreateContent。"""
    rows = []
    for i, row in enumerate(a.rows):
        s = row.stats
        rows.append([
            f.IDS_LAT_ALL if i == 0 else f.ecu_name(row.tx_node),
            "" if i == 0 else f.ecu_name(row.rx_node),
            f.integer(s.count), f.integer(s.min_us), f.fixed1(s.mean_us), f.integer(s.max_us), f.integer(s.p95_us),
        ])
    return Table(kind="latency", title=f.IDS_LAT_TITLE % project_name, note=f.IDS_LAT_NOTE % a.overwrite_count,
                 columns=f.columns(f.IDS_LAT_COLUMNS), rows=rows)


def tx_wait_table(a: TxWaitAnalysis, project_name: str) -> Table:
    """MFC CTxWaitDlg::CreateContent。"""
    rows = []
    for row in a.rows:
        s = row.stats
        rows.append([
            f.IDS_LAT_ALL if row.is_all else f.can_id_text(row.can_id),
            "" if row.is_all else f.ecu_name(row.tx_node),
            f.integer(s.count), f.integer(s.min_us), f.fixed1(s.mean_us), f.integer(s.max_us), f.integer(s.p95_us),
        ])
    return Table(kind="txwait", title=f.IDS_WAIT_TITLE % project_name, note=f.IDS_WAIT_NOTE % a.overwrite_count,
                 columns=f.columns(f.IDS_WAIT_COLUMNS), rows=rows)