import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from rae_db import Role


class ChatCreate(BaseModel):
    title: str = Field(default="New chat", max_length=200)


class ChatUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)
    # Ollama model name; None = server default (OLLAMA_MODEL).
    model: str | None = Field(default=None, max_length=100)
    # Offer MCP tools to the model for this turn.
    tools: bool = True


class ToolCallRead(BaseModel):
    """One tool invocation requested by the model (SSE `tool_call`, and persisted)."""

    id: str
    name: str
    server: str
    arguments: dict[str, Any]
    read_only: bool


class ToolResultRead(BaseModel):
    """SSE `tool_result`: what the tool returned for `id`."""

    id: str
    name: str
    content: str
    is_error: bool


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chat_id: uuid.UUID
    role: Role
    content: str
    model: str | None
    created_at: datetime
    # assistant rows that requested tools
    tool_calls: list[ToolCallRead] | None = None
    # tool rows
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_is_error: bool | None = None


class ModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    size: int
    parameter_size: str | None
    family: str | None
    tools: bool


class ToolRead(BaseModel):
    server: str
    name: str
    qualified: str
    description: str
    read_only: bool


class ToolsRead(BaseModel):
    servers: dict[str, str]
    tools: list[ToolRead]
