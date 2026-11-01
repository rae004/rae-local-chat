"""SSE endpoint: persist the prompt, run the tool loop against Ollama, persist each step.

Events (all `data` is JSON):
  user        -> MessageRead      the persisted user message
  token       -> {"content": str} one streamed chunk of assistant prose
  tool_call   -> ToolCallRead     the model asked for a tool (running now, or refused)
  tool_result -> ToolResultRead   what the tool returned
  message     -> MessageRead      an intermediate persisted row (assistant w/ tool_calls, tool)
  done        -> MessageRead      the persisted final assistant message
  error       -> {"detail": str}  Ollama failed; everything persisted so far stays
"""

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import anyio
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rae_api.deps import OllamaDep, RegistryDep, SessionDep, SessionFactoryDep, SettingsDep
from rae_api.schemas.chat import MessageCreate, MessageRead, ToolCallRead, ToolResultRead
from rae_api.services import agent
from rae_api.services.mcp import McpRegistry
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


def to_ollama(m: Message) -> dict[str, Any]:
    """One persisted row as an Ollama chat message."""
    if m.role is Role.tool:
        return {"role": "tool", "tool_name": m.tool_name or "", "content": m.content}
    msg: dict[str, Any] = {"role": m.role.value, "content": m.content}
    if m.tool_calls:
        msg["tool_calls"] = [
            {"function": {"name": c["name"], "arguments": c["arguments"]}} for c in m.tool_calls
        ]
    return msg


async def _history(session: AsyncSession, chat_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = await session.scalars(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
    )
    return [to_ollama(m) for m in rows]


async def _touch_chat(session: AsyncSession, chat_id: uuid.UUID) -> None:
    """Bump updated_at so the sidebar sorts by latest activity."""
    chat = await session.get(Chat, chat_id)
    if chat is not None:
        chat.updated_at = func.now()


async def _persist(factory: async_sessionmaker[AsyncSession], msg: Message) -> Message:
    async with factory() as session:
        session.add(msg)
        await _touch_chat(session, msg.chat_id)
        await session.commit()
        await session.refresh(msg)
        return msg


def _assistant(chat_id: uuid.UUID, content: str, model: str, **extra: Any) -> Message:
    return Message(chat_id=chat_id, role=Role.assistant, content=content, model=model, **extra)


async def _stream(
    factory: async_sessionmaker[AsyncSession],
    chat_id: uuid.UUID,
    payload: MessageCreate,
    ollama: OllamaClient,
    registry: McpRegistry,
    model: str,
    *,
    tools_enabled: bool,
    max_rounds: int,
) -> AsyncIterator[str]:
    # Own sessions: request-scoped dependencies are torn down before a
    # StreamingResponse body runs.
    async with factory() as session:
        is_first = not await session.scalar(
            select(func.count()).select_from(Message).where(Message.chat_id == chat_id)
        )
        user_msg = Message(chat_id=chat_id, role=Role.user, content=payload.content)
        session.add(user_msg)
        chat = await session.get(Chat, chat_id)
        if chat is not None:
            chat.updated_at = func.now()
            if is_first:
                # First message in this chat: derive the title from it.
                chat.title = title_from_prompt(payload.content)
        await session.commit()
        await session.refresh(user_msg)
        history = await _history(session, chat_id)
    yield sse("user", MessageRead.model_validate(user_msg))

    parts: list[str] = []  # prose of the turn in flight, for partial persistence
    finished = False
    try:
        events = agent.run_agent(
            ollama,
            registry,
            model,
            history,
            tools_enabled=tools_enabled and payload.tools,
            max_rounds=max_rounds,
        )
        async for ev in events:
            match ev:
                case agent.Token(content):
                    parts.append(content)
                    yield sse("token", {"content": content})
                case agent.AssistantTurn(content, calls):
                    parts.clear()
                    row = await _persist(
                        factory,
                        _assistant(
                            chat_id, content, model, tool_calls=[c.as_record() for c in calls]
                        ),
                    )
                    yield sse("message", MessageRead.model_validate(row))
                case agent.ToolCall() as call:
                    yield sse("tool_call", ToolCallRead(**call.as_record()))
                case agent.ToolResult(call, content, is_error):
                    row = await _persist(
                        factory,
                        Message(
                            chat_id=chat_id,
                            role=Role.tool,
                            content=content,
                            tool_call_id=call.id,
                            tool_name=call.name,
                            tool_is_error=is_error,
                        ),
                    )
                    result = ToolResultRead(
                        id=call.id, name=call.name, content=content, is_error=is_error
                    )
                    yield sse("tool_result", result)
                    yield sse("message", MessageRead.model_validate(row))
                case agent.Finished(content):
                    finished = True
                    row = await _persist(factory, _assistant(chat_id, content, model))
                    yield sse("done", MessageRead.model_validate(row))
    except OllamaError as e:
        yield sse("error", {"detail": str(e)})
    except Exception as e:  # noqa: BLE001 — surface anything else to the client, then persist
        yield sse("error", {"detail": f"{type(e).__name__}: {e}"})
    finally:
        # Error, or the client went away mid-stream (CancelledError): keep what
        # we got. The request's cancel scope may already be cancelled, so shield.
        if not finished and parts:
            with anyio.CancelScope(shield=True):
                await _persist(
                    factory, _assistant(chat_id, "".join(parts) + "\n\n_[stopped]_", model)
                )


@router.post("/{chat_id}/stream", status_code=status.HTTP_200_OK)
async def stream_message(
    chat_id: uuid.UUID,
    payload: MessageCreate,
    session: SessionDep,
    factory: SessionFactoryDep,
    ollama: OllamaDep,
    registry: RegistryDep,
    settings: SettingsDep,
) -> StreamingResponse:
    if await session.get(Chat, chat_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    return StreamingResponse(
        _stream(
            factory,
            chat_id,
            payload,
            ollama,
            registry,
            payload.model or settings.ollama_model,
            tools_enabled=settings.tools_enabled,
            max_rounds=settings.agent_max_rounds,
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
