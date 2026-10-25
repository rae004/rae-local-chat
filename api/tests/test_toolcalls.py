from rae_api.services.ollama import ToolCallRequest
from rae_api.services.toolcalls import could_be_tool_call, parse_tool_calls, unwrap_tool_response

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


def test_could_be_tool_call_prefix() -> None:
    assert could_be_tool_call("   ") is None
    assert could_be_tool_call("  {") is True
    assert could_be_tool_call("<tool_call>") is True
    assert could_be_tool_call("```json") is True
    assert could_be_tool_call("Sure") is False


def test_unwrap_tool_response() -> None:
    wrapped = "<tool_response>\nNo such file.\n</tool_response>"
    assert unwrap_tool_response(wrapped) == "No such file."
    assert unwrap_tool_response("plain") == "plain"
    assert unwrap_tool_response("<tool_response>open only") == "<tool_response>open only"
