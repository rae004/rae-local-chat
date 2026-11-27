from fastapi import APIRouter, HTTPException, status

from rae_api.deps import AllowRulesDep, RegistryDep
from rae_api.schemas.chat import AllowRuleRead, ToolRead, ToolsRead

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


@router.get("/allow-rules", response_model=list[AllowRuleRead])
async def list_allow_rules(rules: AllowRulesDep) -> list[AllowRuleRead]:
    """Tools that run without asking ("Always allow"), by qualified name."""
    return [AllowRuleRead(tool=t) for t in rules.list()]


@router.delete("/allow-rules/{tool}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_allow_rule(tool: str, rules: AllowRulesDep) -> None:
    """Revoke a rule; the tool asks again from the next call on."""
    if not await rules.remove(tool):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such rule")
