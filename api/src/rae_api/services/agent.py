"""The tool-calling loop: Ollama ⇄ MCP until the model answers in prose.

Pure: no DB, no SSE. Yields events the stream router persists and forwards.
Read-only tools run at once; anything else parks on `Approvals` until the user
decides (or the timeout counts as a denial).
"""

import uuid
from collections.abc import AsyncIterator, Collection
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from rae_api.services.approvals import Approvals
from rae_api.services.mcp import McpRegistry, ToolOutcome
from rae_api.services.ollama import OllamaClient, ToolCallRequest
from rae_api.services.toolcalls import extract_tool_calls, hold_start, unwrap_tool_response

ToolCallStatus = Literal["auto", "pending"]
DecidedBy = Literal["user", "timeout"]


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
    status: ToolCallStatus = "auto"

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "server": self.server,
            "arguments": self.arguments,
            "read_only": self.read_only,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class AssistantTurn:
    """The model asked for tools; `content` is any prose it wrote alongside."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ToolDecision:
    call: ToolCall
    approved: bool
    by: DecidedBy


@dataclass(frozen=True, slots=True)
class ToolResult:
    call: ToolCall
    content: str
    is_error: bool
    # None = ran without asking (read-only); True/False = the user's decision
    approved: bool | None = None


@dataclass(frozen=True, slots=True)
class Finished:
    content: str


AgentEvent = Token | AssistantTurn | ToolCall | ToolDecision | ToolResult | Finished


async def run_agent(
    ollama: OllamaClient,
    registry: McpRegistry,
    model: str,
    history: list[dict[str, Any]],
    *,
    tools_enabled: bool,
    servers: Collection[str] | None = None,
    approvals: Approvals | None = None,
    approval_timeout: float = 300.0,
    max_rounds: int = 10,
    system_prompt: str | None = None,
) -> AsyncIterator[AgentEvent]:
    # Without an approvals registry there's no way to ask, so only offer read-only tools.
    tools = (
        registry.ollama_tools(include_write=approvals is not None, servers=servers)
        if tools_enabled
        else []
    )
    messages = _with_system(history, system_prompt, tools_offered=bool(tools))
    for round_no in range(max_rounds):
        # Last round: no tools, so the model has to answer.
        offered = tools if round_no < max_rounds - 1 else []
        text = ""
        emitted = 0  # text[:emitted] has been streamed as tokens
        holding = False  # a line that looks like a tool call started; keep the rest back
        structured: list[ToolCallRequest] = []
        async for chunk in ollama.chat_stream(model, messages, offered or None):
            structured.extend(chunk.tool_calls)
            if chunk.content:
                text += chunk.content
                if not offered:
                    yield Token(chunk.content)
                    emitted = len(text)
                elif not holding:
                    start = hold_start(text, emitted)
                    if start is None:
                        yield Token(text[emitted:])
                        emitted = len(text)
                    else:
                        if start > emitted:
                            yield Token(text[emitted:start])
                        emitted = start
                        holding = True
            if chunk.done:
                break
        requests = structured
        if not requests and offered:
            requests, text = extract_tool_calls(text)
        if not requests:
            if emitted < len(text):
                text = text[:emitted] + unwrap_tool_response(text[emitted:])
                yield Token(text[emitted:])  # held back for nothing; release it
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
            if call.read_only or registry.get(call.name) is None or approvals is None:
                yield call
                outcome = await _execute(registry, call)
                yield ToolResult(call, outcome.content, outcome.is_error)
            else:
                approvals.register(call.id)
                call = replace(call, status="pending")
                yield call
                decision = await approvals.wait(call.id, approval_timeout)
                approved = decision is True
                yield ToolDecision(call, approved, "user" if decision is not None else "timeout")
                if approved:
                    outcome = await registry.call(call.name, call.arguments)
                else:
                    why = "the user denied it" if decision is False else "approval timed out"
                    outcome = ToolOutcome(f"{call.name} was not run: {why}.", is_error=True)
                yield ToolResult(call, outcome.content, outcome.is_error, approved=approved)
            messages.append({"role": "tool", "tool_name": call.name, "content": outcome.content})
    yield Finished("")


TOOL_GUIDANCE = (
    "Tools: use one only when the request actually needs it, and make the fewest calls "
    "that answer the question. Never store anything with memory tools unless the user asks "
    "you to remember something. To call a tool, reply with only the tool call and no other "
    "text; after the result arrives, answer in plain prose."
)


def _with_system(
    history: list[dict[str, Any]], system_prompt: str | None, *, tools_offered: bool
) -> list[dict[str, Any]]:
    parts = [p for p in (system_prompt, TOOL_GUIDANCE if tools_offered else None) if p]
    if not parts or (history and history[0].get("role") == "system"):
        return list(history)
    return [{"role": "system", "content": "\n\n".join(parts)}, *history]


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
        # Only reachable with no Approvals registry (tests): writes can't be asked about.
        return ToolOutcome(
            f"{call.name} modifies state and needs user approval, which isn't available here.",
            is_error=True,
        )
    return await registry.call(call.name, call.arguments)
