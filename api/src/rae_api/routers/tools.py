from fastapi import APIRouter

from rae_api.deps import RegistryDep
from rae_api.schemas.chat import ToolRead, ToolsRead

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=ToolsRead)
async def list_tools(registry: RegistryDep, refresh: bool = False) -> ToolsRead:
    """Tool catalogue across all MCP servers, plus per-server connection status."""
    if refresh:
        await registry.refresh()
    return ToolsRead(
        servers=dict(registry.status),
        tools=[
            ToolRead(
                server=t.server,
                name=t.name,
                qualified=t.qualified,
                description=t.description,
                read_only=t.read_only,
            )
            for t in registry.tools.values()
        ],
    )
