import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from rae_api.deps import SessionDep
from rae_api.schemas.chat import (
    ChatCreate,
    ChatRead,
    MessageCreate,
    MessageRead,
    SendMessageResponse,
)
from rae_db import Chat, Message, Role

router = APIRouter(prefix="/chats", tags=["chats"])


async def _get_chat_or_404(session: SessionDep, chat_id: uuid.UUID) -> Chat:
    chat = await session.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    return chat


@router.get("", response_model=list[ChatRead])
async def list_chats(session: SessionDep) -> list[Chat]:
    result = await session.scalars(select(Chat).order_by(Chat.updated_at.desc()))
    return list(result)


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
async def create_chat(payload: ChatCreate, session: SessionDep) -> Chat:
    chat = Chat(title=payload.title)
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


@router.get("/{chat_id}/messages", response_model=list[MessageRead])
async def list_messages(chat_id: uuid.UUID, session: SessionDep) -> list[Message]:
    await _get_chat_or_404(session, chat_id)
    result = await session.scalars(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
    )
    return list(result)


@router.post(
    "/{chat_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    chat_id: uuid.UUID, payload: MessageCreate, session: SessionDep
) -> SendMessageResponse:
    """Milestone A stub: persist the user message and a canned echo reply.

    Milestone B replaces the echo with the Ollama SSE stream.
    """
    chat = await _get_chat_or_404(session, chat_id)
    user_msg = Message(chat=chat, role=Role.user, content=payload.content)
    assistant_msg = Message(
        chat=chat, role=Role.assistant, content=f"echo: {payload.content}", model="echo"
    )
    session.add_all([user_msg, assistant_msg])
    await session.commit()
    await session.refresh(user_msg)
    await session.refresh(assistant_msg)
    return SendMessageResponse(
        user=MessageRead.model_validate(user_msg),
        assistant=MessageRead.model_validate(assistant_msg),
    )
