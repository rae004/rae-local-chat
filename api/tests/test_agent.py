import asyncio
import json

from rae_api.services import agent
from rae_api.services.approvals import Approvals
from tests.fakes import FakeOllama, FakeRegistry


async def _run(fake: FakeOllama, registry: FakeRegistry, **kw: object) -> list[agent.AgentEvent]:
    opts = {"tools_enabled": True, **kw}
    return [ev async for ev in agent.run_agent(fake, registry, "m", [], **opts)]  # type: ignore[arg-type]


async def test_prose_streams_token_by_token() -> None:
    events = await _run(FakeOllama(["Hel", "lo"]), FakeRegistry())
    assert events == [agent.Token("Hel"), agent.Token("lo"), agent.Finished("Hello")]


async def test_system_prompt_and_tool_guidance_lead_the_history() -> None:
    fake = FakeOllama(["ok"])
    await _run(fake, FakeRegistry(), system_prompt="Be terse.")
    first = fake.calls[0][1][0]
    assert first["role"] == "system"
    assert first["content"].startswith("Be terse.") and "fewest calls" in first["content"]
    # Tools off: guidance is left out.
    fake = FakeOllama(["ok"])
    await _run(fake, FakeRegistry(), system_prompt="Be terse.", tools_enabled=False)
    assert fake.calls[0][1][0] == {"role": "system", "content": "Be terse."}
    # No prompt configured: no system message at all.
    fake = FakeOllama(["ok"])
    await _run(fake, FakeRegistry(), tools_enabled=False)
    assert fake.calls[0][1] == []


async def test_tool_call_after_prose_is_executed() -> None:
    call = json.dumps({"name": "fs__read", "arguments": {"path": "notes.txt"}})
    fake = FakeOllama(["Sure, ", "reading it now.\n", call[:12], call[12:]], ["buy milk"])
    registry = FakeRegistry()
    events = await _run(fake, registry)
    kinds = [type(e).__name__ for e in events]
    # Prose streamed live; the JSON line was held back and became the call.
    expected = ["Token", "Token", "AssistantTurn", "ToolCall", "ToolResult", "Token", "Finished"]
    assert kinds == expected
    assert events[0] == agent.Token("Sure, ") and events[1] == agent.Token("reading it now.\n")
    turn = events[2]
    assert isinstance(turn, agent.AssistantTurn)
    assert turn.content == "Sure, reading it now." and turn.tool_calls[0].name == "fs__read"
    assert registry.calls == [("fs__read", {"path": "notes.txt"})]


async def test_json_line_after_prose_that_is_not_a_call_is_released() -> None:
    fake = FakeOllama(["Example:\n", '{"path": "x"}', "\nDone."])
    events = await _run(fake, FakeRegistry())
    assert events == [
        agent.Token("Example:\n"),
        agent.Token('{"path": "x"}\nDone.'),
        agent.Finished('Example:\n{"path": "x"}\nDone.'),
    ]


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


WRITE = {"path": "x", "content": "y"}


async def _collect_with_click(
    fake: FakeOllama, registry: FakeRegistry, approvals: Approvals, click: bool | None
) -> list[agent.AgentEvent]:
    """Run the loop; when a call parks, decide it (None = never click)."""
    events: list[agent.AgentEvent] = []
    async for ev in agent.run_agent(
        fake,  # type: ignore[arg-type]
        registry,
        "m",
        [],
        tools_enabled=True,
        approvals=approvals,
        approval_timeout=0.2,
    ):
        events.append(ev)
        if isinstance(ev, agent.ToolCall) and ev.status == "pending" and click is not None:
            # Simulate the click landing while the loop is parked in wait().
            asyncio.get_running_loop().call_soon(approvals.decide, ev.id, click)
    return events


async def test_write_tool_approved_runs() -> None:
    fake = FakeOllama([FakeOllama.call("fs__write", WRITE)], ["done"])
    registry = FakeRegistry()
    events = await _collect_with_click(fake, registry, Approvals(), click=True)
    kinds = [type(e).__name__ for e in events]
    assert kinds[:4] == ["AssistantTurn", "ToolCall", "ToolDecision", "ToolResult"]
    decision = events[2]
    assert isinstance(decision, agent.ToolDecision) and decision.approved and decision.by == "user"
    result = events[3]
    assert isinstance(result, agent.ToolResult) and result.approved is True and not result.is_error
    assert registry.calls == [("fs__write", WRITE)]


async def test_write_tool_denied_is_fed_back_as_error() -> None:
    fake = FakeOllama([FakeOllama.call("fs__write", WRITE)], ["ok, skipping"])
    registry = FakeRegistry()
    events = await _collect_with_click(fake, registry, Approvals(), click=False)
    result = next(e for e in events if isinstance(e, agent.ToolResult))
    assert result.approved is False and result.is_error and "denied" in result.content
    assert registry.calls == []
    _, messages, _ = fake.calls[1]
    assert messages[-1]["role"] == "tool" and "denied" in messages[-1]["content"]
    assert isinstance(events[-1], agent.Finished) and events[-1].content == "ok, skipping"


async def test_write_tool_times_out_as_denied() -> None:
    fake = FakeOllama([FakeOllama.call("fs__write", WRITE)], ["gave up"])
    registry = FakeRegistry()
    events = await _collect_with_click(fake, registry, Approvals(), click=None)
    decision = next(e for e in events if isinstance(e, agent.ToolDecision))
    assert decision.approved is False and decision.by == "timeout"
    assert registry.calls == []


async def test_read_only_never_parks() -> None:
    fake = FakeOllama([FakeOllama.call("fs__read", {"path": "notes.txt"})], ["ok"])
    events = await _collect_with_click(fake, FakeRegistry(), Approvals(), click=None)
    assert not any(isinstance(e, agent.ToolDecision) for e in events)
    call = next(e for e in events if isinstance(e, agent.ToolCall))
    assert call.status == "auto"


async def test_without_approvals_registry_writes_are_not_offered() -> None:
    fake = FakeOllama(["plain"])
    await _run(fake, FakeRegistry())
    offered = fake.calls[0][2] or []
    assert [t["function"]["name"] for t in offered] == ["fs__read"]
