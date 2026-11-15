from rae_api.services.ollama import ToolCallRequest
from rae_api.services.toolcalls import (
    extract_tool_calls,
    hold_start,
    parse_tool_calls,
    unwrap_tool_response,
)

CALL = ToolCallRequest(name="fs__read", arguments={"path": "notes.txt"})


def test_bare_json_object() -> None:
    assert parse_tool_calls('{"name": "fs__read", "arguments": {"path": "notes.txt"}}') == [CALL]


def test_pretty_printed_and_parameters_alias() -> None:
    text = '{\n  "name": "fs__read",\n  "parameters": {\n    "path": "notes.txt"\n  }\n}'
    assert parse_tool_calls(text) == [CALL]


def test_tagged_blocks_and_fences() -> None:
    inner = '{"name": "fs__read", "arguments": {"path": "notes.txt"}}'
    tagged = f"<tool_call>\n{inner}\n</tool_call>"
    assert parse_tool_calls(tagged) == [CALL]
    fenced = '```json\n{"name": "fs__read", "arguments": {"path": "notes.txt"}}\n```'
    assert parse_tool_calls(fenced) == [CALL]
    two = tagged + "\n" + tagged.replace("notes", "todo")
    assert parse_tool_calls(two) == [CALL, ToolCallRequest("fs__read", {"path": "todo.txt"})]


def test_list_of_calls_and_trailing_prose() -> None:
    text = '[{"name": "a", "arguments": {}}, {"name": "b", "arguments": {"x": 1}}]'
    assert parse_tool_calls(text) == [ToolCallRequest("a", {}), ToolCallRequest("b", {"x": 1})]
    assert parse_tool_calls('{"name": "a", "arguments": {}} I will read it now.') == [
        ToolCallRequest("a", {})
    ]


def test_prose_and_non_call_json_are_not_calls() -> None:
    assert parse_tool_calls("Here is the file content.") is None
    assert parse_tool_calls('{"path": "notes.txt"}') is None
    assert parse_tool_calls('{"name": 3, "arguments": {}}') is None
    assert parse_tool_calls('{"name": "a", "arguments": "oops"}') is None
    assert parse_tool_calls("") is None


def test_hold_start_finds_a_line_that_begins_a_payload() -> None:
    assert hold_start("Sure") is None
    assert hold_start("   ") is None
    assert hold_start("{") == 0
    assert hold_start("  {") == 2
    assert hold_start("<tool_call>") == 0
    text = 'Certainly! Here it is:\n{"name"'
    assert hold_start(text) == text.index("{")
    # Nothing new after what was already streamed.
    assert hold_start(text, start=len(text)) is None
    # A brace mid-sentence is prose, not a payload.
    assert hold_start("use {curly} braces") is None


def test_extract_call_embedded_after_prose() -> None:
    text = (
        "Certainly! Let's run it.\n\n"
        '{"name": "shell__run", "arguments": {"command": "ls", "args": ["-altr"]}}'
    )
    calls, prose = extract_tool_calls(text)
    assert calls == [ToolCallRequest("shell__run", {"command": "ls", "args": ["-altr"]})]
    assert prose == "Certainly! Let's run it."


def test_extract_skips_non_json_braces_and_strips_fences() -> None:
    text = (
        "Step 1. {Create the project entity}\n\n"
        '```json\n{"name": "memory__create_entities", "arguments": {"entities": []}}\n```\n'
        "Then we continue."
    )
    calls, prose = extract_tool_calls(text)
    assert calls == [ToolCallRequest("memory__create_entities", {"entities": []})]
    assert prose == "Step 1. {Create the project entity}\nThen we continue."


def test_extract_returns_text_untouched_without_calls() -> None:
    text = 'Use {"path": "x"} as the body.'
    assert extract_tool_calls(text) == ([], text)


def test_unwrap_tool_response() -> None:
    wrapped = "<tool_response>\nNo such file.\n</tool_response>"
    assert unwrap_tool_response(wrapped) == "No such file."
    assert unwrap_tool_response("plain") == "plain"
    assert unwrap_tool_response("<tool_response>open only") == "<tool_response>open only"
