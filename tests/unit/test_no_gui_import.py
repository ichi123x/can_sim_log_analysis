"""解析コアが画面のライブラリに依存しないこと（憲章 原則 II、FR-039、SC-005）。

GUI の禁止は憲章によるもの。numpy・matplotlib・pandas を使わないのはこの機能の決定（research.md R-4、R-11:
加算の順序を MFC と同じにするため、実行時の依存を標準ライブラリだけにする）で、別のテストに分けている。
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parents[2] / "src" / "can_log_analysis"
GUI = {"PySide6", "PySide2", "PyQt5", "PyQt6", "tkinter", "wx", "can_log_analysis_gui"}  # nor the screen package
NOT_IN_THIS_FEATURE = {"numpy", "matplotlib", "pandas"}


def imported_top_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module.split(".")[0]


SOURCES = sorted(PACKAGE.glob("*.py"))


@pytest.mark.parametrize("path", SOURCES, ids=[p.name for p in SOURCES])
def test_no_gui_library(path):
    assert not (set(imported_top_modules(path)) & GUI)


@pytest.mark.parametrize("path", SOURCES, ids=[p.name for p in SOURCES])
def test_standard_library_only_r11(path):
    assert not (set(imported_top_modules(path)) & NOT_IN_THIS_FEATURE)


def test_sources_found():
    assert len(SOURCES) >= 10
