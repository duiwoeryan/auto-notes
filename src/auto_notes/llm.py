"""LLM 抽象层：统一 OpenAI / Ollama 接口，支持自定义 base_url。"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """LLM 调用抽象基类。"""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        ...


class OpenAIProvider(LLMProvider):
    """通过 OpenAI 兼容 API 调用 LLM（可用于 OpenAI / DeepSeek 等）。"""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self._client = None
        self._base_url = base_url

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI

            kwargs = {}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = OpenAI(**kwargs)

    def generate(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        self._ensure_client()
        response = self._client.chat.completions.create(
            model=model or "deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content or ""


class OllamaProvider(LLMProvider):
    """调用本地 Ollama API（http://localhost:11434）。"""

    def generate(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        import httpx

        resp = httpx.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model or "qwen3",
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
            },
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json()["response"]


def get_llm(provider: str, base_url: Optional[str] = None) -> LLMProvider:
    """工厂方法：按名称获取 LLM 实例，自动检测可选依赖是否已安装。"""
    providers: dict[str, type[LLMProvider]] = {}
    try:
        from openai import OpenAI  # noqa: F401
        providers["openai"] = OpenAIProvider
    except ImportError:
        pass
    try:
        import httpx  # noqa: F401
        providers["ollama"] = OllamaProvider
    except ImportError:
        pass

    if provider in providers:
        if provider == "openai":
            return providers[provider](base_url=base_url)
        return providers[provider]()
    raise ValueError(f"Unknown LLM provider: {provider}. Available: {list(providers.keys())}")
