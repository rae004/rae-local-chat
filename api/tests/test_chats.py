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


async def test_list_messages_unknown_chat_404(client: AsyncClient) -> None:
    r = await client.get(f"/chats/{uuid.uuid4()}/messages")
    assert r.status_code == 404
