from auto_notes.output import build_merged_text, _format_ts


def test_format_ts_seconds():
    result = _format_ts(65)
    assert result == "0:01:05"


def test_format_ts_zero():
    result = _format_ts(0)
    assert result == "0:00:00"


def test_format_ts_large():
    result = _format_ts(3661)
    assert result == "1:01:01"


def test_build_merged_text_no_ocr():
    segments = [
        {"start": 0.0, "end": 5.0, "text": "hello"},
        {"start": 6.0, "end": 10.0, "text": "world"},
    ]
    result = build_merged_text(segments, [])
    assert "hello" in result
    assert "world" in result
    assert "slide" not in result


def test_build_merged_text_with_ocr():
    segments = [
        {"start": 0.0, "end": 5.0, "text": "hello world"},
    ]
    ocr = [
        {"timestamp": 3.0, "texts": ["slide text"]},
    ]
    result = build_merged_text(segments, ocr)
    assert "hello world" in result
    assert "slide text" in result


def test_build_merged_text_ocr_out_of_range():
    segments = [
        {"start": 0.0, "end": 5.0, "text": "hello"},
    ]
    ocr = [
        {"timestamp": 10.0, "texts": ["later slide"]},
    ]
    result = build_merged_text(segments, ocr)
    assert "未匹配的时间戳" in result
    assert "later slide" in result


def test_build_merged_text_empty():
    result = build_merged_text([], [])
    assert result == ""
