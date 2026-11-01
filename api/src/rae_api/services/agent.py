"""The tool-calling loop: Ollama ⇄ MCP until the model answers in prose.

Pure: no DB, no SSE. Yields events the stream router persists and forwards.
"""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from rae_api.services.mcp import McpRegistry, ToolOutcome
from rae_api.services.ollama import OllamaClient, ToolCallRequest
from rae_api.services.toolcalls import could_be_tool_call, parse_tool_calls, unwrap_tool_response


@dataclass(frozen=True, slots=True)
class Token:
    content: str


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    server: str
    arguments: dict[str, Any]
    read_only: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "server": self.server,
            "arguments": self.arguments,
            "read_only": self.read_only,
        }


@dataclass(frozen=True, slots=True)
class AssistantTurn:
    """The model asked for tools; `content` is any prose it wrote alongside."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ToolResult:
    call: ToolCall
    content: str
    is_error: bool


@dataclass(frozen=True, slots=True)
class Finished:
    content: str


AgentEvent = Token | AssistantTurn | ToolCall | ToolResult | Finished


async def run_agent(
    ollama: OllamaClient,
    registry: McpRegistry,
    model: str,
    history: list[dict[str, Any]],
    *,
    tools_enabled: bool,
    max_rounds: int = 10,
) -> AsyncIterator[AgentEvent]:
    messages = list(history)
    tools = registry.ollama_tools() if tools_enabled else []
    for round_no in range(max_rounds):
        # Last round: no tools, so the model has to answer.
        offered = tools if round_no < max_rounds - 1 else []
        parts: list[str] = []
        structured: list[ToolCallRequest] = []
        hold: bool | None = None if offered else False  # None = undecided
        async for chunk in ollama.chat_stream(model, messages, offered or None):
            structured.extend(chunk.tool_calls)
            if chunk.content:
                parts.append(chunk.content)
                if hold is None:
                    hold = could_be_tool_call("".join(parts))
                    if hold is False:
                        yield Token("".join(parts))
                elif hold is False:
                    yield Token(chunk.content)
            if chunk.done:
                break
        text = "".join(parts)
        requests = structured
        if not requests and offered:
            parsed = parse_tool_calls(text)
            if parsed:
                requests, text = parsed, ""
        if not requests:
            if hold and text:
                text = unwrap_tool_response(text)
                yield Token(text)  # held back for nothing; release it
            yield Finished(text)
            return

        calls = [_resolve(registry, r) for r in requests]
        yield AssistantTurn(content=text, tool_calls=calls)
        messages.append(
            {
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {"function": {"name": c.name, "arguments": c.arguments}} for c in calls
                ],
            }
        )
        for call in calls:
            yield call
            outcome = await _execute(registry, call)
            yield ToolResult(call, outcome.content, outcome.is_error)
            messages.append({"role": "tool", "tool_name": call.name, "content": outcome.content})
    yield Finished("")


def _resolve(registry: McpRegistry, req: ToolCallRequest) -> ToolCall:
    spec = registry.get(req.name)
    return ToolCall(
        id=uuid.uuid4().hex[:12],
        name=req.name,
        server=spec.server if spec else "",
        arguments=req.arguments,
        read_only=bool(spec and spec.read_only),
    )


async def _execute(registry: McpRegistry, call: ToolCall) -> ToolOutcome:
    if registry.get(call.name) is None:
        return ToolOutcome(f"Unknown tool: {call.name}", is_error=True)
    if not call.read_only:
        # Milestone E2 adds the approve/deny flow; until then writes are refused.
        return ToolOutcome(
            f"{call.name} modifies state and needs user approval, which isn't available yet.",
            is_error=True,
        )
    return await registry.call(call.name, call.arguments)
