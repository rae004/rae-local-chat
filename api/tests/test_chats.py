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


async def test_rename_chat(client: AsyncClient) -> None:
    chat_id = (await client.post("/chats", json={})).json()["id"]
    r = await client.patch(f"/chats/{chat_id}", json={"title": "  Lighthouse story  "})
    assert r.status_code == 200
    assert r.json()["title"] == "Lighthouse story"

    r = await client.patch(f"/chats/{chat_id}", json={"title": ""})
    assert r.status_code == 422


async def test_delete_chat(client: AsyncClient) -> None:
    chat_id = (await client.post("/chats", json={})).json()["id"]
    r = await client.delete(f"/chats/{chat_id}")
    assert r.status_code == 204
    assert (await client.get(f"/chats/{chat_id}/messages")).status_code == 404
    assert (await client.delete(f"/chats/{chat_id}")).status_code == 404
    assert (await client.get("/chats")).json() == []
