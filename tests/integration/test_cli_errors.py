"""読めない入力（US4、FR-003、FR-006、SC-004、contracts/cli.md「出力と終了コード」）。"""

import pytest

from can_log_analysis.cli import main

from conftest import DATA_DIR

ERRORS = DATA_DIR / "errors"


def run(capsys, argv):
    code = main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.mark.parametrize("name,message", [
    ("no_status_column", "line 1: no column Status"),
    ("bad_number", "line 5: bad number"),
    ("bad_can_id", "line 2: bad CAN_ID"),
    ("bad_status", "line 3: bad Status"),
    ("too_few_columns", "line 3: too few columns"),
    ("empty_log", "line 1: no header"),
])
def test_log_errors_fr006(capsys, tmp_path, name, message):
    project = ERRORS / f"{name}.canprj"
    out_dir = tmp_path / "out"
    code, out, err = run(capsys, [str(project), "-o", str(out_dir)])
    assert code == 1
    assert out == ""
    assert err == f"{project}.log.csv: {message}\n"
    assert not out_dir.exists()  # nothing is written when the log cannot be read


def test_log_error_without_output_dir_prints_no_table(capsys):
    code, out, err = run(capsys, [str(ERRORS / "bad_number.canprj")])
    assert (code, out) == (1, "")
    assert err.endswith("bad_number.canprj.log.csv: line 5: bad number\n")


def test_no_log_fr003(capsys):
    code, out, err = run(capsys, [str(ERRORS / "no_log.canprj")])
    assert (code, out) == (1, "")
    assert err == "プロジェクト「no_log.canprj」のシミュレーションログはありません。\n"


def test_no_project_fr003(capsys, tmp_path):
    project = str(tmp_path / "no_such.canprj")
    code, out, err = run(capsys, [project])
    assert (code, out) == (1, "")
    assert err == f"プロジェクトファイルがありません: {project}\n"


def test_bad_project(capsys):
    project = str(ERRORS / "bad_project.canprj")
    code, out, err = run(capsys, [project])
    assert (code, out) == (1, "")
    assert err.startswith(f"プロジェクトファイルを読めません: {project}: ")
    assert err.count("\n") == 1


def test_unknown_analysis_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as e:
        main([str(DATA_DIR / "as001" / "as001.canprj"), "-a", "foo"])
    assert e.value.code == 2
    assert capsys.readouterr().out == ""


def test_cannot_write_output(capsys, tmp_path):
    not_a_dir = tmp_path / "file.txt"
    not_a_dir.write_text("x", encoding="utf-8")
    code, out, err = run(capsys, [str(DATA_DIR / "as001" / "as001.canprj"), "-o", str(not_a_dir)])
    assert (code, out) == (1, "")
    assert err.startswith(f"出力できません: {not_a_dir}: ")
    assert err.count("\n") == 1
