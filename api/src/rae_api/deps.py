from typing import Annotated

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rae_api.services.mcp import McpRegistry
from rae_api.services.ollama import OllamaClient
from rae_api.settings import Settings, get_settings
from rae_db import get_session, get_session_factory

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionFactoryDep = Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)]


def get_ollama(request: Request) -> OllamaClient:
    http: httpx.AsyncClient = request.app.state.ollama_http
    return OllamaClient(http)


OllamaDep = Annotated[OllamaClient, Depends(get_ollama)]


def get_registry(request: Request) -> McpRegistry:
    registry: McpRegistry = request.app.state.mcp
    return registry


RegistryDep = Annotated[McpRegistry, Depends(get_registry)]
