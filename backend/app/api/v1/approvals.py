from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_org_id
from app.models.entities import ApprovalRequest, NegotiationSession, CustomerQuotation, AuditLog
from app.schemas.domain import ApprovalActionRequest

router = APIRouter()

@router.get("")
def list_approvals(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    query = db.query(ApprovalRequest).filter(ApprovalRequest.organization_id == org_id)
    if status:
        query = query.filter(ApprovalRequest.status == status)
    approvals = query.order_by(ApprovalRequest.created_at.desc()).all()
    results = []
    for a in approvals:
        results.append({
            "id": a.id,
            "request_type": a.request_type,
            "entity_id": a.entity_id,
            "requested_by": a.requested_by,
            "details": a.details_json,
            "status": a.status,
            "decision_reason": a.decision_reason,
            "decided_at": a.decided_at.strftime("%Y-%m-%d %H:%M") if a.decided_at else None,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else None
        })
    return results

@router.post("/{approval_id}/action")
def act_on_approval(
    approval_id: str,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    appr = db.query(ApprovalRequest).filter(
        ApprovalRequest.id == approval_id,
        ApprovalRequest.organization_id == org_id
    ).first()
    if not appr:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    new_status = "APPROVED" if payload.action.upper() == "APPROVE" else "REJECTED"
    appr.status = new_status
    appr.decision_reason = payload.reason or ("Authorized by factory owner." if new_status == "APPROVED" else "Rejected by user.")
    appr.decided_at = datetime.utcnow()

    # Cascade state change to underlying entity
    if appr.request_type == "NEGOTIATION_DISPATCH":
        session = db.query(NegotiationSession).filter(NegotiationSession.id == appr.entity_id).first()
        if session:
            session.status = "APPROVED_TO_SEND" if new_status == "APPROVED" else "REJECTED"

    elif appr.request_type == "CUSTOMER_QUOTE":
        quote = db.query(CustomerQuotation).filter(CustomerQuotation.id == appr.entity_id).first()
        if quote:
            quote.status = "APPROVED" if new_status == "APPROVED" else "REJECTED"

    # Audit logging
    log = AuditLog(
        organization_id=org_id,
        action=f"HUMAN_APPROVAL_{new_status}",
        entity_type=appr.request_type,
        entity_id=appr.entity_id,
        changes_json={"approval_id": appr.id, "new_status": new_status, "reason": appr.decision_reason}
    )
    db.add(log)

    db.commit()
    db.refresh(appr)

    return {
        "approval_id": appr.id,
        "status": appr.status,
        "decision_reason": appr.decision_reason,
        "decided_at": appr.decided_at.isoformat()
    }

