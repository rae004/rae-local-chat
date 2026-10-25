import json
import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import AsyncClient

from rae_api.deps import get_ollama
from rae_api.main import app
from rae_api.services.ollama import ChatChunk, ModelInfo, OllamaError


class FakeOllama:
    def __init__(self, tokens: list[str], *, fail_after: int | None = None) -> None:
        self.tokens = tokens
        self.fail_after = fail_after
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    async def chat_stream(
        self, model: str, messages: list[dict[str, str]]
    ) -> AsyncIterator[ChatChunk]:
        self.calls.append((model, messages))
        for i, tok in enumerate(self.tokens):
            if self.fail_after is not None and i == self.fail_after:
                raise OllamaError("model exploded")
            yield ChatChunk(content=tok, done=False, model=model)
        yield ChatChunk(content="", done=True, model=model)

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(name="qwen2.5-coder:latest", size=4, parameter_size="7.6B", family="qwen2"),
            ModelInfo(name="starcoder2:7b", size=4, parameter_size="7B", family="starcoder2"),
        ]


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

    _, history = fake_ollama.calls[1]
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

    r = await client.get("/models/default")
    assert r.json() == {"name": "qwen2.5-coder:latest"}
