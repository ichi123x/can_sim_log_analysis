"""コマンドライン can-log-analysis（contracts/cli.md）。"""

import argparse
import io
import sys
from pathlib import Path

from can_log_analysis.analysis import analyze_latency, analyze_tx_wait
from can_log_analysis.log_reader import read_log_records
from can_log_analysis.project import open_project
from can_log_analysis.tables import latency_table, tx_wait_table, write_table_csv

# The order of the MFC "解析" menu (AR-090); busload and jitter come with US3 and US2
_KINDS = {
    "latency": lambda records, name: latency_table(analyze_latency(records), name),
    "txwait": lambda records, name: tx_wait_table(analyze_tx_wait(records), name),
}
_CHOICES = ["all", "latency", "busload", "txwait", "jitter"]


def _parse(argv):
    parser = argparse.ArgumentParser(
        prog="can-log-analysis",
        description="CAN バスシミュレータ（MFC 版）のフレームログを解析し、MFC 版と同じ表を CSV で出す。")
    parser.add_argument("project", metavar="PROJECT", help=".canprj のパス（ログは PROJECT.log.csv）")
    parser.add_argument("-a", "--analysis", action="append", choices=_CHOICES, metavar="KIND",
                        help="all（既定）、latency、busload、txwait、jitter。複数回指定できる")
    parser.add_argument("-o", "--output-dir", metavar="DIR", help="表ごとに DIR/<kind>.csv に書く。なければ標準出力")
    return parser.parse_args(argv)


def _use_utf8(stream):
    # Output does not depend on the console code page (research.md R-7)
    if isinstance(stream, io.TextIOWrapper):
        stream.reconfigure(encoding="utf-8", newline="\n")


def _selected(analyses):
    if not analyses or "all" in analyses:
        return list(_KINDS)
    return [kind for kind in _KINDS if kind in analyses]


def main(argv=None) -> int:
    _use_utf8(sys.stdout)
    _use_utf8(sys.stderr)
    args = _parse(argv)
    project = open_project(args.project)
    records = read_log_records(project.log_path)
    # every table is made before anything is written
    tables = [_KINDS[kind](records, project.name) for kind in _selected(args.analysis)]
    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for table in tables:
            with open(out_dir / f"{table.kind}.csv", "w", encoding="utf-8", newline="\n") as out:
                write_table_csv(table, out)
    else:
        for i, table in enumerate(tables):
            if i > 0:
                sys.stdout.write("\n")
            write_table_csv(table, sys.stdout)
        sys.stdout.flush()
    return 0
