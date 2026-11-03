"""
IndusPilot Copilot Persistent Conversation & Multi-Agent Execution Service
Manages conversation lifecycles, message persistence, LangGraph workflow execution,
audit tracing, and human-in-the-loop commercial approval gates.
"""

from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.entities import (
    CopilotConversation, CopilotMessage, AgentRun, AgentRunStep,
    AgentToolCall, PendingAgentAction, WorkflowCheckpoint
)
from app.agents.langgraph_supervisor import IndusPilotSupervisorGraph, CopilotWorkflowState


# ============================================================================
# CONVERSATION CRUD & THREADING
# ============================================================================

def list_conversations(
    db: Session,
    org_id: str,
    user_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Lists persistent conversations for an organization."""
    query = db.query(CopilotConversation).filter(
        CopilotConversation.organization_id == org_id,
        CopilotConversation.is_archived == False
    )
    if user_id:
        query = query.filter(CopilotConversation.user_id == user_id)

    convs = query.order_by(CopilotConversation.updated_at.desc()).limit(limit).all()
    results = []
    for c in convs:
        last_msg = db.query(CopilotMessage).filter(CopilotMessage.conversation_id == c.id).order_by(CopilotMessage.created_at.desc()).first()
        results.append({
            "id": c.id,
            "title": c.title,
            "summary": c.summary,
            "last_message": last_msg.content[:100] if last_msg else "No messages yet",
            "message_count": len(c.messages),
            "updated_at": c.updated_at.isoformat() if c.updated_at else c.created_at.isoformat()
        })
    return results


def get_conversation_details(
    db: Session,
    org_id: str,
    conversation_id: str
) -> Dict[str, Any]:
    """Retrieves full conversation with chronological messages and cards."""
    any_conv = db.query(CopilotConversation).filter(
        CopilotConversation.id == conversation_id
    ).first()
    if any_conv and any_conv.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access forbidden: Conversation belongs to another organization.")
    if not any_conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    conv = any_conv

    msgs = []
    for m in conv.messages:
        msgs.append({
            "id": m.id,
            "role": m.role,
            "agent_name": m.agent_name,
            "content": m.content,
            "structured_data": m.structured_data_json,
            "tool_calls": m.tool_calls_json,
            "run_id": m.run_id,
            "requires_human_approval": m.requires_human_approval,
            "pending_action_id": m.pending_action_id,
            "created_at": m.created_at.strftime("%H:%M:%S")
        })

    return {
        "id": conv.id,
        "title": conv.title,
        "summary": conv.summary,
        "context_state": conv.context_state_json or {},
        "created_at": conv.created_at.isoformat(),
        "messages": msgs
    }


def create_conversation(
    db: Session,
    org_id: str,
    title: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Creates a new persistent conversation thread."""
    conv = CopilotConversation(
        organization_id=org_id,
        user_id=user_id,
        title=title or "Manufacturing Discussion",
        context_state_json={}
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    # Initial system greeting
    initial_msg = CopilotMessage(
        conversation_id=conv.id,
        organization_id=org_id,
        role="assistant",
        agent_name="Supervisor Agent",
        content=(
            "Hello! I am IndusPilot, your AI Manufacturing & Procurement Copilot. "
            "You can ask me questions in English, Hindi, or Hinglish! I connect directly to our deterministic "
            "costing engine, Google OR-Tools optimizer, and BOM database. How can I assist your plant today?"
        )
    )
    db.add(initial_msg)
    db.commit()

    return {
        "id": conv.id,
        "title": conv.title,
        "is_archived": conv.is_archived,
        "created_at": conv.created_at.isoformat(),
        "messages": [{
            "id": initial_msg.id,
            "role": initial_msg.role,
            "agent_name": initial_msg.agent_name,
            "content": initial_msg.content,
            "created_at": initial_msg.created_at.strftime("%H:%M:%S")
        }]
    }


def update_conversation(
    db: Session,
    org_id: str,
    conversation_id: str,
    title: Optional[str] = None,
    is_archived: Optional[bool] = None
) -> Dict[str, Any]:
    """Updates title or archive status."""
    conv = db.query(CopilotConversation).filter(
        CopilotConversation.id == conversation_id,
        CopilotConversation.organization_id == org_id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    if title is not None:
        conv.title = title
    if is_archived is not None:
        conv.is_archived = is_archived
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conv)
    return {"id": conv.id, "title": conv.title, "is_archived": conv.is_archived}


def delete_conversation(
    db: Session,
    org_id: str,
    conversation_id: str
) -> Dict[str, bool]:
    """Permanently deletes a conversation and cascade deletes its messages and runs."""
    any_conv = db.query(CopilotConversation).filter(
        CopilotConversation.id == conversation_id
    ).first()
    if any_conv and any_conv.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access forbidden: Conversation belongs to another organization.")
    if not any_conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    db.delete(any_conv)
    db.commit()
    return {"success": True}


# ============================================================================
# LANGGRAPH WORKFLOW EXECUTION & CHAT ORCHESTRATION
# ============================================================================

def post_message_and_execute(
    db: Session,
    org_id: str,
    conversation_id: str,
    content: str,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Primary LangGraph orchestration entry point:
    1. Verifies conversation multi-tenant access.
    2. Persists user message.
    3. Initializes AgentRun with unique run_id.
    4. Executes IndusPilotSupervisorGraph across specialized agents.
    5. Persists assistant reply, structured response card, and execution steps.
    6. Updates conversational context memory for subsequent turns.
    """
    any_conv = db.query(CopilotConversation).filter(
        CopilotConversation.id == conversation_id
    ).first()
    if any_conv and any_conv.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access forbidden: Conversation belongs to another organization.")
    if not any_conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    conv = any_conv

    # 1. Persist User Message
    user_msg = CopilotMessage(
        conversation_id=conv.id,
        organization_id=org_id,
        role="user",
        content=content
    )
    db.add(user_msg)
    conv.updated_at = datetime.utcnow()
    db.commit()

    # 2. Instantiate AgentRun
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    agent_run = AgentRun(
        id=run_id,
        organization_id=org_id,
        conversation_id=conv.id,
        user_id=user_id,
        objective=content,
        status="STARTED"
    )
    db.add(agent_run)
    db.commit()

    # 3. Context Memory: retrieve existing conversation context
    ctx = conv.context_state_json or {}

    # 4. Construct Initial State
    initial_state: CopilotWorkflowState = {
        "conversation_id": conv.id,
        "run_id": run_id,
        "org_id": org_id,
        "user_id": user_id,
        "query": content,
        "intent": "UNKNOWN",
        "language": "en",
        "selected_agents": [],
        "active_agent": "Supervisor Agent",
        "parameters": {},
        "context_data": ctx,
        "step_trace": [],
        "tool_results": {},
        "requires_approval": False,
        "pending_action": None,
        "final_response": None,
        "structured_card": None,
        "status": "EXECUTING",
        "error_message": None
    }

    # 5. Run LangGraph Workflow
    supervisor_graph = IndusPilotSupervisorGraph(db=db)
    final_state = supervisor_graph.run(initial_state)

    # 6. Update Conversation Context Memory
    # Persist extracted product, quantity, material so follow-ups ("What if I increase to 800 kg?") work!
    params = final_state.get("parameters", {})
    if params.get("product_code"):
        ctx["product_code"] = params["product_code"]
    if params.get("material_grade"):
        ctx["material_grade"] = params["material_grade"]
    if params.get("production_quantity"):
        ctx["quantity"] = params["production_quantity"]
    conv.context_state_json = ctx

    # Auto-generate conversational title if first turn
    if len(conv.messages) <= 2 and conv.title == "New Manufacturing Discussion":
        first_words = " ".join(content.split()[:5])
        conv.title = f"{first_words}..." if len(content.split()) > 5 else first_words

    # 7. Persist Assistant Message
    assistant_msg = CopilotMessage(
        conversation_id=conv.id,
        organization_id=org_id,
        role="assistant",
        agent_name=final_state.get("active_agent") or "Supervisor Agent",
        content=final_state.get("final_response") or "Workflow executed successfully.",
        structured_data_json=final_state.get("structured_card"),
        tool_calls_json=final_state.get("tool_results"),
        run_id=run_id,
        requires_human_approval=final_state.get("requires_approval", False),
        pending_action_id=final_state.get("pending_action", {}).get("id") if final_state.get("pending_action") else None
    )
    db.add(assistant_msg)

    # 8. Update AgentRun record
    agent_run.status = final_state.get("status", "COMPLETED")
    agent_run.selected_agents_json = final_state.get("selected_agents", [])
    agent_run.workflow_state_json = {
        "intent": final_state.get("intent"),
        "parameters": final_state.get("parameters"),
        "requires_approval": final_state.get("requires_approval")
    }
    agent_run.completed_at = datetime.utcnow()
    db.commit()

    return {
        "message": {
            "id": assistant_msg.id,
            "role": assistant_msg.role,
            "agent_name": assistant_msg.agent_name,
            "content": assistant_msg.content,
            "structured_data": assistant_msg.structured_data_json,
            "requires_human_approval": assistant_msg.requires_human_approval,
            "pending_action": final_state.get("pending_action"),
            "run_id": run_id,
            "created_at": assistant_msg.created_at.strftime("%H:%M:%S")
        },
        "run": {
            "id": agent_run.id,
            "status": agent_run.status,
            "selected_agents": agent_run.selected_agents_json
        },
        "step_trace": final_state.get("step_trace", [])
    }


# ============================================================================
# AGENT RUN TELEMETRY & APPROVAL ACTIONS
# ============================================================================

def get_run_details(db: Session, org_id: str, run_id: str) -> Dict[str, Any]:
    """Retrieves full agent run trace, steps, and tool calls."""
    run = db.query(AgentRun).filter(AgentRun.id == run_id, AgentRun.organization_id == org_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found.")

    steps = [
        {
            "step_number": s.step_number,
            "agent_name": s.agent_name,
            "step_type": s.step_type,
            "description": s.description,
            "status": s.status,
            "timestamp": s.timestamp.strftime("%H:%M:%S")
        }
        for s in run.steps
    ]

    tool_calls = [
        {
            "tool_name": tc.tool_name,
            "agent_name": tc.agent_name,
            "permission_tier": tc.permission_tier,
            "status": tc.status,
            "duration_ms": tc.execution_duration_ms,
            "created_at": tc.created_at.strftime("%H:%M:%S")
        }
        for tc in run.tool_calls
    ]

    return {
        "id": run.id,
        "objective": run.objective,
        "status": run.status,
        "selected_agents": run.selected_agents_json,
        "steps": steps,
        "tool_calls": tool_calls,
        "pending_actions_count": len(run.pending_actions)
    }


def get_run_events(db: Session, org_id: str, run_id: str) -> List[Dict[str, Any]]:
    """Returns chronological event stream for a run."""
    run = db.query(AgentRun).filter(AgentRun.id == run_id, AgentRun.organization_id == org_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found.")

    return [
        {
            "step_number": s.step_number,
            "agent": s.agent_name,
            "agent_name": s.agent_name,
            "event_type": s.step_type,
            "step_type": s.step_type,
            "description": s.description,
            "status": s.status,
            "time": s.timestamp.strftime("%H:%M:%S")
        }
        for s in run.steps
    ]


def list_pending_actions(
    db: Session,
    org_id: str,
    status: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves pending or historical agent actions."""
    query = db.query(PendingAgentAction).filter(PendingAgentAction.organization_id == org_id)
    if status:
        query = query.filter(PendingAgentAction.status == status)
    if conversation_id:
        query = query.filter(PendingAgentAction.conversation_id == conversation_id)

    actions = query.order_by(PendingAgentAction.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "action_id": a.id,
            "conversation_id": a.conversation_id,
            "run_id": a.run_id,
            "action_type": a.action_type,
            "title": a.title,
            "description": a.description,
            "status": a.status,
            "payload": a.proposed_payload_json,
            "financial_impact": a.financial_impact_summary,
            "reviewed_by": a.decision_by,
            "decision_by": a.decision_by,
            "decision_reason": a.decision_reason,
            "decided_at": a.decided_at.isoformat() if a.decided_at else None,
            "created_at": a.created_at.strftime("%H:%M:%S") if a.created_at else None
        }
        for a in actions
    ]


def approve_pending_action(
    db: Session,
    org_id: str,
    action_id: str,
    approver_name: str = "Commercial Director",
    decision_reason: Optional[str] = None
) -> Dict[str, Any]:
    """Authorizes a paused commercial action and marks it approved."""
    any_action = db.query(PendingAgentAction).filter(
        PendingAgentAction.id == action_id
    ).first()
    if any_action and any_action.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-tenant action forbidden: Action belongs to another organization.")
    if not any_action:
        raise HTTPException(status_code=404, detail="Pending action not found.")
    action = any_action
    if action.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Action already decided ({action.status}).")

    action.status = "APPROVED"
    action.decision_by = approver_name
    action.decision_reason = decision_reason or "Authorized by executive command."
    action.decided_at = datetime.utcnow()

    # Update associated run
    run = action.run
    if run:
        run.status = "COMPLETED"

    # Synchronize underlying entity state
    if action.action_type == "DISPATCH_CUSTOMER_QUOTE" and action.proposed_payload_json:
        quote_id = action.proposed_payload_json.get("quotation_id") or action.proposed_payload_json.get("quote_id")
        if quote_id:
            from app.models.entities import CustomerQuotation
            quote = db.query(CustomerQuotation).filter_by(id=quote_id).first()
            if quote:
                quote.status = "APPROVED"
                quote.approval_status = "APPROVED"
                quote.approved_by = approver_name
                quote.approved_at = datetime.utcnow()

    db.commit()

    return {
        "id": action.id,
        "action_id": action.id,
        "status": action.status,
        "decision_by": action.decision_by,
        "reviewed_by": action.decision_by,
        "decision_reason": action.decision_reason,
        "execution_result": {"status": "SUCCESS", "message": f"Action '{action.title}' successfully authorized."},
        "message": f"Action '{action.title}' successfully authorized."
    }


def reject_pending_action(
    db: Session,
    org_id: str,
    action_id: str,
    approver_name: str = "Commercial Director",
    reason: str = "Rejected by executive review."
) -> Dict[str, Any]:
    """Rejects a paused commercial action."""
    any_action = db.query(PendingAgentAction).filter(
        PendingAgentAction.id == action_id
    ).first()
    if any_action and any_action.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-tenant action forbidden: Action belongs to another organization.")
    if not any_action:
        raise HTTPException(status_code=404, detail="Pending action not found.")
    action = any_action

    action.status = "REJECTED"
    action.decision_by = approver_name
    action.decision_reason = reason
    action.decided_at = datetime.utcnow()

    run = action.run
    if run:
        run.status = "CANCELLED"

    # Synchronize underlying entity state
    if action.action_type == "DISPATCH_CUSTOMER_QUOTE" and action.proposed_payload_json:
        quote_id = action.proposed_payload_json.get("quotation_id") or action.proposed_payload_json.get("quote_id")
        if quote_id:
            from app.models.entities import CustomerQuotation
            quote = db.query(CustomerQuotation).filter_by(id=quote_id).first()
            if quote:
                quote.approval_status = "REJECTED"
                quote.rejection_reason = reason

    db.commit()
    return {
        "id": action.id,
        "action_id": action.id,
        "status": action.status,
        "decision_by": action.decision_by,
        "reviewed_by": action.decision_by,
        "rejection_reason": action.decision_reason,
        "message": f"Action rejected: {reason}"
    }

