"""open_project（FR-001、FR-002、FR-003、AR-020、AR-021）。"""

from pathlib import Path

import pytest

from can_log_analysis.errors import ProjectNotFoundError, ProjectReadError
from can_log_analysis.project import open_project

from conftest import DATA_DIR, write_text


def test_name_and_log_path_fr001():
    path = DATA_DIR / "as001" / "as001.canprj"
    project = open_project(path)
    assert project.path == path
    assert project.name == "as001.canprj"
    assert project.log_path == Path(str(path) + ".log.csv")


def test_name_takes_text_after_last_slash_or_backslash_fr002(tmp_path):
    path = tmp_path / "my.project.canprj"
    write_text(path, "[Project]\nEcuCount=1\n")
    assert open_project(str(path)).name == "my.project.canprj"
    assert open_project(str(path).replace("\\", "/")).name == "my.project.canprj"


def test_missing_project_fr003(tmp_path):
    with pytest.raises(ProjectNotFoundError):
        open_project(tmp_path / "none.canprj")


def test_not_ini_fr002(tmp_path):
    path = tmp_path / "bad.canprj"
    write_text(path, "a=1\n")  # no section header
    with pytest.raises(ProjectReadError):
        open_project(path)


def test_not_utf8_fr002(tmp_path):
    path = tmp_path / "bad.canprj"
    path.write_bytes(b"[Project]\nName=\xff\xfe\n")
    with pytest.raises(ProjectReadError):
        open_project(path)


def test_project_without_log_opens_fr003(tmp_path):
    path = tmp_path / "nolog.canprj"
    write_text(path, "[Project]\nEcuCount=1\n")
    project = open_project(path)
    assert not project.log_path.exists()
