"""表 CSV（FR-037、FR-038、contracts/table-csv.md）。"""

import io

import pytest

from can_log_analysis.analysis import analyze_bus_load, analyze_jitter, analyze_latency, analyze_tx_wait
from can_log_analysis.log_reader import read_log_records
from can_log_analysis.tables import (Table, bus_load_table, jitter_table, latency_table, tx_wait_table,
                                     write_table_csv)

from conftest import DATA_DIR, log_row

AS001 = DATA_DIR / "as001" / "as001.canprj.log.csv"


def written(table):
    out = io.StringIO(newline="")
    write_table_csv(table, out)
    return out.getvalue()


def test_layout_fr038():
    table = Table(kind="txwait", title="T", note="N", columns=["a", "b"], rows=[["1", ""], ["x", "y"]])
    assert written(table) == "T\nN\na,b\n1,\nx,y\n"


def test_no_rows_still_three_lines():
    assert written(Table(kind="jitter", title="T", note="N", columns=["a"], rows=[])) == "T\nN\na\n"


@pytest.mark.parametrize("cell", ["a,b", 'a"b', "a\rb", "a\nb"])
def test_cells_must_not_need_quoting(cell):
    with pytest.raises(ValueError):
        written(Table(kind="txwait", title="T", note="N", columns=["a"], rows=[[cell]]))
    with pytest.raises(ValueError):
        written(Table(kind="txwait", title=cell, note="N", columns=["a"], rows=[]))


def test_latency_table_fr021_fr022():
    t = latency_table(analyze_latency(read_log_records(AS001)), "as001.canprj")
    assert t.kind == "latency"
    assert t.title == "受信完了時間 - as001.canprj"
    assert t.note == "送信要求 → 受信完了の時間（再送は届いた 1 回を 1 件）。破棄（OVERWRITE）0 件は含みません。"
    assert t.columns == ["送信 ECU", "受信 ECU", "件数", "最小 (µs)", "平均 (µs)", "最大 (µs)", "95% (µs)"]
    assert t.rows == [
        ["全体", "", "3", "246", "330.0", "498", "498"],
        ["ECU 01", "ECU 05", "1", "498", "498.0", "498", "498"],
        ["ECU 03", "ECU 01", "1", "246", "246.0", "246", "246"],
        ["ECU 03", "ECU 05", "1", "246", "246.0", "246", "246"],
    ]


def test_tx_wait_table_fr024_fr025():
    t = tx_wait_table(analyze_tx_wait(read_log_records(AS001)), "as001.canprj")
    assert t.kind == "txwait"
    assert t.title == "送信待ち時間 - as001.canprj"
    assert t.note == "送信要求 → 送信開始の時間（送信 1 回を 1 件。再送は送れた 1 回）。破棄（OVERWRITE）0 件は含みません。"
    assert t.columns == ["CAN ID", "送信 ECU", "件数", "最小 (µs)", "平均 (µs)", "最大 (µs)", "95% (µs)"]
    assert t.rows == [
        ["全体", "", "2", "0", "126.0", "252", "252"],
        ["0x080", "ECU 03", "1", "0", "0.0", "0", "0"],
        ["0x100", "ECU 01", "1", "252", "252.0", "252", "252"],
    ]


def test_notes_carry_the_overwrite_count(make_project):
    rows = [log_row(start=0), log_row(start=10, status="OVERWRITE"), log_row(start=20, status="OVERWRITE")]
    records = read_log_records(str(make_project(rows)) + ".log.csv")
    assert "破棄（OVERWRITE）2 件は含みません。" in latency_table(analyze_latency(records), "t.canprj").note
    assert "破棄（OVERWRITE）2 件は含みません。" in tx_wait_table(analyze_tx_wait(records), "t.canprj").note

def test_jitter_table_fr028_fr029(make_project):
    rows = [log_row(can_id="0x100", tx=1, req=r, start=s) for r, s in [(0, 0), (10000, 10100), (20000, 20000)]]
    rows.append(log_row(can_id="0x0A0", tx=3, req=0, start=0))
    records = read_log_records(str(make_project(rows)) + ".log.csv")
    t = jitter_table(analyze_jitter(records), "t.canprj")
    assert t.kind == "jitter"
    assert t.title == "送信ジッター - t.canprj"
    assert t.note == "連続する送信開始の間隔 − 送信要求の間隔（正は遅れ、負は早まり）。標準偏差は件数で割った値です。"
    assert t.columns == ["CAN ID", "送信 ECU", "周期 (ms)", "件数", "最小 (µs)", "最大 (µs)", "標準偏差 (µs)"]
    assert t.rows == [
        ["0x0A0", "ECU 03", "", "0", "", "", ""],
        ["0x100", "ECU 01", "10", "2", "-100", "100", "100.0"],
    ]

def test_bus_load_table_fr034_fr035():
    t = bus_load_table(analyze_bus_load(read_log_records(AS001)), "as001.canprj")
    assert t.kind == "busload"
    assert t.title == "CAN バス負荷 - as001.canprj"
    assert t.note == "平均負荷 0.0%　最大負荷 4.9%（10000〜10010 ms）　範囲 0〜10010 ms（10 ms ごと）"
    assert t.columns == ["ECU", "送信フレーム数", "使用率 (%)"]
    assert t.rows == [["ECU 01", "1", "0.0"], ["ECU 03", "1", "0.0"]]


def test_bus_load_summary_without_transmissions(make_project):
    records = read_log_records(str(make_project([])) + ".log.csv")
    t = bus_load_table(analyze_bus_load(records), "t.canprj")
    assert t.note == "平均負荷 0.0%　最大負荷 0.0%（0〜10 ms）　範囲 0〜10 ms（10 ms ごと）"
    assert t.rows == []