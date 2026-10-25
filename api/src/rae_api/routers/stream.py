"""SSE endpoint: persist the prompt, stream Ollama's reply, persist the reply.

Events (all `data` is JSON):
  user   -> MessageRead      the persisted user message
  token  -> {"content": str} one streamed chunk
  done   -> MessageRead      the persisted assistant message
  error  -> {"detail": str}  Ollama failed; the user message is still persisted
"""

import json
import uuid
from collections.abc import AsyncIterator

import anyio
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rae_api.deps import OllamaDep, SessionDep, SessionFactoryDep, SettingsDep
from rae_api.schemas.chat import MessageCreate, MessageRead
from rae_api.services.ollama import OllamaClient, OllamaError
from rae_db import Chat, Message, Role

router = APIRouter(prefix="/chats", tags=["stream"])

TITLE_MAX = 60


def title_from_prompt(prompt: str) -> str:
    """First line of the prompt, whitespace-collapsed, cut at a word boundary."""
    first = " ".join(prompt.strip().splitlines()[0].split()) if prompt.strip() else "New chat"
    if len(first) <= TITLE_MAX:
        return first
    cut = first[:TITLE_MAX].rsplit(" ", 1)[0] or first[:TITLE_MAX]
    return cut + "…"


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def sse(event: str, data: BaseModel | dict[str, object]) -> str:
    body = data.model_dump_json() if isinstance(data, BaseModel) else json.dumps(data)
    return f"event: {event}\ndata: {body}\n\n"


async def _history(session: AsyncSession, chat_id: uuid.UUID) -> list[dict[str, str]]:
    rows = await session.scalars(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
    )
    return [{"role": m.role.value, "content": m.content} for m in rows]


async def _touch_chat(session: AsyncSession, chat_id: uuid.UUID) -> None:
    """Bump updated_at so the sidebar sorts by latest activity."""
    chat = await session.get(Chat, chat_id)
    if chat is not None:
        chat.updated_at = func.now()


async def _persist_assistant(
    factory: async_sessionmaker[AsyncSession],
    chat_id: uuid.UUID,
    content: str,
    model: str,
    *,
    partial: bool,
) -> Message:
    async with factory() as session:
        msg = Message(chat_id=chat_id, role=Role.assistant, content=content, model=model)
        if partial:
            msg.content = content + "\n\n_[stopped]_"
        session.add(msg)
        await _touch_chat(session, chat_id)
        await session.commit()
        await session.refresh(msg)
        return msg


async def _stream(
    factory: async_sessionmaker[AsyncSession],
    chat_id: uuid.UUID,
    prompt: str,
    ollama: OllamaClient,
    model: str,
) -> AsyncIterator[str]:
    # Own sessions: request-scoped dependencies are torn down before a
    # StreamingResponse body runs.
    async with factory() as session:
        is_first = not await session.scalar(
            select(func.count()).select_from(Message).where(Message.chat_id == chat_id)
        )
        user_msg = Message(chat_id=chat_id, role=Role.user, content=prompt)
        session.add(user_msg)
        chat = await session.get(Chat, chat_id)
        if chat is not None:
            chat.updated_at = func.now()
            if is_first:
                # First message in this chat: derive the title from it.
                chat.title = title_from_prompt(prompt)
        await session.commit()
        await session.refresh(user_msg)
        history = await _history(session, chat_id)
    yield sse("user", MessageRead.model_validate(user_msg))

    parts: list[str] = []
    finished = False
    try:
        async for chunk in ollama.chat_stream(model, history):
            if chunk.content:
                parts.append(chunk.content)
                yield sse("token", {"content": chunk.content})
            if chunk.done:
                finished = True
                break
    except OllamaError as e:
        yield sse("error", {"detail": str(e)})
        return
    except Exception as e:  # noqa: BLE001 — surface anything else to the client, then persist
        yield sse("error", {"detail": f"{type(e).__name__}: {e}"})
        return
    finally:
        # Client went away mid-stream (CancelledError): keep what we got. The
        # request's cancel scope is already cancelled, so shield the DB write.
        if not finished and parts:
            with anyio.CancelScope(shield=True):
                await _persist_assistant(factory, chat_id, "".join(parts), model, partial=True)

    assistant = await _persist_assistant(factory, chat_id, "".join(parts), model, partial=False)
    yield sse("done", MessageRead.model_validate(assistant))


@router.post("/{chat_id}/stream", status_code=status.HTTP_200_OK)
async def stream_message(
    chat_id: uuid.UUID,
    payload: MessageCreate,
    session: SessionDep,
    factory: SessionFactoryDep,
    ollama: OllamaDep,
    settings: SettingsDep,
) -> StreamingResponse:
    if await session.get(Chat, chat_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    return StreamingResponse(
        _stream(factory, chat_id, payload.content, ollama, settings.ollama_model),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
