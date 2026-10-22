"""4 つの解析（MFC LogAnalysis.cpp の AnalyzeLatency、AnalyzeTxWait、AnalyzeJitter、AnalyzeBusLoad）。

関数は MFC と 1 対 1 に対応させ、条件・並び順・浮動小数点の計算順を合わせる（research.md R-4、R-5）。
"""

import math
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

    MFC と同じく CAN ID ごとに分けて集める。ログは時刻順なので、ID ごとの送信はふつう既に (送信開始, 送信ノード) 順で、
    並べ替えずに済む。並んでいない ID だけ並べ替える。全体を 1 回で並べ替えると、300 万行で 0.2 秒以上 GIL を
    握ったままになり、画面（機能 002）が止まるため（002 research R-3 の追記）。
    """
    overwrites = 0
    buckets: dict[int, dict[tuple[int, int], int]] = {}  # can_id -> (tx_start, tx_node) -> tx_request, in log order
    status = records.status
    tx_request, tx_start, tx_node = records.tx_request, records.tx_start, records.tx_node
    for i, can_id in enumerate(records.can_id):
        if status[i] == OVERWRITE:
            overwrites += 1
            continue
        request = tx_request[i]
        start = tx_start[i]
        if request < 0 or start < 0:
            continue
        bucket = buckets.get(can_id)
        if bucket is None:
            bucket = buckets[can_id] = {}
        key = (start, tx_node[i])
        if key not in bucket:
            bucket[key] = request
    transmissions = []
    for can_id in sorted(buckets):
        items = list(buckets.pop(can_id).items())  # pop: each bucket is freed on its own, not all at the end
        if any(items[k][0] > items[k + 1][0] for k in range(len(items) - 1)):
            items.sort()
        transmissions.extend(Transmission(can_id=can_id, tx_node=node, tx_request=request, tx_start=start)
                             for (start, node), request in items)
        _release(items)
    return transmissions, overwrites


def _release(objects: list, step: int = 50_000):
    """大きなリストを末尾から少しずつ空にする。一度に解放すると 75 万件で 0.1 秒 GIL を握り続けるため（画面の応答）。"""
    while objects:
        del objects[-step:]


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
    _release(transmissions)
    return TxWaitAnalysis(rows=rows, overwrite_count=overwrites)

# ---- 送信ジッタ ----

@dataclass(frozen=True)
class JitterPoint:
    time_us: int       # Tx_Start of the later transmission
    deviation_us: int  # start interval - request interval (+ late, - early)


@dataclass
class JitterRow:
    can_id: int = 0
    tx_node: int = 0
    period_us: int = 0      # the most frequent request interval (the smaller on a tie); 0 if sent once
    count: int = 0          # transmissions - 1
    min_us: int = 0
    max_us: int = 0
    std_dev_us: float = 0.0  # population standard deviation
    points: list[JitterPoint] = field(default_factory=list)  # by time


@dataclass
class JitterAnalysis:
    rows: list[JitterRow]  # CAN ID ascending


def analyze_jitter(records: LogRecords) -> JitterAnalysis:
    """CAN ID ごとに (Start[k] - Start[k-1]) - (Request[k] - Request[k-1])。MFC AnalyzeJitter。"""
    transmissions, _ = collect_transmissions(records)
    rows = []
    begin = 0
    n = len(transmissions)
    while begin < n:
        end = begin
        while end < n and transmissions[end].can_id == transmissions[begin].can_id:
            end += 1
        row = JitterRow(can_id=transmissions[begin].can_id, tx_node=transmissions[begin].tx_node)
        intervals: dict[int, int] = {}  # request interval -> how often
        for k in range(begin + 1, end):
            prev, cur = transmissions[k - 1], transmissions[k]
            request_interval = cur.tx_request - prev.tx_request
            row.points.append(JitterPoint(cur.tx_start, (cur.tx_start - prev.tx_start) - request_interval))
            intervals[request_interval] = intervals.get(request_interval, 0) + 1
        row.count = len(row.points)
        if row.count > 0:
            best = 0
            for interval, times in sorted(intervals.items()):  # ascending, so a tie keeps the smaller interval
                if times > best:
                    best = times
                    row.period_us = interval
            deviations = [p.deviation_us for p in row.points]
            row.min_us = min(deviations)
            row.max_us = max(deviations)
            # The same order of double operations as MFC (research.md R-4): no fsum, no statistics
            mean = float(sum(deviations)) / row.count
            squares = 0.0
            for v in deviations:
                d = float(v) - mean
                squares += d * d
            row.std_dev_us = math.sqrt(squares / row.count)  # population, as the summary CSV
        rows.append(row)
        begin = end
    _release(transmissions)
    return JitterAnalysis(rows=rows)

# ---- CAN バス負荷 ----

@dataclass
class EcuBusUsage:
    node: int = 0
    frame_count: int = 0
    busy_us: int = 0
    usage_pct: float = 0.0  # busy_us / range_us


@dataclass
class BusLoadAnalysis:
    section_us: int = 10000
    range_us: int = 10000  # 0 .. the section holding the last Tx_End
    section_pct: list[float] = field(default_factory=list)
    average_pct: float = 0.0  # busy time / range_us
    max_pct: float = 0.0
    max_section: int = 0      # first section with max_pct
    ecus: list[EcuBusUsage] = field(default_factory=list)  # senders only, by node number
    transmission_count: int = 0


def analyze_bus_load(records: LogRecords) -> BusLoadAnalysis:
    """送信ごと（(Tx_Node, CAN_ID, Tx_Start) で 1 回）に、バスは [Tx_Start, Tx_End) の間使用中。MFC AnalyzeBusLoad。

    条件は collect_transmissions と違う: Tx_Request は見ず、Tx_End > Tx_Start の送信だけ（research.md R-5）。
    """
    result = BusLoadAnalysis()
    seen = set()
    transmissions = []  # (tx_node, tx_start, tx_end) of the first row of each transmission
    last_end = 0
    status, tx_node, can_id = records.status, records.tx_node, records.can_id
    tx_start, tx_end = records.tx_start, records.tx_end
    for i in range(len(records)):
        start = tx_start[i]
        end = tx_end[i]
        if status[i] == OVERWRITE or start < 0 or end <= start:
            continue
        key = (tx_node[i], can_id[i], start)
        if key in seen:
            continue  # the same transmission seen by another receiver
        seen.add(key)
        transmissions.append((tx_node[i], start, end))
        last_end = max(last_end, end)
    result.transmission_count = len(transmissions)
    while seen:  # free the set bit by bit (one free of 750k keys keeps the GIL for 0.1 s)
        seen.pop()

    section = result.section_us
    result.range_us = section if last_end <= 0 else ((last_end + section - 1) // section) * section
    busy = [0] * (result.range_us // section)
    ecus: dict[int, EcuBusUsage] = {}
    total = 0
    for node, start, end in transmissions:
        t = start
        while t < end:
            index = t // section
            stop = min(end, (index + 1) * section)
            busy[index] += stop - t
            t = stop
        duration = end - start
        total += duration
        e = ecus.get(node)
        if e is None:
            e = ecus[node] = EcuBusUsage(node=node)
        e.frame_count += 1
        e.busy_us += duration
    _release(transmissions)

    for i, b in enumerate(busy):
        pct = 100.0 * float(b) / float(section)
        result.section_pct.append(pct)
        if pct > result.max_pct:
            result.max_pct = pct
            result.max_section = i
    range_us = float(result.range_us)
    result.average_pct = 100.0 * float(total) / range_us
    for node in sorted(ecus):
        e = ecus[node]
        e.usage_pct = 100.0 * float(e.busy_us) / range_us
        result.ecus.append(e)
    return result