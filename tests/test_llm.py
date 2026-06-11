from typing import Optional

from auto_notes.llm import OpenAIProvider, get_llm


def test_get_openai_provider():
    provider = get_llm("openai")
    assert isinstance(provider, OpenAIProvider)


def test_openai_provider_with_base_url():
    provider = get_llm("openai", base_url="https://custom.api.com/v1")
    assert isinstance(provider, OpenAIProvider)
    assert provider._base_url == "https://custom.api.com/v1"


def test_get_unknown_provider():
    try:
        get_llm("nonexistent")
        assert False, "should raise"
    except ValueError as e:
        assert "Unknown LLM provider" in str(e)


def test_openai_provider_constructor():
    provider = OpenAIProvider()
    assert provider._client is None


def test_openai_provider_with_base_url_constructor():
    provider = OpenAIProvider(base_url="https://custom.api.com/v1")
    assert provider._base_url == "https://custom.api.com/v1"
