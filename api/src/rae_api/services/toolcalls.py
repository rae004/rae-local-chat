"""Recover tool calls that the model wrote as plain text.

qwen2.5-coder (both sizes) answers a tool-enabled prompt with a bare
`{"name": ..., "arguments": {...}}` instead of the `<tool_call>` tags its
template asks for, so Ollama never populates `message.tool_calls`. Often the
JSON follows a sentence of prose ("Certainly! Here is the command: {...}").
We stream prose, hold back tokens from the line where a call seems to start,
and extract every call from the finished text.
"""

import json
import re
from typing import Any

from rae_api.services.ollama import ToolCallRequest

_TAGGED = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
_RESPONSE_WRAP = re.compile(r"^\s*<tool_response>\s*(.*?)\s*</tool_response>\s*$", re.DOTALL)
# A line that begins a JSON object/array or a <tool_call> tag.
_HOLD_START = re.compile(r"(?:^|\n)[ \t]*(?=[{\[]|<tool_call>)")
_FENCE_BEFORE = re.compile(r"```(?:json)?[ \t]*\n?[ \t]*$")
_FENCE_AFTER = re.compile(r"^[ \t]*\n?[ \t]*```")


def hold_start(text: str, start: int = 0) -> int | None:
    """Offset (>= start) where a possible tool-call payload begins, else None."""
    m = _HOLD_START.search(text, max(start - 1, 0))
    if m is None:
        return None
    pos = m.end()
    return pos if pos >= start else None


def extract_tool_calls(text: str) -> tuple[list[ToolCallRequest], str]:
    """(calls found anywhere in `text`, the remaining prose)."""
    calls: list[ToolCallRequest] = []
    spans: list[tuple[int, int]] = []
    for m in _TAGGED.finditer(text):
        found = _calls_from_json(_leading_json(m.group(1)))
        if found:
            calls += found
            spans.append(m.span())
    if not calls:
        for i, ch in enumerate(text):
            if ch not in "{[" or any(a <= i < b for a, b in spans):
                continue
            try:
                value, length = json.JSONDecoder().raw_decode(text[i:])
            except ValueError:
                continue
            found = _calls_from_json(value)
            if found:
                calls += found
                spans.append((i, i + length))
    if not calls:
        return [], text
    prose = _remove(text, spans)
    return calls, prose


def parse_tool_calls(text: str) -> list[ToolCallRequest] | None:
    """Tool calls encoded in `text`, or None if it holds none."""
    calls, _ = extract_tool_calls(text)
    return calls or None


def unwrap_tool_response(text: str) -> str:
    """qwen2.5-coder sometimes wraps its prose in the tags meant for tool *results*."""
    m = _RESPONSE_WRAP.match(text)
    return m.group(1) if m else text


def _remove(text: str, spans: list[tuple[int, int]]) -> str:
    out = text
    for a, b in sorted(spans, reverse=True):
        before, after = out[:a], out[b:]
        fence = _FENCE_BEFORE.search(before)
        if fence:
            before = before[: fence.start()]
        fence = _FENCE_AFTER.match(after)
        if fence:
            after = after[fence.end() :]
        out = before.rstrip() + ("\n" if before.strip() and after.strip() else "") + after.lstrip()
    return out.strip()


def _leading_json(text: str) -> Any:
    try:
        value, _ = json.JSONDecoder().raw_decode(text.strip())
    except ValueError:
        return None
    return value


def _calls_from_json(value: Any) -> list[ToolCallRequest]:
    items = value if isinstance(value, list) else [value]
    calls: list[ToolCallRequest] = []
    for item in items:
        call = _as_call(item)
        if call is None:
            return []
        calls.append(call)
    return calls


def _as_call(item: Any) -> ToolCallRequest | None:
    if not isinstance(item, dict):
        return None
    name = item.get("name")
    args = item.get("arguments", item.get("parameters", {}))
    if not isinstance(name, str) or not name or not isinstance(args, dict):
        return None
    return ToolCallRequest(name=name, arguments=args)
