from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rae_api.routers import chats, models, stream
from rae_api.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    timeout = httpx.Timeout(10.0, read=settings.ollama_read_timeout)
    async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=timeout) as http:
        app.state.ollama_http = http
        yield


app = FastAPI(title="rae-local-chat api", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chats.router)
app.include_router(stream.router)
app.include_router(models.router)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
