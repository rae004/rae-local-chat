"""Thin async client for Ollama's streaming /api/chat endpoint."""

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx


class OllamaError(Exception):
    """Ollama returned an error (HTTP or in-stream)."""


@dataclass(frozen=True, slots=True)
class ToolCallRequest:
    """A tool invocation the model asked for (Ollama assigns no id; we do)."""

    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ChatChunk:
    content: str
    done: bool
    model: str
    tool_calls: tuple[ToolCallRequest, ...] = ()


@dataclass(frozen=True, slots=True)
class ModelInfo:
    name: str
    size: int
    parameter_size: str | None
    family: str | None
    tools: bool = field(default=False)


class OllamaClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def list_models(self) -> list[ModelInfo]:
        """Models available on the server (`/api/tags`), name-sorted, with tool capability."""
        try:
            resp = await self._http.get("/api/tags")
        except httpx.HTTPError as e:
            raise OllamaError(f"Ollama unreachable: {e}") from e
        if resp.status_code >= 400:
            raise OllamaError(_error_text(resp.content, resp.status_code))
        raw = resp.json().get("models", [])
        caps = await asyncio.gather(*(self._capabilities(str(m["name"])) for m in raw))
        models = [
            ModelInfo(
                name=str(m["name"]),
                size=int(m.get("size", 0)),
                parameter_size=(m.get("details") or {}).get("parameter_size"),
                family=(m.get("details") or {}).get("family"),
                tools="tools" in c,
            )
            for m, c in zip(raw, caps, strict=True)
        ]
        return sorted(models, key=lambda m: m.name)

    async def _capabilities(self, name: str) -> list[str]:
        """`/api/show` capabilities (e.g. ["completion", "tools"]); [] if unavailable."""
        try:
            resp = await self._http.post("/api/show", json={"model": name})
        except httpx.HTTPError:
            return []
        if resp.status_code >= 400:
            return []
        return [str(c) for c in resp.json().get("capabilities", [])]

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ChatChunk]:
        """Yield one chunk per NDJSON line until Ollama reports `done`."""
        payload: dict[str, Any] = {"model": model, "messages": messages, "stream": True}
        if tools:
            payload["tools"] = tools
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
                message = data.get("message", {})
                yield ChatChunk(
                    content=message.get("content", ""),
                    done=bool(data.get("done")),
                    model=str(data.get("model", model)),
                    tool_calls=tuple(_parse_tool_calls(message.get("tool_calls") or [])),
                )
                if data.get("done"):
                    return


def _parse_tool_calls(raw: list[dict[str, Any]]) -> list[ToolCallRequest]:
    calls: list[ToolCallRequest] = []
    for item in raw:
        fn = item.get("function") or {}
        args = fn.get("arguments") or {}
        if isinstance(args, str):  # some models stringify; be lenient
            try:
                args = json.loads(args)
            except ValueError:
                args = {"_raw": args}
        calls.append(ToolCallRequest(name=str(fn.get("name", "")), arguments=dict(args)))
    return calls


def _error_text(body: bytes, status: int) -> str:
    try:
        return str(json.loads(body).get("error", body.decode()))
    except ValueError, AttributeError:
        return f"Ollama HTTP {status}: {body.decode(errors='replace')}"
