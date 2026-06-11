import json
from pathlib import Path
from tempfile import TemporaryDirectory

from auto_notes.asr import ASREngine


def test_save_and_load_transcript():
    engine = ASREngine()
    segments = [
        {"start": 0.0, "end": 2.5, "text": "hello"},
        {"start": 3.0, "end": 5.0, "text": "world"},
    ]
    with TemporaryDirectory() as tmp:
        p = Path(tmp) / "transcript.json"
        engine.save_transcript(segments, p)
        assert p.exists()
        loaded = engine.load_transcript(p)
        assert loaded == segments


def test_save_empty_transcript():
    engine = ASREngine()
    with TemporaryDirectory() as tmp:
        p = Path(tmp) / "empty.json"
        engine.save_transcript([], p)
        loaded = engine.load_transcript(p)
        assert loaded == []


def test_save_with_unicode():
    engine = ASREngine()
    segments = [{"start": 0.0, "end": 1.0, "text": "中文测试"}]
    with TemporaryDirectory() as tmp:
        p = Path(tmp) / "unicode.json"
        engine.save_transcript(segments, p)
        loaded = engine.load_transcript(p)
        assert loaded[0]["text"] == "中文测试"


def test_transcript_json_format():
    engine = ASREngine()
    segments = [{"start": 1.5, "end": 3.7, "text": "test"}]
    with TemporaryDirectory() as tmp:
        p = Path(tmp) / "t.json"
        engine.save_transcript(segments, p)
        data = json.loads(p.read_text())
        assert data[0]["start"] == 1.5
        assert data[0]["end"] == 3.7
