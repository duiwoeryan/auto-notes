import re
from pathlib import Path
from tempfile import TemporaryDirectory

from auto_notes.downloader import Downloader, PROGRESS_RE


def test_progress_re_matches_percentage():
    line = "[download]  45.3% of ~259.60MiB at  5.2MiB/s ETA 00:45"
    m = PROGRESS_RE.search(line)
    assert m is not None
    assert float(m.group(1)) == 45.3


def test_progress_re_matches_100():
    line = "[download] 100% of  259.60MiB in  00:50"
    m = PROGRESS_RE.search(line)
    assert m is not None
    assert float(m.group(1)) == 100.0


def test_progress_re_no_match():
    line = "[info] BV1qG4y1B74U_p34: Downloading 1 format(s): 30080+30280"
    m = PROGRESS_RE.search(line)
    assert m is None


def test_progress_re_partial():
    line = "[download]   0.0% of   33.17MiB at  Unknown B/s ETA Unknown"
    m = PROGRESS_RE.search(line)
    assert m is not None
    assert float(m.group(1)) == 0.0


def test_find_audio_files_finds_m4a():
    d = Downloader()
    with TemporaryDirectory() as tmp:
        (Path(tmp) / "test_audio.m4a").touch()
        result = d._find_audio_files(Path(tmp), "test")
        assert len(result) == 1
        assert result[0].name == "test_audio.m4a"


def test_find_audio_files_finds_webm():
    d = Downloader()
    with TemporaryDirectory() as tmp:
        (Path(tmp) / "test_audio.webm").touch()
        result = d._find_audio_files(Path(tmp), "test")
        assert len(result) == 1
        assert result[0].name == "test_audio.webm"


def test_find_audio_files_returns_sorted():
    d = Downloader()
    with TemporaryDirectory() as tmp:
        (Path(tmp) / "z.m4a").touch()
        (Path(tmp) / "a.m4a").touch()
        result = d._find_audio_files(Path(tmp), "")
        assert result[0].name == "a.m4a"
        assert result[-1].name == "z.m4a"


def test_find_audio_files_empty_dir():
    d = Downloader()
    with TemporaryDirectory() as tmp:
        result = d._find_audio_files(Path(tmp), "test")
        assert result == []


def test_find_audio_files_filters_by_title():
    d = Downloader()
    with TemporaryDirectory() as tmp:
        (Path(tmp) / "other_audio.m4a").touch()
        (Path(tmp) / "video_title_001.m4a").touch()
        result = d._find_audio_files(Path(tmp), "video_title")
        assert len(result) == 1
        assert "video_title" in result[0].name
