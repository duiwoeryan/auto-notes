from auto_notes.config import Config
from auto_notes.downloader import Downloader
from auto_notes.keyframe import KeyframeExtractor
from auto_notes.output import build_merged_text


def test_imports():
    from auto_notes.cli import app
    from auto_notes.asr import ASREngine
    from auto_notes.ocr import OCREngine
    from auto_notes.llm import LLMProvider, OpenAIProvider, get_llm
    from auto_notes.pipeline import Pipeline
    assert app


def test_minimal_interface():
    # basic sanity: empty merge text is empty
    assert build_merged_text([], []) == ""
