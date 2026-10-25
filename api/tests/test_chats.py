import uuid

from httpx import AsyncClient


async def test_health(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_create_and_list_chats(client: AsyncClient) -> None:
    r = await client.post("/chats", json={})
    assert r.status_code == 201
    chat = r.json()
    assert chat["title"] == "New chat"

    r = await client.get("/chats")
    assert r.status_code == 200
    assert [c["id"] for c in r.json()] == [chat["id"]]


async def test_send_message_echoes(client: AsyncClient) -> None:
    chat_id = (await client.post("/chats", json={})).json()["id"]

    r = await client.post(f"/chats/{chat_id}/messages", json={"content": "hello"})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["role"] == "user"
    assert body["user"]["content"] == "hello"
    assert body["assistant"]["role"] == "assistant"
    assert body["assistant"]["content"] == "echo: hello"
    assert body["assistant"]["model"] == "echo"

    r = await client.get(f"/chats/{chat_id}/messages")
    assert [m["role"] for m in r.json()] == ["user", "assistant"]


async def test_send_message_unknown_chat_404(client: AsyncClient) -> None:
    r = await client.post(f"/chats/{uuid.uuid4()}/messages", json={"content": "x"})
    assert r.status_code == 404


async def test_send_message_rejects_empty(client: AsyncClient) -> None:
    chat_id = (await client.post("/chats", json={})).json()["id"]
    r = await client.post(f"/chats/{chat_id}/messages", json={"content": ""})
    assert r.status_code == 422
