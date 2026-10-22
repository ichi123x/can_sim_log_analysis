"""プロジェクトファイル .canprj（FR-001、FR-002、research.md R-9）。"""

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

from can_log_analysis.errors import ProjectNotFoundError, ProjectReadError


@dataclass(frozen=True)
class Project:
    path: Path
    name: str       # MFC ProjectFileName(): the text after the last '\' or '/'
    log_path: Path  # MFC LogPathFor(): the project path + ".log.csv"


def open_project(path: str | os.PathLike) -> Project:
    """.canprj を UTF-8 の INI として読む。値は検査しない（解析には使わない）。"""
    path = Path(path)
    if not path.is_file():
        raise ProjectNotFoundError(path)
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        with open(path, encoding="utf-8") as f:
            parser.read_file(f)
    except (configparser.Error, UnicodeDecodeError, OSError) as e:
        raise ProjectReadError(path, str(e).splitlines()[0]) from e
    text = str(path)
    name = text[max(text.rfind("\\"), text.rfind("/")) + 1:]
    return Project(path=path, name=name, log_path=Path(text + ".log.csv"))
