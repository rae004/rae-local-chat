from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rae_api.routers import chats
from rae_api.settings import get_settings

app = FastAPI(title="rae-local-chat api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chats.router)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
