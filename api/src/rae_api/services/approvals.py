"""In-process registry of tool calls waiting for the user's approve/deny click.

The SSE stream parks on `wait()`; the decision endpoint calls `decide()`.
State lives in memory, so the API must run as a single process (it does).
"""

from dataclasses import dataclass, field

import anyio


@dataclass
class _Pending:
    tool: str
    event: anyio.Event = field(default_factory=anyio.Event)
    approved: bool | None = None


class Approvals:
    def __init__(self) -> None:
        self._pending: dict[str, _Pending] = {}

    def register(self, call_id: str, tool: str = "") -> None:
        """Start tracking `call_id` before announcing it, so a fast click can't be lost."""
        self._pending[call_id] = _Pending(tool)

    def tool_of(self, call_id: str) -> str | None:
        """Qualified tool name of a pending call, or None if nothing is waiting under that id."""
        pending = self._pending.get(call_id)
        return pending.tool if pending is not None else None

    async def wait(self, call_id: str, wait_seconds: float) -> bool | None:
        """True approved, False denied, None timed out. Forgets the call afterwards."""
        pending = self._pending.get(call_id)
        if pending is None:
            return None
        try:
            with anyio.move_on_after(wait_seconds):
                await pending.event.wait()
        finally:
            self._pending.pop(call_id, None)
        return pending.approved

    def decide(self, call_id: str, approved: bool) -> bool:
        """Record the decision; False if nothing is waiting under that id."""
        pending = self._pending.get(call_id)
        if pending is None or pending.approved is not None:
            return False
        pending.approved = approved
        pending.event.set()
        return True

    def is_pending(self, call_id: str) -> bool:
        return call_id in self._pending
