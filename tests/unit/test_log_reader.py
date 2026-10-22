"""read_log_records（FR-004〜FR-006、AR-030〜AR-032、contracts/core-api.md「ログの読み込み」）。"""

from pathlib import Path

import pytest

from can_log_analysis.errors import LogNotFoundError, LogReadError
from can_log_analysis.log_reader import OVERWRITE, RETRY_SUCCESS, SUCCESS, read_log_records

from conftest import DATA_DIR, DEFAULT_HEADER, log_row, write_text


def write_log(tmp_path, text, name="t.log.csv"):
    path = tmp_path / name
    write_text(path, text)
    return path


def read_text(tmp_path, text):
    return read_log_records(write_log(tmp_path, text))


def error_of(tmp_path, text):
    with pytest.raises(LogReadError) as e:
        read_text(tmp_path, text)
    return e.value.message


def test_as001_values_fr004():
    r = read_log_records(DATA_DIR / "as001" / "as001.canprj.log.csv")
    assert len(r) == 3
    assert list(r.can_id) == [0x080, 0x080, 0x100]
    assert list(r.tx_node) == [3, 3, 1]
    assert list(r.rx_node) == [1, 5, 5]
    assert list(r.tx_request) == [10000000] * 3
    assert list(r.tx_start) == [10000000, 10000000, 10000252]
    assert list(r.tx_end) == [10000246, 10000246, 10000498]
    assert list(r.rx_end) == [10000246, 10000246, 10000498]
    assert list(r.status) == [SUCCESS, SUCCESS, RETRY_SUCCESS]


def test_column_order_and_extra_columns_ar031(tmp_path):
    text = (
        "Status,Extra,Rx_End,Tx_End,Tx_Start,Tx_Request,Rx_Node,Tx_Node,CAN_ID\n"
        "OVERWRITE,zz,4,3,2,1,7,6,0x10\n"
    )
    r = read_text(tmp_path, text)
    assert (r.can_id[0], r.tx_node[0], r.rx_node[0]) == (0x10, 6, 7)
    assert (r.tx_request[0], r.tx_start[0], r.tx_end[0], r.rx_end[0]) == (1, 2, 3, 4)
    assert r.status[0] == OVERWRITE


def test_cr_removed_and_empty_lines_skipped_ar030(tmp_path):
    text = DEFAULT_HEADER + "\r\n" + log_row() + "\r\n\r\n" + log_row(can_id="0x100") + "\r\n"
    r = read_text(tmp_path, text)
    assert list(r.can_id) == [0x080, 0x100]
    assert list(r.status) == [SUCCESS, SUCCESS]


def test_empty_line_counts_as_a_line_fr006(tmp_path):
    text = DEFAULT_HEADER + "\n" + log_row() + "\n\n" + log_row(start="x") + "\n"
    assert error_of(tmp_path, text) == "line 4: bad number"


def test_last_line_without_line_break(tmp_path):
    r = read_text(tmp_path, DEFAULT_HEADER + "\n" + log_row())
    assert len(r) == 1


def test_empty_cells_defaults_fr005(tmp_path):
    text = "CAN_ID,Tx_Node,Rx_Node,Tx_Request,Tx_Start,Tx_End,Rx_End,Status\n0x1,,,,,,,SUCCESS\n"
    r = read_text(tmp_path, text)
    assert (r.tx_node[0], r.rx_node[0]) == (0, 0)
    assert (r.tx_request[0], r.tx_start[0], r.tx_end[0], r.rx_end[0]) == (-1, -1, -1, -1)


def test_trailing_comma_gives_an_empty_last_cell(tmp_path):
    text = "CAN_ID,Tx_Node,Rx_Node,Tx_Request,Tx_Start,Tx_End,Status,Rx_End\n0x1,1,2,3,4,5,SUCCESS,\n"
    assert read_text(tmp_path, text).rx_end[0] == -1


def test_signed_numbers_fr006(tmp_path):
    r = read_text(tmp_path, DEFAULT_HEADER + "\n" + log_row(req="+12", start="-5") + "\n")
    assert (r.tx_request[0], r.tx_start[0]) == (12, -5)


@pytest.mark.parametrize("value", [" 12", "12 ", "1_000", "12a", "1.5", "+", "-", "+-1", "１２"])
def test_bad_number_fr006(tmp_path, value):
    assert error_of(tmp_path, DEFAULT_HEADER + "\n" + log_row(start=value) + "\n") == "line 2: bad number"


@pytest.mark.parametrize("value,expected", [("0x7ff", 0x7FF), ("0X7FF", 0x7FF), ("0x0", 0), ("0xabcDEF", 0xABCDEF)])
def test_can_id_fr006(tmp_path, value, expected):
    assert read_text(tmp_path, DEFAULT_HEADER + "\n" + log_row(can_id=value) + "\n").can_id[0] == expected


@pytest.mark.parametrize("value", ["7ff", "0x", "0xg1", "", " 0x7ff", "0x7ff ", "0x_7ff"])
def test_bad_can_id_fr006(tmp_path, value):
    assert error_of(tmp_path, DEFAULT_HEADER + "\n" + log_row(can_id=value) + "\n") == "line 2: bad CAN_ID"


@pytest.mark.parametrize("value,expected", [("SUCCESS", SUCCESS), ("ARBITRATION_LOST_RETRY", RETRY_SUCCESS), ("OVERWRITE", OVERWRITE)])
def test_status_fr006(tmp_path, value, expected):
    assert read_text(tmp_path, DEFAULT_HEADER + "\n" + log_row(status=value) + "\n").status[0] == expected


@pytest.mark.parametrize("value", ["success", "SUCCESS ", "", "ERROR"])
def test_bad_status_fr006(tmp_path, value):
    assert error_of(tmp_path, DEFAULT_HEADER + "\n" + log_row(status=value) + "\n") == "line 2: bad Status"


def test_missing_column_reports_first_missing_name_ar031(tmp_path):
    header = "CAN_ID,Tx_Node,Rx_Node,Tx_Request,Tx_Start,Tx_End,Rx_End"
    assert error_of(tmp_path, header + "\n") == "line 1: no column Status"
    header = "CAN_ID,Rx_Node,Tx_Request,Tx_Start,Tx_End,Rx_End"
    assert error_of(tmp_path, header + "\n") == "line 1: no column Tx_Node"


def test_header_names_are_not_trimmed_ar031(tmp_path):
    header = "CAN_ID, Tx_Node,Rx_Node,Tx_Request,Tx_Start,Tx_End,Rx_End,Status"
    assert error_of(tmp_path, header + "\n") == "line 1: no column Tx_Node"


def test_only_a_line_break_has_no_columns(tmp_path):
    assert error_of(tmp_path, "\n") == "line 1: no column CAN_ID"


def test_too_few_columns_fr006(tmp_path):
    text = DEFAULT_HEADER + "\n" + log_row() + "\n" + "1,0x080,8,1,2\n"
    assert error_of(tmp_path, text) == "line 3: too few columns"


def test_empty_file_has_no_header_fr006(tmp_path):
    assert error_of(tmp_path, "") == "line 1: no header"


def test_header_only_gives_no_records(tmp_path):
    assert len(read_text(tmp_path, DEFAULT_HEADER + "\n")) == 0


def test_check_order_can_id_then_numbers_then_status_fr006(tmp_path):
    row = log_row(can_id="bad", start="x", status="bad")
    assert error_of(tmp_path, DEFAULT_HEADER + "\n" + row + "\n") == "line 2: bad CAN_ID"
    row = log_row(start="x", status="bad")
    assert error_of(tmp_path, DEFAULT_HEADER + "\n" + row + "\n") == "line 2: bad number"


def test_quotes_are_not_interpreted(tmp_path):
    assert error_of(tmp_path, DEFAULT_HEADER + "\n" + log_row(can_id='"0x080"') + "\n") == "line 2: bad CAN_ID"


def test_missing_file_is_log_not_found(tmp_path):
    with pytest.raises(LogNotFoundError):
        read_log_records(tmp_path / "none.log.csv")


def test_accepts_str_path():
    assert len(read_log_records(str(DATA_DIR / "as001" / "as001.canprj.log.csv"))) == 3


def test_sample_vehicle_row_count():
    path = DATA_DIR / "sample_vehicle_16ecu" / "sample_vehicle_16ecu.canprj.log.csv"
    assert len(read_log_records(Path(path))) == 16080
