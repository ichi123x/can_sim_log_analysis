"""セルの書式（MFC AnalysisDlg.cpp と同じ書式文字列）と、表の文言（MFCApplication1.rc の文字列テーブル）。

文言は .rc からそのままコピーしている（%s、%d、%% は MFC の書式指定のまま）。
小数は printf と同じ "%.1f" で丸める。round() や Decimal は使わない（research.md R-4）。
"""

# ---- MFCApplication1.rc ----
IDS_LAT_TITLE = "受信完了時間 - %s"
IDS_LAT_COLUMNS = "送信 ECU|受信 ECU|件数|最小 (µs)|平均 (µs)|最大 (µs)|95% (µs)"
IDS_LAT_ALL = "全体"
IDS_LAT_NOTE = "送信要求 → 受信完了の時間（再送は届いた 1 回を 1 件）。破棄（OVERWRITE）%d 件は含みません。"
IDS_BUS_TITLE = "CAN バス負荷 - %s"
IDS_BUS_SUMMARY = "平均負荷 %s%%　最大負荷 %s%%（%s〜%s ms）　範囲 0〜%s ms（10 ms ごと）"
IDS_BUS_COLUMNS = "ECU|送信フレーム数|使用率 (%)"
IDS_WAIT_TITLE = "送信待ち時間 - %s"
IDS_WAIT_COLUMNS = "CAN ID|送信 ECU|件数|最小 (µs)|平均 (µs)|最大 (µs)|95% (µs)"
IDS_WAIT_NOTE = "送信要求 → 送信開始の時間（送信 1 回を 1 件。再送は送れた 1 回）。破棄（OVERWRITE）%d 件は含みません。"
IDS_JIT_TITLE = "送信ジッター - %s"
IDS_JIT_COLUMNS = "CAN ID|送信 ECU|周期 (ms)|件数|最小 (µs)|最大 (µs)|標準偏差 (µs)"
IDS_JIT_NOTE = "連続する送信開始の間隔 − 送信要求の間隔（正は遅れ、負は早まり）。標準偏差は件数で割った値です。"
# The first sentence of IDS_LOG_NONE; the second one is about the simulator's Start button
IDS_LOG_NONE = "プロジェクト「%s」のシミュレーションログはありません。"


def ecu_name(node: int) -> str:
    return "ECU %02d" % node


def can_id_text(can_id: int) -> str:
    return "0x%03X" % can_id


def fixed1(value: float) -> str:
    return "%.1f" % value


def integer(value: int) -> str:
    return "%d" % value


def columns(rc_columns: str) -> list[str]:
    """MFC CreateList の列見出し（'|' 区切り）を列のリストにする。"""
    return rc_columns.split("|")
