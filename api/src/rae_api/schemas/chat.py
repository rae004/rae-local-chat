import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from rae_db import Role


class ChatCreate(BaseModel):
    title: str = Field(default="New chat", max_length=200)


class ChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chat_id: uuid.UUID
    role: Role
    content: str
    model: str | None
    created_at: datetime


class SendMessageResponse(BaseModel):
    user: MessageRead
    assistant: MessageRead
