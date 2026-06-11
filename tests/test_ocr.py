from pathlib import Path
from tempfile import TemporaryDirectory

from auto_notes.ocr import OCREngine


def test_save_and_load_result():
    engine = OCREngine()
    results = [
        {"timestamp": 10.0, "texts": ["hello", "world"]},
    ]
    with TemporaryDirectory() as tmp:
        p = Path(tmp) / "ocr.json"
        engine.save_result(results, p)
        assert p.exists()
        loaded = engine.load_result(p)
        assert loaded == results


def test_save_empty_result():
    engine = OCREngine()
    with TemporaryDirectory() as tmp:
        p = Path(tmp) / "empty.json"
        engine.save_result([], p)
        loaded = engine.load_result(p)
        assert loaded == []


def test_load_nonexistent():
    engine = OCREngine()
    with TemporaryDirectory() as tmp:
        p = Path(tmp) / "nonexistent.json"
        try:
            engine.load_result(p)
            assert False, "should raise"
        except FileNotFoundError:
            pass
