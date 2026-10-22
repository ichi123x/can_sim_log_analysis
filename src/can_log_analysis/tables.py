"""表（MFC の解析画面の表）と表 CSV（contracts/table-csv.md）。"""

from dataclasses import dataclass, field
from typing import TextIO

from can_log_analysis import formatting as f
from can_log_analysis.analysis import BusLoadAnalysis, JitterAnalysis, LatencyAnalysis, TxWaitAnalysis

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

def jitter_table(a: JitterAnalysis, project_name: str) -> Table:
    """MFC CJitterDlg::CreateContent。送信 1 回の ID（件数 0）は周期以降を空欄にする。"""
    rows = []
    for row in a.rows:
        if row.count == 0:
            rows.append([f.can_id_text(row.can_id), f.ecu_name(row.tx_node), "", f.integer(row.count), "", "", ""])
            continue
        rows.append([
            f.can_id_text(row.can_id), f.ecu_name(row.tx_node), f.period_text(row.period_us), f.integer(row.count),
            f.integer(row.min_us), f.integer(row.max_us), f.fixed1(row.std_dev_us),
        ])
    return Table(kind="jitter", title=f.IDS_JIT_TITLE % project_name, note=f.IDS_JIT_NOTE,
                 columns=f.columns(f.IDS_JIT_COLUMNS), rows=rows)

def bus_load_table(a: BusLoadAnalysis, project_name: str) -> Table:
    """MFC CBusLoadDlg::CreateContent。2 行目は要約（平均、最大とその区間、範囲）。"""
    section_ms = a.section_us // 1000
    summary = f.IDS_BUS_SUMMARY % (
        f.fixed1(a.average_pct), f.fixed1(a.max_pct),
        f.integer(a.max_section * section_ms), f.integer((a.max_section + 1) * section_ms),
        f.integer(a.range_us // 1000))
    rows = [[f.ecu_name(e.node), f.integer(e.frame_count), f.fixed1(e.usage_pct)] for e in a.ecus]
    return Table(kind="busload", title=f.IDS_BUS_TITLE % project_name, note=summary,
                 columns=f.columns(f.IDS_BUS_COLUMNS), rows=rows)