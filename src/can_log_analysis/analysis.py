"""4 つの解析（MFC LogAnalysis.cpp の AnalyzeLatency、AnalyzeTxWait、AnalyzeJitter、AnalyzeBusLoad）。

関数は MFC と 1 対 1 に対応させ、条件・並び順・浮動小数点の計算順を合わせる（research.md R-4、R-5）。
"""

from array import array
from dataclasses import dataclass, field

from can_log_analysis.log_reader import OVERWRITE, LogRecords
from can_log_analysis.stats import Stats, compute_stats


@dataclass(frozen=True)
class Transmission:
    """1 回の送信（ログは受信ノードの数だけ同じ送信を並べる）。"""

    can_id: int
    tx_node: int
    tx_request: int
    tx_start: int


def collect_transmissions(records: LogRecords) -> tuple[list[Transmission], int]:
    """送信された行（OVERWRITE でなく、送信要求と送信開始がある）を (CAN ID, 送信開始, 送信ノード) で
    1 回にまとめ、その順に並べる。返り値は (送信, OVERWRITE の行数)。MFC CollectTransmissions。

    同じキーの行が複数あれば最初の行を残す（research.md R-5）。
    """
    overwrites = 0
    seen = {}
    status = records.status
    for i, can_id in enumerate(records.can_id):
        if status[i] == OVERWRITE:
            overwrites += 1
            continue
        request = records.tx_request[i]
        start = records.tx_start[i]
        if request < 0 or start < 0:
            continue
        key = (can_id, start, records.tx_node[i])
        if key not in seen:
            seen[key] = request
    transmissions = [
        Transmission(can_id=can_id, tx_node=node, tx_request=request, tx_start=start)
        for (can_id, start, node), request in sorted(seen.items())
    ]
    return transmissions, overwrites


# ---- 受信完了時間 ----

@dataclass
class LatencyRow:
    tx_node: int = 0  # 0 / 0: the row of every receive
    rx_node: int = 0
    stats: Stats = field(default_factory=Stats)


@dataclass
class LatencyAnalysis:
    rows: list[LatencyRow]    # [0] = all, then (tx_node, rx_node) ascending
    overwrite_count: int = 0  # discarded rows, not in the table


def analyze_latency(records: LogRecords) -> LatencyAnalysis:
    """Rx_End - Tx_Request を、受信ノードがあり送信された行（OVERWRITE でない）ごとに 1 件。MFC AnalyzeLatency。"""
    overwrites = 0
    every = array("q")
    pairs: dict[tuple[int, int], array] = {}
    status, tx_node, rx_node = records.status, records.tx_node, records.rx_node
    tx_request, rx_end = records.tx_request, records.rx_end
    for i in range(len(records)):
        if status[i] == OVERWRITE:
            overwrites += 1
            continue
        rx = rx_node[i]
        end = rx_end[i]
        request = tx_request[i]
        if rx <= 0 or end < 0 or request < 0:
            continue
        t = end - request
        every.append(t)
        key = (tx_node[i], rx)
        values = pairs.get(key)
        if values is None:
            values = pairs[key] = array("q")
        values.append(t)
    rows = [LatencyRow(stats=compute_stats(every))]
    for (tx, rx), values in sorted(pairs.items()):
        rows.append(LatencyRow(tx_node=tx, rx_node=rx, stats=compute_stats(values)))
    return LatencyAnalysis(rows=rows, overwrite_count=overwrites)


# ---- 送信待ち時間 ----

@dataclass
class TxWaitRow:
    is_all: bool = False  # the row of every transmission
    can_id: int = 0
    tx_node: int = 0      # the sender of the first (earliest) transmission of the ID
    stats: Stats = field(default_factory=Stats)


@dataclass
class TxWaitAnalysis:
    rows: list[TxWaitRow]     # [0] = all, then CAN ID ascending
    overwrite_count: int = 0  # discarded rows, not in the table


def analyze_tx_wait(records: LogRecords) -> TxWaitAnalysis:
    """Tx_Start - Tx_Request を送信ごとに 1 件。MFC AnalyzeTxWait。"""
    transmissions, overwrites = collect_transmissions(records)
    every = array("q")
    ids: list[tuple[int, int, array]] = []  # (can_id, tx_node, waits); transmissions are sorted by CAN ID
    for t in transmissions:
        wait = t.tx_start - t.tx_request
        every.append(wait)
        if not ids or ids[-1][0] != t.can_id:
            ids.append((t.can_id, t.tx_node, array("q")))
        ids[-1][2].append(wait)
    rows = [TxWaitRow(is_all=True, stats=compute_stats(every))]
    for can_id, node, values in ids:
        rows.append(TxWaitRow(can_id=can_id, tx_node=node, stats=compute_stats(values)))
    return TxWaitAnalysis(rows=rows, overwrite_count=overwrites)