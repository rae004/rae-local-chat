import uuid

from fastapi import APIRouter, HTTPException, status

from rae_api.deps import ApprovalsDep
from rae_api.schemas.chat import ToolDecision

router = APIRouter(prefix="/chats", tags=["tools"])


@router.post("/{chat_id}/tool-calls/{call_id}/decision", status_code=status.HTTP_204_NO_CONTENT)
async def decide_tool_call(
    chat_id: uuid.UUID, call_id: str, payload: ToolDecision, approvals: ApprovalsDep
) -> None:
    """Approve or deny a tool call the stream is waiting on. 404 once it's no longer pending."""
    if not approvals.decide(call_id, payload.approved):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No pending tool call with that id")
