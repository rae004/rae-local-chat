"""Tools the user chose to run without asking ("Always allow").

One instance per process (app.state), mirroring the `tool_allow_rules` table in
memory so the agent loop can check membership without a query and a rule added
mid-stream applies to the very next call.
"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rae_db import ToolAllowRule


class AllowRules:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory
        self._tools: set[str] = set()

    async def load(self) -> None:
        async with self._factory() as session:
            self._tools = set(await session.scalars(select(ToolAllowRule.tool)))

    def __contains__(self, tool: object) -> bool:
        return tool in self._tools

    def list(self) -> list[str]:
        return sorted(self._tools)

    async def add(self, tool: str) -> bool:
        """Persist a rule; False if it already existed."""
        if tool in self._tools:
            return False
        async with self._factory() as session:
            await session.merge(ToolAllowRule(tool=tool))
            await session.commit()
        self._tools.add(tool)
        return True

    async def remove(self, tool: str) -> bool:
        """Drop a rule; False if there was none."""
        if tool not in self._tools:
            return False
        async with self._factory() as session:
            await session.execute(delete(ToolAllowRule).where(ToolAllowRule.tool == tool))
            await session.commit()
        self._tools.discard(tool)
        return True
