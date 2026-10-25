"""Test doubles for the Ollama client and the MCP registry."""

import json
from collections.abc import AsyncIterator
from typing import Any

from rae_api.services.mcp import McpRegistry, McpServerConfig, ToolOutcome, ToolSpec
from rae_api.services.ollama import ChatChunk, ModelInfo, OllamaError, ToolCallRequest

Turn = list[str | ToolCallRequest]


class FakeOllama:
    """Scripted turns: each is a list of text tokens and/or structured tool calls."""

    def __init__(self, *turns: Turn, fail_after: int | None = None) -> None:
        self.turns = list(turns) or [[]]
        self.fail_after = fail_after
        self.calls: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]] | None]] = []

    @staticmethod
    def call(name: str, arguments: dict[str, Any]) -> ToolCallRequest:
        return ToolCallRequest(name=name, arguments=arguments)

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ChatChunk]:
        self.calls.append((model, messages, tools))
        turn = self.turns[min(len(self.calls) - 1, len(self.turns) - 1)]
        for i, item in enumerate(turn):
            if self.fail_after is not None and i == self.fail_after:
                raise OllamaError("model exploded")
            if isinstance(item, ToolCallRequest):
                yield ChatChunk(content="", done=False, model=model, tool_calls=(item,))
            else:
                yield ChatChunk(content=item, done=False, model=model)
        yield ChatChunk(content="", done=True, model=model)

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                name="qwen2.5-coder:latest",
                size=4,
                parameter_size="7.6B",
                family="qwen2",
                tools=True,
            ),
            ModelInfo(name="starcoder2:7b", size=4, parameter_size="7B", family="starcoder2"),
        ]


class FakeRegistry(McpRegistry):
    """One server `fs` with a read-only `read` and a writing `write`; records calls."""

    def __init__(self) -> None:
        super().__init__([McpServerConfig(name="fs", url="http://fs/mcp")])
        schema = {"type": "object", "properties": {"path": {"type": "string"}}}
        self.tools = {
            "fs__read": ToolSpec("fs", "read", "Read a file", schema, read_only=True),
            "fs__write": ToolSpec("fs", "write", "Write a file", schema, read_only=False),
        }
        self.status = {"fs": "ok"}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.files = {"notes.txt": "buy milk\n"}

    async def refresh(self) -> None:
        return None

    async def call(self, qualified: str, arguments: dict[str, Any]) -> ToolOutcome:
        self.calls.append((qualified, arguments))
        if qualified == "fs__read":
            path = str(arguments.get("path"))
            if path in self.files:
                return ToolOutcome(self.files[path], is_error=False)
            return ToolOutcome(f"No such file: {path}", is_error=True)
        return ToolOutcome(json.dumps(arguments), is_error=False)
