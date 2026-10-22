"""プロジェクトファイル .canprj（FR-001、FR-002、research.md R-9。機能 002 の表示用の読み取り: research.md R-7）。"""

import configparser
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from can_log_analysis.errors import ProjectNotFoundError, ProjectReadError


@dataclass(frozen=True)
class Project:
    path: Path
    name: str       # MFC ProjectFileName(): the text after the last '\' or '/'
    log_path: Path  # MFC LogPathFor(): the project path + ".log.csv"


def _read_ini(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        with open(path, encoding="utf-8") as f:
            parser.read_file(f)
    except (configparser.Error, UnicodeDecodeError, OSError) as e:
        raise ProjectReadError(path, str(e).splitlines()[0]) from e
    return parser


def open_project(path: str | os.PathLike) -> Project:
    """.canprj を UTF-8 の INI として読む。値は検査しない（解析には使わない）。"""
    path = Path(path)
    if not path.is_file():
        raise ProjectNotFoundError(path)
    _read_ini(path)
    text = str(path)
    name = text[max(text.rfind("\\"), text.rfind("/")) + 1:]
    return Project(path=path, name=name, log_path=Path(text + ".log.csv"))


# ---- 機能 002: メインウィンドウに表示する .canprj の内容（解析の計算には使わない。元仕様 AR-003） ----

@dataclass(frozen=True)
class EcuInfo:
    section_no: int  # N of [NodeN]
    node_id: int | None = None
    name: str = ""
    label: str = ""
    rx_filter: str | None = None  # None: every frame is received
    receive_delay_us: int | None = None
    power_on_time_us: int | None = None
    init_duration_us: int | None = None


@dataclass(frozen=True)
class FrameInfo:
    node_section_no: int  # N of [NodeN.FrameM]
    frame_no: int         # M
    name: str = ""
    can_id: int | None = None
    dlc: int | None = None
    period_us: int | None = None
    initial_offset_us: int | None = None


@dataclass(frozen=True)
class ProjectContents:
    bit_rate_bps: int | None = None
    ecu_count: int | None = None
    duration_sec: int | None = None
    ecus: list[EcuInfo] = field(default_factory=list)
    frames: list[FrameInfo] = field(default_factory=list)


_NODE = re.compile(r"Node(\d+)")
_FRAME = re.compile(r"Node(\d+)\.Frame(\d+)")
_CAN_ID = re.compile(r"0[xX][0-9A-Fa-f]+")


def _int(section, key) -> int | None:
    if section is None:
        return None
    text = section.get(key)
    if text is None:
        return None
    try:
        return int(text.strip(), 10)
    except ValueError:
        return None


def _can_id(section, key) -> int | None:
    text = section.get(key)
    if text is None or not _CAN_ID.fullmatch(text.strip()):
        return None
    return int(text.strip()[2:], 16)


def read_project_contents(project: Project) -> ProjectContents:
    """.canprj の [Project]・[Network]・[NodeN]・[NodeN.FrameM] を読む。項目がない・数値でない値は None。"""
    ini = _read_ini(project.path)
    ecus = []
    frames = []
    for name in ini.sections():
        s = ini[name]
        m = _NODE.fullmatch(name)
        if m:
            ecus.append(EcuInfo(
                section_no=int(m.group(1)), node_id=_int(s, "NodeId"), name=s.get("Name", ""),
                label=s.get("Label", ""), rx_filter=s.get("RxFilter"),
                receive_delay_us=_int(s, "ReceiveDelayUs"), power_on_time_us=_int(s, "PowerOnTimeUs"),
                init_duration_us=_int(s, "InitDurationUs")))
            continue
        m = _FRAME.fullmatch(name)
        if m:
            frames.append(FrameInfo(
                node_section_no=int(m.group(1)), frame_no=int(m.group(2)), name=s.get("Name", ""),
                can_id=_can_id(s, "CanId"), dlc=_int(s, "Dlc"), period_us=_int(s, "PeriodUs"),
                initial_offset_us=_int(s, "InitialOffsetUs")))
    ecus.sort(key=lambda e: e.section_no)
    frames.sort(key=lambda f: (f.node_section_no, f.frame_no))
    project_section = ini["Project"] if ini.has_section("Project") else None
    network = ini["Network"] if ini.has_section("Network") else None
    return ProjectContents(bit_rate_bps=_int(network, "BitRateBps"), ecu_count=_int(project_section, "EcuCount"),
                           duration_sec=_int(project_section, "DurationSec"), ecus=ecus, frames=frames)
