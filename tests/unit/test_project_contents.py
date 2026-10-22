"""read_project_contents（FR-004b〜FR-004e、元仕様 AR-021、research.md R-7）。"""

import pytest

from can_log_analysis.errors import ProjectReadError
from can_log_analysis.project import open_project, read_project_contents

from conftest import DATA_DIR, write_text

SAMPLE = DATA_DIR / "sample_vehicle_16ecu" / "sample_vehicle_16ecu.canprj"


def contents_of(tmp_path, text):
    path = tmp_path / "p.canprj"
    write_text(path, text)
    return read_project_contents(open_project(path))


def test_sample_network():
    c = read_project_contents(open_project(SAMPLE))
    assert (c.bit_rate_bps, c.ecu_count, c.duration_sec) == (500000, 16, 5)


def test_sample_ecus():
    c = read_project_contents(open_project(SAMPLE))
    assert [e.section_no for e in c.ecus] == list(range(1, 17))
    e = c.ecus[0]
    assert (e.node_id, e.name, e.label, e.rx_filter) == (1, "ECM Engine Control Module", "エンジン",
                                                          "0x0A8,0x0E0,0x380,0x3E8")
    assert (e.receive_delay_us, e.power_on_time_us, e.init_duration_us) == (None, None, None)


def test_sample_frames():
    c = read_project_contents(open_project(SAMPLE))
    assert len(c.frames) == 31
    f = c.frames[0]
    assert (f.node_section_no, f.frame_no, f.name, f.can_id, f.dlc, f.period_us, f.initial_offset_us) == \
        (1, 1, "EngineRPM_ThrottlePos", 0x0C0, 8, 10000, 5000)
    assert (c.frames[3].dlc, c.frames[3].period_us) == (4, 200000)


def test_sections_in_number_order(tmp_path):
    c = contents_of(tmp_path, "[Node10]\nNodeId=10\n[Node2]\nNodeId=2\n"
                              "[Node10.Frame2]\nName=b\n[Node2.Frame1]\nName=a\n[Node10.Frame1]\nName=c\n")
    assert [e.section_no for e in c.ecus] == [2, 10]
    assert [(f.node_section_no, f.frame_no) for f in c.frames] == [(2, 1), (10, 1), (10, 2)]


def test_values_that_cannot_be_read_are_none(tmp_path):
    c = contents_of(tmp_path, "[Node1]\nNodeId=x\nReceiveDelayUs=40\n"
                              "[Node1.Frame1]\nCanId=12\nPeriodUs=abc\nDlc=8\n")
    assert c.ecus[0].node_id is None
    assert c.ecus[0].receive_delay_us == 40
    assert c.ecus[0].rx_filter is None  # 全受信
    f = c.frames[0]
    assert (f.can_id, f.period_us, f.dlc, f.name) == (None, None, 8, "")


def test_missing_sections(tmp_path):
    c = contents_of(tmp_path, "; empty project\n[Other]\nA=1\n")
    assert (c.bit_rate_bps, c.ecu_count, c.duration_sec, c.ecus, c.frames) == (None, None, None, [], [])


def test_other_section_names_are_ignored(tmp_path):
    c = contents_of(tmp_path, "[NodeA]\nNodeId=1\n[Node1.FrameX]\nName=x\n[Node1.Frame1.Extra]\nName=y\n")
    assert (c.ecus, c.frames) == ([], [])


def test_unreadable_project(tmp_path):
    path = tmp_path / "p.canprj"
    write_text(path, "[Project]\nEcuCount=1\n")
    project = open_project(path)
    path.write_bytes(b"[Project]\nName=\xff\n")
    with pytest.raises(ProjectReadError):
        read_project_contents(project)
