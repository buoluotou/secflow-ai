"""LLM configuration — read from environment (same keys as .env.example)."""
from __future__ import annotations

import os

PROVIDERS = ("mock", "openai", "ollama")


class LLMConfig:
    def __init__(
        self,
        provider: str = "mock",
        base_url: str = "",
        api_key: str = "",
        model: str = "",
        timeout: int = 120,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ):
        self.provider = provider if provider in PROVIDERS else "mock"
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model or self._default_model()
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            provider=os.getenv("LLM_PROVIDER", "mock"),
            base_url=os.getenv("LLM_BASE_URL", ""),
            api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", ""),
            timeout=int(os.getenv("LLM_TIMEOUT", "120")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
        )

    def _default_model(self) -> str:
        if self.provider == "ollama":
            return "qwen2.5:7b"
        return "gpt-4o-mini"

    @property
    def headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h
