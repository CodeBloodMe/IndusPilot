"""
IndusPilot Phase 9 Human-in-the-Loop Approval Governance Test Suite
Verifies:
1. Actions cannot self-execute without explicit human supervisor authorization.
2. Complete approval lifecycle (Pending -> Approved / Rejected).
3. Rejection finality (rejected actions cannot subsequently be approved).
4. Idempotency (duplicate decisions on decided actions return 400).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.models.entities import PendingAgentAction, AgentRun
from app.database.session import SessionLocal


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_approval_lifecycle_approval_and_idempotency(client):
    """Verify approval transition and duplicate decision rejection."""
    # 1. Start a conversation and trigger an action requiring human approval
    conv_res = client.post("/api/v1/copilot/conversations", json={
        "title": "Phase 9 Approval Governance Verification"
    })
    conv_id = conv_res.json()["id"]

    msg_res = client.post(f"/api/v1/copilot/conversations/{conv_id}/messages", json={
        "content": "Prepare full order workflow for 500 brackets and draft customer quote"
    })
    assert msg_res.status_code == 200
    msg_data = msg_res.json()["message"]
    assert msg_data["requires_human_approval"] is True
    pending_action = msg_data["pending_action"]
    assert pending_action is not None
    action_id = pending_action["id"]

    # 2. Verify action appears in pending actions list
    pending_list = client.get("/api/v1/copilot/actions?status=PENDING")
    assert pending_list.status_code == 200
    pending_ids = [a["id"] for a in pending_list.json()]
    assert action_id in pending_ids

    # 3. Approve action as Plant Head
    approve_res = client.post(f"/api/v1/copilot/actions/{action_id}/approve", json={
        "reason": "Authorized based on 25.1% margin threshold and verified landed cost.",
        "approver_name": "S. Sharma, Plant Head"
    })
    assert approve_res.status_code == 200
    data = approve_res.json()
    assert data["status"] == "APPROVED"
    assert data["decision_by"] == "S. Sharma, Plant Head"

    # 4. Attempt to approve again (idempotent rejection)
    duplicate_res = client.post(f"/api/v1/copilot/actions/{action_id}/approve", json={
        "reason": "Second approval attempt",
        "approver_name": "Another Approver"
    })
    assert duplicate_res.status_code == 400
    assert "already decided" in duplicate_res.json()["detail"].lower()


def test_approval_lifecycle_rejection_finality(client):
    """Verify that rejecting an action prevents execution and subsequent approval."""
    db = SessionLocal()
    try:
        # Create a test pending action directly
        run = AgentRun(
            organization_id=settings.DEFAULT_ORGANIZATION_ID,
            objective="Dispatch customer quotation to client",
            status="PAUSED_FOR_APPROVAL"
        )
        db.add(run)
        db.flush()

        action = PendingAgentAction(
            run_id=run.id,
            organization_id=settings.DEFAULT_ORGANIZATION_ID,
            action_type="DISPATCH_CUSTOMER_QUOTATION",
            agent_name="Customer Quotation Agent",
            title="Dispatch Quotation to Larsen Heavy Machinery",
            description="Official dispatch of negotiated quote",
            proposed_payload_json={"quote_id": "CQ-TEST-001", "email": "client@larsen.com"},
            status="PENDING"
        )
        db.add(action)
        db.commit()
        action_id = action.id
    finally:
        db.close()

    # 1. Reject action
    reject_res = client.post(f"/api/v1/copilot/actions/{action_id}/reject", json={
        "reason": "Customer payment terms 90 days too long. Requires 30 days renegotiation.",
        "approver_name": "V. Nair, Commercial Director"
    })
    assert reject_res.status_code == 200
    reject_data = reject_res.json()
    assert reject_data["status"] == "REJECTED"

    # 2. Attempt to approve rejected action MUST fail
    approve_attempt = client.post(f"/api/v1/copilot/actions/{action_id}/approve", json={
        "reason": "Trying to override rejection",
        "approver_name": "Plant Head"
    })
    assert approve_attempt.status_code == 400
    assert "already decided" in approve_attempt.json()["detail"].lower()
