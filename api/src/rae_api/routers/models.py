from fastapi import APIRouter, HTTPException, status

from rae_api.deps import OllamaDep, SettingsDep
from rae_api.schemas.chat import ModelRead
from rae_api.services.ollama import OllamaError

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelRead])
async def list_models(ollama: OllamaDep) -> list[ModelRead]:
    try:
        return [ModelRead.model_validate(m) for m in await ollama.list_models()]
    except OllamaError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@router.get("/default")
async def default_model(settings: SettingsDep) -> dict[str, str]:
    return {"name": settings.ollama_model}
