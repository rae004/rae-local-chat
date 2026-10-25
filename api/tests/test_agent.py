import json

from rae_api.services import agent
from tests.fakes import FakeOllama, FakeRegistry


async def _run(fake: FakeOllama, registry: FakeRegistry, **kw: object) -> list[agent.AgentEvent]:
    opts = {"tools_enabled": True, **kw}
    return [ev async for ev in agent.run_agent(fake, registry, "m", [], **opts)]  # type: ignore[arg-type]


async def test_prose_streams_token_by_token() -> None:
    events = await _run(FakeOllama(["Hel", "lo"]), FakeRegistry())
    assert events == [agent.Token("Hel"), agent.Token("lo"), agent.Finished("Hello")]


async def test_json_looking_text_is_held_then_released_if_not_a_call() -> None:
    events = await _run(FakeOllama(["{", '"a": 1}', " done"]), FakeRegistry())
    # Nothing leaked token-by-token; the whole text arrived once at the end.
    assert events == [agent.Token('{"a": 1} done'), agent.Finished('{"a": 1} done')]


async def test_no_holding_when_tools_disabled() -> None:
    events = await _run(FakeOllama(["{", "x"]), FakeRegistry(), tools_enabled=False)
    assert events[:2] == [agent.Token("{"), agent.Token("x")]


async def test_text_tool_call_is_executed_and_fed_back() -> None:
    call = json.dumps({"name": "fs__read", "arguments": {"path": "notes.txt"}})
    fake = FakeOllama(["{", call[1:]], ["buy ", "milk"])
    registry = FakeRegistry()
    events = await _run(fake, registry)
    kinds = [type(e).__name__ for e in events]
    assert kinds == ["AssistantTurn", "ToolCall", "ToolResult", "Token", "Token", "Finished"]
    turn = events[0]
    assert isinstance(turn, agent.AssistantTurn) and turn.content == ""
    assert turn.tool_calls[0].name == "fs__read" and turn.tool_calls[0].read_only
    assert registry.calls == [("fs__read", {"path": "notes.txt"})]
    result = events[2]
    assert isinstance(result, agent.ToolResult) and result.content == "buy milk\n"
    # Second Ollama call carries assistant tool_calls + tool message.
    _, messages, _ = fake.calls[1]
    assert messages[-2]["tool_calls"] == [
        {"function": {"name": "fs__read", "arguments": {"path": "notes.txt"}}}
    ]
    assert messages[-1] == {"role": "tool", "tool_name": "fs__read", "content": "buy milk\n"}


async def test_unknown_tool_is_an_error_result() -> None:
    fake = FakeOllama([FakeOllama.call("nope__x", {})], ["sorry"])
    events = await _run(fake, FakeRegistry())
    result = next(e for e in events if isinstance(e, agent.ToolResult))
    assert result.is_error and "Unknown tool" in result.content
    assert result.call.server == "" and not result.call.read_only


async def test_round_cap_forces_a_toolless_final_answer() -> None:
    # The model asks for a tool forever; on the last round no tools are offered.
    fake = FakeOllama([FakeOllama.call("fs__read", {"path": "notes.txt"})])
    events = await _run(fake, FakeRegistry(), max_rounds=3)
    assert len(fake.calls) == 3
    assert fake.calls[0][2] and fake.calls[1][2] and fake.calls[2][2] is None
    assert isinstance(events[-1], agent.Finished)
