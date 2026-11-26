import uuid

from fastapi import APIRouter, HTTPException, status

from rae_api.deps import AllowRulesDep, ApprovalsDep
from rae_api.schemas.chat import ToolDecision

router = APIRouter(prefix="/chats", tags=["tools"])


@router.post("/{chat_id}/tool-calls/{call_id}/decision", status_code=status.HTTP_204_NO_CONTENT)
async def decide_tool_call(
    chat_id: uuid.UUID,
    call_id: str,
    payload: ToolDecision,
    approvals: ApprovalsDep,
    rules: AllowRulesDep,
) -> None:
    """Approve or deny a tool call the stream is waiting on. 404 once it's no longer pending.

    `always: true` with an approval also records a standing rule, so the tool runs
    without asking from now on (including later in this same reply).
    """
    tool = approvals.tool_of(call_id)
    if tool is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No pending tool call with that id")
    if payload.approved and payload.always and tool:
        await rules.add(tool)
    if not approvals.decide(call_id, payload.approved):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No pending tool call with that id")
