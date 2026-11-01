import json
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from httpx import AsyncClient

from rae_api.deps import get_ollama, get_registry
from rae_api.main import app
from tests.fakes import FakeOllama, FakeRegistry


def parse_sse(body: str) -> list[tuple[str, dict[str, object]]]:
    events: list[tuple[str, dict[str, object]]] = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


@pytest.fixture
def fake_ollama() -> Iterator[FakeOllama]:
    fake = FakeOllama(["Hel", "lo", "!"])
    app.dependency_overrides[get_ollama] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_ollama, None)


async def _new_chat(client: AsyncClient) -> str:
    return str((await client.post("/chats", json={})).json()["id"])


async def test_stream_persists_both_sides(client: AsyncClient, fake_ollama: FakeOllama) -> None:
    chat_id = await _new_chat(client)

    r = await client.post(f"/chats/{chat_id}/stream", json={"content": "hi"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    events = parse_sse(r.text)
    assert [e for e, _ in events] == ["user", "token", "token", "token", "done"]
    assert events[0][1]["content"] == "hi"
    assert "".join(str(d["content"]) for e, d in events if e == "token") == "Hello!"
    done = events[-1][1]
    assert done["role"] == "assistant"
    assert done["content"] == "Hello!"

    r = await client.get(f"/chats/{chat_id}/messages")
    assert [(m["role"], m["content"]) for m in r.json()] == [
        ("user", "hi"),
        ("assistant", "Hello!"),
    ]


async def test_stream_sends_full_history_to_ollama(
    client: AsyncClient, fake_ollama: FakeOllama
) -> None:
    chat_id = await _new_chat(client)
    await client.post(f"/chats/{chat_id}/stream", json={"content": "first"})
    await client.post(f"/chats/{chat_id}/stream", json={"content": "second"})

    _, history, _ = fake_ollama.calls[1]
    assert [m["role"] for m in history] == ["user", "assistant", "user"]
    assert history[-1]["content"] == "second"


async def test_stream_error_keeps_user_message(client: AsyncClient) -> None:
    fake = FakeOllama(["a", "b"], fail_after=1)
    app.dependency_overrides[get_ollama] = lambda: fake
    try:
        chat_id = await _new_chat(client)
        r = await client.post(f"/chats/{chat_id}/stream", json={"content": "boom"})
        events = parse_sse(r.text)
        assert [e for e, _ in events] == ["user", "token", "error"]
        assert events[-1][1] == {"detail": "model exploded"}

        r = await client.get(f"/chats/{chat_id}/messages")
        msgs = r.json()
        # Partial output is kept, marked as stopped.
        assert [m["role"] for m in msgs] == ["user", "assistant"]
        assert msgs[1]["content"].startswith("a")
        assert "[stopped]" in msgs[1]["content"]
    finally:
        app.dependency_overrides.pop(get_ollama, None)


async def test_stream_unknown_chat_404(client: AsyncClient, fake_ollama: FakeOllama) -> None:
    r = await client.post(f"/chats/{uuid.uuid4()}/stream", json={"content": "x"})
    assert r.status_code == 404


async def test_stream_rejects_empty(client: AsyncClient, fake_ollama: FakeOllama) -> None:
    chat_id = await _new_chat(client)
    r = await client.post(f"/chats/{chat_id}/stream", json={"content": ""})
    assert r.status_code == 422


async def test_first_message_sets_title_and_bumps_updated_at(
    client: AsyncClient, fake_ollama: FakeOllama
) -> None:
    older = await _new_chat(client)
    newer = await _new_chat(client)
    assert [c["id"] for c in (await client.get("/chats")).json()] == [newer, older]

    before = (await client.get("/chats")).json()[1]["updated_at"]
    await client.post(f"/chats/{older}/stream", json={"content": "How do I  write\na sonnet?"})

    chats = (await client.get("/chats")).json()
    assert [c["id"] for c in chats] == [older, newer]  # activity moved it to the top
    assert chats[0]["title"] == "How do I write"
    assert chats[0]["updated_at"] > before

    # Second message leaves the title alone.
    await client.post(f"/chats/{older}/stream", json={"content": "Make it shorter"})
    assert (await client.get("/chats")).json()[0]["title"] == "How do I write"


def test_title_from_prompt_truncates_at_word_boundary() -> None:
    from rae_api.routers.stream import title_from_prompt

    assert title_from_prompt("short") == "short"
    long = "word " * 30
    t = title_from_prompt(long)
    assert t.endswith("…") and len(t) <= 61 and not t[:-1].endswith(" ")
    assert title_from_prompt("x" * 100) == "x" * 60 + "…"
    assert title_from_prompt("   ") == "New chat"


async def test_stream_uses_requested_model(client: AsyncClient, fake_ollama: FakeOllama) -> None:
    chat_id = await _new_chat(client)
    r = await client.post(
        f"/chats/{chat_id}/stream", json={"content": "hi", "model": "starcoder2:7b"}
    )
    assert r.status_code == 200
    assert fake_ollama.calls[0][0] == "starcoder2:7b"
    assert parse_sse(r.text)[-1][1]["model"] == "starcoder2:7b"

    r = await client.post(f"/chats/{chat_id}/stream", json={"content": "again"})
    assert fake_ollama.calls[1][0] == "qwen2.5-coder:latest"  # settings default


async def test_list_models(client: AsyncClient, fake_ollama: FakeOllama) -> None:
    r = await client.get("/models")
    assert r.status_code == 200
    assert [m["name"] for m in r.json()] == ["qwen2.5-coder:latest", "starcoder2:7b"]
    assert r.json()[0]["parameter_size"] == "7.6B"
    assert [m["tools"] for m in r.json()] == [True, False]

    r = await client.get("/models/default")
    assert r.json() == {"name": "qwen2.5-coder:latest"}


# --- tool rounds ---------------------------------------------------------------


@pytest.fixture
def registry() -> Iterator[FakeRegistry]:
    reg = FakeRegistry()
    app.dependency_overrides[get_registry] = lambda: reg
    yield reg
    app.dependency_overrides.pop(get_registry, None)


def _tooling_ollama(*, text: bool) -> FakeOllama:
    """Round 1 asks for `fs__read` (structured, or as bare JSON text); round 2 answers."""
    call: dict[str, Any] = {"name": "fs__read", "arguments": {"path": "notes.txt"}}
    first: list[Any] = [json.dumps(call)] if text else [FakeOllama.call(**call)]
    return FakeOllama(first, ["It says: ", "buy milk"])


@pytest.mark.parametrize("as_text", [False, True])
async def test_tool_round_is_streamed_and_persisted(
    client: AsyncClient, registry: FakeRegistry, as_text: bool
) -> None:
    fake = _tooling_ollama(text=as_text)
    app.dependency_overrides[get_ollama] = lambda: fake
    try:
        chat_id = await _new_chat(client)
        r = await client.post(f"/chats/{chat_id}/stream", json={"content": "read my notes"})
        events = parse_sse(r.text)
        kinds = [e for e, _ in events]
        assert kinds == [
            "user",
            "message",  # assistant turn with tool_calls
            "tool_call",
            "tool_result",
            "message",  # tool row
            "token",
            "token",
            "done",
        ]
        call = events[2][1]
        assert call["name"] == "fs__read" and call["server"] == "fs" and call["read_only"]
        assert call["arguments"] == {"path": "notes.txt"}
        result = events[3][1]
        assert result["id"] == call["id"] and not result["is_error"]
        assert result["content"] == "buy milk\n"
        assert events[-1][1]["content"] == "It says: buy milk"
        assert registry.calls == [("fs__read", {"path": "notes.txt"})]

        # Round 2 saw the tool exchange in Ollama's own shape.
        _, history, _ = fake.calls[1]
        assert [m["role"] for m in history] == ["user", "assistant", "tool"]
        assert history[1]["tool_calls"][0]["function"]["name"] == "fs__read"
        assert history[2] == {"role": "tool", "tool_name": "fs__read", "content": "buy milk\n"}
        # Only read-only tools were offered.
        offered = fake.calls[0][2] or []
        assert [t["function"]["name"] for t in offered] == ["fs__read"]

        rows = (await client.get(f"/chats/{chat_id}/messages")).json()
        assert [m["role"] for m in rows] == ["user", "assistant", "tool", "assistant"]
        assert rows[1]["tool_calls"][0]["name"] == "fs__read"
        assert rows[2]["tool_call_id"] == call["id"] and rows[2]["tool_name"] == "fs__read"
        assert rows[2]["tool_is_error"] is False

        # The next turn replays the whole exchange to the model.
        await client.post(f"/chats/{chat_id}/stream", json={"content": "thanks"})
        _, history, _ = fake.calls[2]
        assert [m["role"] for m in history] == ["user", "assistant", "tool", "assistant", "user"]
    finally:
        app.dependency_overrides.pop(get_ollama, None)


async def test_tools_can_be_disabled_per_message(
    client: AsyncClient, registry: FakeRegistry
) -> None:
    fake = FakeOllama(["plain"])
    app.dependency_overrides[get_ollama] = lambda: fake
    try:
        chat_id = await _new_chat(client)
        await client.post(f"/chats/{chat_id}/stream", json={"content": "hi", "tools": False})
        assert fake.calls[0][2] is None
        await client.post(f"/chats/{chat_id}/stream", json={"content": "hi"})
        assert fake.calls[1][2] is not None
    finally:
        app.dependency_overrides.pop(get_ollama, None)


async def test_write_tool_is_refused_until_approval_flow_exists(
    client: AsyncClient, registry: FakeRegistry
) -> None:
    fake = FakeOllama([FakeOllama.call("fs__write", {"path": "x", "content": "y"})], ["ok"])
    app.dependency_overrides[get_ollama] = lambda: fake
    try:
        chat_id = await _new_chat(client)
        r = await client.post(f"/chats/{chat_id}/stream", json={"content": "write it"})
        results = [d for e, d in parse_sse(r.text) if e == "tool_result"]
        assert results[0]["is_error"] and "approval" in str(results[0]["content"])
        assert registry.calls == []
    finally:
        app.dependency_overrides.pop(get_ollama, None)


async def test_list_tools(client: AsyncClient, registry: FakeRegistry) -> None:
    r = await client.get("/tools")
    assert r.status_code == 200
    body = r.json()
    assert body["servers"] == {"fs": "ok"}
    assert [(t["qualified"], t["read_only"]) for t in body["tools"]] == [
        ("fs__read", True),
        ("fs__write", False),
    ]
