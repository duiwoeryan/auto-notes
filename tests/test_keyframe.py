from pathlib import Path

from auto_notes.keyframe import KeyframeExtractor


def test_extract_no_video():
    extractor = KeyframeExtractor()
    frames = extractor.extract(Path("/nonexistent.mp4"), Path("/tmp/out"))
    assert frames == []


def test_extract_output_dir_created(tmp_path):
    extractor = KeyframeExtractor()
    out = tmp_path / "sub" / "frames"
    frames = extractor.extract(Path("/nonexistent.mp4"), out)
    assert frames == []
    assert out.exists()
