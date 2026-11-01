"""Registry of MCP servers → one flat tool catalogue for Ollama.

Each server is reached over Streamable HTTP. Tools are exposed to the model
under `<server>__<tool>` so names can't collide across servers. A fresh client
is opened per call: the handshake is cheap on the LAN and it self-heals when a
server restarts.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent
from pydantic import BaseModel

log = logging.getLogger(__name__)

SEP = "__"


class McpServerConfig(BaseModel):
    name: str
    url: str
    headers: dict[str, str] = {}


@dataclass(frozen=True, slots=True)
class ToolSpec:
    server: str
    name: str
    description: str
    input_schema: dict[str, Any]
    read_only: bool

    @property
    def qualified(self) -> str:
        return f"{self.server}{SEP}{self.name}"

    def as_ollama(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.qualified,
                "description": self.description,
                "parameters": self.input_schema or {"type": "object", "properties": {}},
            },
        }


@dataclass(frozen=True, slots=True)
class ToolOutcome:
    content: str
    is_error: bool


class McpRegistry:
    def __init__(self, servers: list[McpServerConfig], *, result_max_chars: int = 16_000) -> None:
        self._servers = {s.name: s for s in servers}
        self._result_max_chars = result_max_chars
        self.tools: dict[str, ToolSpec] = {}
        # server name -> "ok" or "error: ..."
        self.status: dict[str, str] = {name: "not connected" for name in self._servers}

    @property
    def servers(self) -> list[McpServerConfig]:
        return list(self._servers.values())

    async def refresh(self) -> None:
        """Re-list tools from every server; a failing server is reported, not fatal."""
        results = await asyncio.gather(
            *(self._list(s) for s in self._servers.values()), return_exceptions=True
        )
        tools: dict[str, ToolSpec] = {}
        for server, result in zip(self._servers.values(), results, strict=True):
            if isinstance(result, BaseException):
                self.status[server.name] = f"error: {result}"
                log.warning("MCP server %s unavailable: %s", server.name, result)
                continue
            self.status[server.name] = "ok"
            for spec in result:
                tools[spec.qualified] = spec
        self.tools = tools

    def ollama_tools(self, *, include_write: bool = False) -> list[dict[str, Any]]:
        return [t.as_ollama() for t in self.tools.values() if include_write or t.read_only]

    def get(self, qualified: str) -> ToolSpec | None:
        return self.tools.get(qualified)

    async def call(self, qualified: str, arguments: dict[str, Any]) -> ToolOutcome:
        spec = self.tools.get(qualified)
        if spec is None:
            return ToolOutcome(f"Unknown tool: {qualified}", is_error=True)
        try:
            async with self._client(self._servers[spec.server]) as client:
                result = await client.call_tool(spec.name, arguments)
        except Exception as e:  # noqa: BLE001 — any transport/protocol failure is a tool error
            return ToolOutcome(f"{spec.server} failed: {type(e).__name__}: {e}", is_error=True)
        text = "\n".join(
            c.text if isinstance(c, TextContent) else f"[{c.type} content omitted]"
            for c in result.content
        )
        if not text and result.structured_content is not None:
            text = json.dumps(result.structured_content)
        return ToolOutcome(self._truncate(text), is_error=bool(result.is_error))

    def _truncate(self, text: str) -> str:
        if len(text) <= self._result_max_chars:
            return text
        return text[: self._result_max_chars] + f"\n…[truncated {len(text)} chars total]"

    async def _list(self, server: McpServerConfig) -> list[ToolSpec]:
        specs: list[ToolSpec] = []
        async with self._client(server) as client:
            cursor: str | None = None
            while True:
                page = await client.list_tools(cursor=cursor)
                for t in page.tools:
                    ann = t.annotations
                    specs.append(
                        ToolSpec(
                            server=server.name,
                            name=t.name,
                            description=t.description or t.title or t.name,
                            input_schema=dict(t.input_schema or {}),
                            # No annotation => assume it writes. Safe default.
                            read_only=bool(ann and ann.read_only_hint),
                        )
                    )
                cursor = page.next_cursor
                if not cursor:
                    return specs

    @staticmethod
    @asynccontextmanager
    async def _client(server: McpServerConfig) -> AsyncIterator[Client]:
        timeout = httpx2.Timeout(30.0, read=180.0)
        async with httpx2.AsyncClient(headers=server.headers, timeout=timeout) as http:
            transport = streamable_http_client(server.url, http_client=http)
            async with Client(transport) as client:
                yield client
