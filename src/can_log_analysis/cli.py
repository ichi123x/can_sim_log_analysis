"""コマンドライン can-log-analysis（contracts/cli.md）。"""

import argparse
import io
import sys
import time
from pathlib import Path

from can_log_analysis.analysis import analyze_bus_load, analyze_jitter, analyze_latency, analyze_tx_wait
from can_log_analysis.errors import LogNotFoundError, LogReadError, ProjectNotFoundError, ProjectReadError
from can_log_analysis.formatting import IDS_LOG_NONE
from can_log_analysis.log_reader import read_log_records
from can_log_analysis.project import open_project
from can_log_analysis.tables import bus_load_table, jitter_table, latency_table, tx_wait_table, write_table_csv

# The order of the MFC "解析" menu (AR-090)
_KINDS = {
    "latency": lambda records, name: latency_table(analyze_latency(records), name),
    "busload": lambda records, name: bus_load_table(analyze_bus_load(records), name),
    "txwait": lambda records, name: tx_wait_table(analyze_tx_wait(records), name),
    "jitter": lambda records, name: jitter_table(analyze_jitter(records), name),
}
_CHOICES = ["all", "latency", "busload", "txwait", "jitter"]

# MFC IDS_ANALYZING_READ / IDS_ANALYZING_CALC (FR-042)
_READING = "ログを読み込んでいます... "
_CALCULATING = "集計しています..."
_CANCELLED = "中断しました。"
_PROGRESS_AFTER = 0.5  # seconds (constitution IV)

_now = time.monotonic  # replaced by the tests


class _Progress:
    """標準エラーへの進捗（contracts/cli.md「進捗」）。開始から 0.5 秒を超えてから出す。
    端末なら行頭復帰で同じ行を上書きし、端末でなければ 1 回 1 行。"""

    def __init__(self, stream, start: float, quiet: bool = False):
        self._stream = stream
        self._start = start
        self._quiet = quiet
        self._tty = bool(getattr(stream, "isatty", lambda: False)())
        self._percent = None
        self._open = False  # a line without its line break is on a terminal

    def _due(self) -> bool:
        return not self._quiet and _now() - self._start > _PROGRESS_AFTER

    def _show(self, text: str, overwrite: bool):
        if self._tty and overwrite:
            self._stream.write("\r" + text)
            self._open = True
        else:
            self.end()
            if self._tty:
                self._stream.write(text)
                self._open = True
            else:
                self._stream.write(text + "\n")
        self._stream.flush()

    def read(self, done: int, total: int) -> bool:
        """read_log_records の progress。中止は Ctrl+C（KeyboardInterrupt）で行うので常に続ける。"""
        if self._due():
            percent = done * 100 // total if total > 0 else 100
            if percent != self._percent:
                self._percent = percent
                self._show(f"{_READING}{percent}%", overwrite=True)
        return True

    def calc(self):
        if self._due():
            self._show(_CALCULATING, overwrite=False)

    def end(self):
        if self._open:
            self._stream.write("\n")
            self._stream.flush()
            self._open = False


def _parse(argv):
    parser = argparse.ArgumentParser(
        prog="can-log-analysis",
        description="CAN バスシミュレータ（MFC 版）のフレームログを解析し、MFC 版と同じ表を CSV で出す。")
    parser.add_argument("project", metavar="PROJECT", help=".canprj のパス（ログは PROJECT.log.csv）")
    parser.add_argument("-a", "--analysis", action="append", choices=_CHOICES, metavar="KIND",
                        help="all（既定）、latency、busload、txwait、jitter。複数回指定できる")
    parser.add_argument("-o", "--output-dir", metavar="DIR", help="表ごとに DIR/<kind>.csv に書く。なければ標準出力")
    parser.add_argument("-q", "--quiet", action="store_true", help="進捗を出さない（エラーは出す）")
    return parser.parse_args(argv)


def _use_utf8(stream):
    # Output does not depend on the console code page (research.md R-7)
    if isinstance(stream, io.TextIOWrapper):
        stream.reconfigure(encoding="utf-8", newline="\n")


def _selected(analyses):
    if not analyses or "all" in analyses:
        return list(_KINDS)
    return [kind for kind in _KINDS if kind in analyses]


def _message(text: str):
    sys.stderr.write(text + "\n")
    sys.stderr.flush()


def _write(tables, output_dir):
    if output_dir:
        out_dir = Path(output_dir)
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


def _run(args, progress: _Progress) -> int:
    try:
        project = open_project(args.project)
        records = read_log_records(project.log_path, progress=progress.read)
        progress.calc()
        # every table is made before anything is written, so a failure leaves no partial output
        tables = [_KINDS[kind](records, project.name) for kind in _selected(args.analysis)]
    except ProjectNotFoundError:
        error = f"プロジェクトファイルがありません: {args.project}"
    except ProjectReadError as e:
        error = f"プロジェクトファイルを読めません: {args.project}: {e.reason}"
    except LogNotFoundError:
        error = IDS_LOG_NONE % project.name
    except LogReadError as e:
        error = f"{e.path}: {e.message}"
    else:
        progress.end()
        try:
            _write(tables, args.output_dir)
        except OSError as e:
            path = e.filename if e.filename is not None else args.output_dir
            _message(f"出力できません: {path}: {e.strerror or e}")
            return 1
        return 0
    progress.end()
    _message(error)
    return 1


def main(argv=None) -> int:
    _use_utf8(sys.stdout)
    _use_utf8(sys.stderr)
    args = _parse(argv)
    progress = _Progress(sys.stderr, start=_now(), quiet=args.quiet)
    try:
        return _run(args, progress)
    except KeyboardInterrupt:
        progress.end()
        _message(_CANCELLED)
        return 130
