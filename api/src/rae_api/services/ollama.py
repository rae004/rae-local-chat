"""Thin async client for Ollama's streaming /api/chat endpoint."""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx


class OllamaError(Exception):
    """Ollama returned an error (HTTP or in-stream)."""


@dataclass(frozen=True, slots=True)
class ChatChunk:
    content: str
    done: bool
    model: str


class OllamaClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def chat_stream(
        self, model: str, messages: list[dict[str, str]]
    ) -> AsyncIterator[ChatChunk]:
        """Yield one chunk per NDJSON line until Ollama reports `done`."""
        payload = {"model": model, "messages": messages, "stream": True}
        async with self._http.stream("POST", "/api/chat", json=payload) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                raise OllamaError(_error_text(body, resp.status_code))
            async for line in resp.aiter_lines():
                if not line:
                    continue
                data: dict[str, Any] = json.loads(line)
                if "error" in data:
                    raise OllamaError(str(data["error"]))
                yield ChatChunk(
                    content=data.get("message", {}).get("content", ""),
                    done=bool(data.get("done")),
                    model=str(data.get("model", model)),
                )
                if data.get("done"):
                    return


def _error_text(body: bytes, status: int) -> str:
    try:
        return str(json.loads(body).get("error", body.decode()))
    except ValueError, AttributeError:
        return f"Ollama HTTP {status}: {body.decode(errors='replace')}"
