from pathlib import Path
from tempfile import TemporaryDirectory

from auto_notes.config import Config


def test_default_values():
    with TemporaryDirectory() as tmp:
        cfg = Config()
        assert cfg.output_dir == Path("notes")
        assert cfg.working_dir == Path("workspace")
        assert cfg.lang == "zh"
        assert cfg.llm_provider == "openai"
        assert cfg.keep_intermediates is True
        assert cfg.audio_only is True
        assert cfg.max_keyframes == 120


def test_properties():
    cfg = Config()
    assert str(cfg.audio_path).endswith("audio.wav")
    assert str(cfg.frames_dir).endswith("frames")
    assert str(cfg.transcript_path).endswith("transcript.json")
    assert str(cfg.ocr_path).endswith("ocr.json")


def test_ensure_dirs():
    cfg = Config()
    with TemporaryDirectory() as tmp:
        cfg.working_dir = Path(tmp) / "work"
        cfg.output_dir = Path(tmp) / "out"
        cfg.ensure_dirs()
        assert cfg.working_dir.exists()
        assert cfg.output_dir.exists()


def test_ensure_dirs_creates_frames():
    cfg = Config()
    with TemporaryDirectory() as tmp:
        cfg.working_dir = Path(tmp) / "work"
        cfg.output_dir = Path(tmp) / "out"
        cfg.ensure_dirs()
        assert cfg.frames_dir.exists()


def test_toml_config_override(tmp_path):
    toml_content = """
    output_dir = "custom_notes"
    lang = "en"
    max_keyframes = 200
    """
    p = tmp_path / "config.toml"
    p.write_text(toml_content)
    cfg = Config(p)
    assert cfg.output_dir == Path("custom_notes")
    assert cfg.lang == "en"
    assert cfg.max_keyframes == 200


def test_toml_config_respects_missing(tmp_path):
    p = tmp_path / "nonexistent.toml"
    cfg = Config(p)
    assert cfg.output_dir == Path("notes")


def test_audio_path_depends_on_working_dir():
    cfg = Config()
    cfg.working_dir = Path("/custom/work")
    assert str(cfg.audio_path) == "/custom/work/audio.wav"
