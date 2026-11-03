"""
IndusPilot Copilot & Multi-Agent LangGraph REST API Endpoints
Provides persistent conversational memory, LangGraph supervisor execution,
detailed telemetry step-tracing, and human-in-the-loop approval endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_org_id
from app.schemas.domain import (
    CopilotChatRequest,
    CopilotConversationCreate,
    CopilotConversationUpdate,
    CopilotMessagePostRequest,
    CopilotActionDecisionRequest
)
from app.services.copilot_service import (
    list_conversations,
    get_conversation_details,
    create_conversation,
    update_conversation,
    delete_conversation,
    post_message_and_execute,
    get_run_details,
    get_run_events,
    list_pending_actions,
    approve_pending_action,
    reject_pending_action
)
from app.models.entities import CopilotConversation

router = APIRouter()


# ============================================================================
# CONVERSATION THREAD MANAGEMENT
# ============================================================================

@router.get("/conversations")
def get_conversations(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Lists persistent conversations for the organization."""
    return list_conversations(db=db, org_id=org_id, limit=limit)


@router.post("/conversations", status_code=201)
def create_new_conversation(
    payload: CopilotConversationCreate,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Creates a new conversation thread."""
    return create_conversation(db=db, org_id=org_id, title=payload.title)


@router.get("/conversations/{conversation_id}")
def get_single_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves full conversation with chronological messages, tool calls, and structured cards."""
    return get_conversation_details(db=db, org_id=org_id, conversation_id=conversation_id)


@router.patch("/conversations/{conversation_id}")
def update_single_conversation(
    conversation_id: str,
    payload: CopilotConversationUpdate,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Renames or archives a conversation."""
    return update_conversation(
        db=db,
        org_id=org_id,
        conversation_id=conversation_id,
        title=payload.title,
        is_archived=payload.is_archived
    )


@router.delete("/conversations/{conversation_id}")
def delete_single_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Permanently deletes a conversation and cascade removes all messages and runs."""
    return delete_conversation(db=db, org_id=org_id, conversation_id=conversation_id)


# ============================================================================
# LANGGRAPH WORKFLOW EXECUTION
# ============================================================================

@router.post("/conversations/{conversation_id}/messages")
def send_message_to_conversation(
    conversation_id: str,
    payload: CopilotMessagePostRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Primary LangGraph multi-agent execution endpoint:
    Posts user query to conversation, runs IndusPilotSupervisorGraph across the 9 agents,
    persists execution steps, and returns the synthesized response with structured card.
    """
    return post_message_and_execute(
        db=db,
        org_id=org_id,
        conversation_id=conversation_id,
        content=payload.content
    )


# ============================================================================
# AGENT RUN TELEMETRY & APPROVAL ACTIONS
# ============================================================================

@router.get("/runs/{run_id}")
def get_agent_run(
    run_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves execution details for a specific LangGraph agent run."""
    return get_run_details(db=db, org_id=org_id, run_id=run_id)


@router.get("/runs/{run_id}/events")
def get_agent_run_events(
    run_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves chronological execution events for the Agent Activity Panel."""
    return get_run_events(db=db, org_id=org_id, run_id=run_id)


@router.get("/actions")
def list_agent_actions(
    status: Optional[str] = Query(None),
    conversation_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Lists pending or historical agent actions for commercial review."""
    return list_pending_actions(
        db=db,
        org_id=org_id,
        status=status,
        conversation_id=conversation_id
    )


@router.post("/actions/{action_id}/approve")
def approve_agent_action(
    action_id: str,
    payload: CopilotActionDecisionRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Human-in-the-loop: Authorizes a paused commercial action."""
    return approve_pending_action(
        db=db,
        org_id=org_id,
        action_id=action_id,
        approver_name=payload.approver_name or "Commercial Director",
        decision_reason=payload.reason
    )


@router.post("/actions/{action_id}/reject")
def reject_agent_action(
    action_id: str,
    payload: CopilotActionDecisionRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Human-in-the-loop: Rejects a paused commercial action."""
    return reject_pending_action(
        db=db,
        org_id=org_id,
        action_id=action_id,
        approver_name=payload.approver_name or "Commercial Director",
        reason=payload.reason or "Declined during human commercial review."
    )


# ============================================================================
# BACKWARDS-COMPATIBLE CHAT ENDPOINT
# ============================================================================

@router.post("/chat")
def chat_with_copilot_legacy(
    payload: CopilotChatRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Backwards-compatible endpoint for existing test suites and previous frontend callers.
    Executes through the persistent LangGraph supervisor workflow.
    """
    # 1. Get or create active conversation
    conv = db.query(CopilotConversation).filter(
        CopilotConversation.organization_id == org_id,
        CopilotConversation.is_archived == False
    ).order_by(CopilotConversation.updated_at.desc()).first()

    if not conv:
        conv_dict = create_conversation(db=db, org_id=org_id, title="Manufacturing Copilot Session")
        conv_id = conv_dict["id"]
    else:
        conv_id = conv.id

    # 2. Execute via LangGraph
    res = post_message_and_execute(
        db=db,
        org_id=org_id,
        conversation_id=conv_id,
        content=payload.query
    )

    msg = res["message"]
    return {
        "agent_name": msg["agent_name"],
        "intent_detected": res["run"].get("selected_agents", ["Supervisor Agent"])[0] if res["run"].get("selected_agents") else "SUPERVISOR",
        "response_text": msg["content"],
        "data": msg.get("structured_data"),
        "requires_human_approval": msg["requires_human_approval"],
        "pending_action": msg.get("pending_action"),
        "run_id": msg.get("run_id"),
        "conversation_id": conv_id,
        "step_trace": res.get("step_trace", [])
    }
