from auto_notes.pipeline import Pipeline
from auto_notes.config import Config


def test_pipeline_construction():
    cfg = Config()
    pipeline = Pipeline(cfg)
    assert pipeline.cfg is cfg


def test_pipeline_config_mutation():
    cfg = Config()
    cfg.audio_only = True
    pipeline = Pipeline(cfg)
    assert pipeline.cfg.audio_only is True


def test_pipeline_with_different_config():
    cfg1 = Config()
    cfg2 = Config()
    p1 = Pipeline(cfg1)
    p2 = Pipeline(cfg2)
    assert p1 is not p2
    assert p1.cfg is not p2.cfg
