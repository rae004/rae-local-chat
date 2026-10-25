"""Recover tool calls that the model wrote as plain text.

qwen2.5-coder (both sizes) answers a tool-enabled prompt with a bare
`{"name": ..., "arguments": {...}}` instead of the `<tool_call>` tags its
template asks for, so Ollama never populates `message.tool_calls`. We hold back
tokens that look like the start of such a payload and parse the finished text.
"""

import json
import re
from typing import Any

from rae_api.services.ollama import ToolCallRequest

_TAGGED = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
_RESPONSE_WRAP = re.compile(r"^\s*<tool_response>\s*(.*?)\s*</tool_response>\s*$", re.DOTALL)
_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
_PREFIXES = ("{", "<", "`")


def could_be_tool_call(text: str) -> bool | None:
    """None = too early to tell (only whitespace so far); else whether to hold tokens."""
    stripped = text.lstrip()
    if not stripped:
        return None
    return stripped.startswith(_PREFIXES)


def parse_tool_calls(text: str) -> list[ToolCallRequest] | None:
    """Tool calls encoded in `text`, or None if it's ordinary prose."""
    body = text.strip()
    if not body:
        return None
    blocks = _TAGGED.findall(body) or [body]
    calls: list[ToolCallRequest] = []
    for block in blocks:
        m = _FENCE.match(block)
        candidate = m.group(1) if m else block
        parsed = _leading_json(candidate)
        if parsed is None:
            return None
        items = parsed if isinstance(parsed, list) else [parsed]
        for item in items:
            call = _as_call(item)
            if call is None:
                return None
            calls.append(call)
    return calls or None


def _leading_json(text: str) -> Any:
    """First JSON value in `text`; trailing prose is ignored. None if none."""
    try:
        value, _ = json.JSONDecoder().raw_decode(text)
    except ValueError:
        return None
    return value


def _as_call(item: Any) -> ToolCallRequest | None:
    if not isinstance(item, dict):
        return None
    name = item.get("name")
    args = item.get("arguments", item.get("parameters", {}))
    if not isinstance(name, str) or not name or not isinstance(args, dict):
        return None
    return ToolCallRequest(name=name, arguments=args)


def unwrap_tool_response(text: str) -> str:
    """qwen2.5-coder sometimes wraps its prose in the tags meant for tool *results*."""
    m = _RESPONSE_WRAP.match(text)
    return m.group(1) if m else text
