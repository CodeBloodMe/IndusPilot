from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_org_id
from app.schemas.domain import CopilotChatRequest
from app.agents.orchestrator import IndusPilotAgentOrchestrator

router = APIRouter()

@router.post("/chat")
def chat_with_copilot(
    payload: CopilotChatRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Multilingual AI Manufacturing Copilot endpoint.
    Accepts queries in English, Hindi, and Hinglish.
    Invokes specialized agents and deterministic backend tools.
    """
    orchestrator = IndusPilotAgentOrchestrator(db_session=db)
    response = orchestrator.process_conversational_query(
        query=payload.query,
        context=payload.context or {}
    )
    return response

