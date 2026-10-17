"""Kielimalliasiakas. OpenAI-yhteensopiva rajapinta toimii Ollaman (/v1), vLLM:n ja
hostattujen Qwen-palveluiden kanssa, joten mallin ajopaikkaa voi vaihtaa asetuksella."""

from __future__ import annotations

from typing import Any, Protocol

import httpx


class ChatClient(Protocol):
    model: str

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Palauttaa assistentin viestin: {"content": ..., "tool_calls": [...]}"""


class OpenAICompatibleClient:
    def __init__(self, base_url: str, model: str, api_key: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "temperature": 0.2,
                "stream": False,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]
