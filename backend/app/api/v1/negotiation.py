from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_org_id
from app.models.entities import NegotiationSession, NegotiationMessage, Supplier, ApprovalRequest
from app.schemas.domain import NegotiationStartRequest, NegotiationCounterRequest, NegotiationTransitionRequest
from app.services.negotiation_service import (
    NegotiationStateMachine,
    generate_counteroffer_draft,
    simulate_supplier_response
)

router = APIRouter()

@router.get("/sessions")
def list_negotiation_sessions(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    sessions = db.query(NegotiationSession).filter(NegotiationSession.organization_id == org_id).order_by(NegotiationSession.updated_at.desc()).all()
    results = []
    for s in sessions:
        results.append({
            "id": s.id,
            "supplier_id": s.supplier_id,
            "supplier_name": s.supplier.name if s.supplier else "Unknown",
            "material_name": s.material_name,
            "quantity": s.quantity,
            "original_unit_price": s.original_unit_price,
            "target_unit_price": s.target_unit_price,
            "current_offered_price": s.current_offered_price,
            "status": s.status,
            "simulation_mode": s.simulation_mode,
            "rounds_count": len(s.messages),
            "updated_at": s.updated_at.strftime("%Y-%m-%d %H:%M") if s.updated_at else None,
            "messages": [
                {
                    "id": m.id,
                    "round_number": m.round_number,
                    "sender_type": m.sender_type,
                    "message_text": m.message_text,
                    "proposed_unit_price": m.proposed_unit_price,
                    "is_simulated": m.is_simulated,
                    "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else None
                }
                for m in s.messages
            ]
        })
    return results

@router.post("/start")
def start_negotiation_session(
    payload: NegotiationStartRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    sup = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    session = NegotiationSession(
        organization_id=org_id,
        supplier_id=sup.id,
        quotation_id=payload.quotation_id,
        material_name=payload.material_name,
        quantity=payload.quantity,
        original_unit_price=payload.original_unit_price,
        target_unit_price=payload.target_unit_price,
        current_offered_price=payload.original_unit_price,
        status="DRAFT",
        simulation_mode=True
    )
    db.add(session)
    db.flush()

    # Generate initial counteroffer draft
    draft = generate_counteroffer_draft(
        supplier_name=sup.name,
        material_name=payload.material_name,
        quantity=payload.quantity,
        unit="kg",
        current_offered_price=payload.original_unit_price,
        target_price=payload.target_unit_price,
        current_payment_terms=sup.payment_terms_days and f"{sup.payment_terms_days} Days" or "30 Days",
        improved_payment_terms=payload.payment_terms
    )

    msg = NegotiationMessage(
        session_id=session.id,
        round_number=1,
        sender_type="BUYER_AGENT",
        message_text=draft["email_body"],
        proposed_unit_price=payload.target_unit_price,
        payment_terms=payload.payment_terms,
        is_simulated=True
    )
    db.add(msg)

    # Move to READY_FOR_APPROVAL
    session.status = "READY_FOR_APPROVAL"

    # Create pending human approval request
    appr = ApprovalRequest(
        organization_id=org_id,
        request_type="NEGOTIATION_DISPATCH",
        entity_id=session.id,
        requested_by="Negotiation Agent",
        details_json={
            "supplier_name": sup.name,
            "material": payload.material_name,
            "quantity": payload.quantity,
            "opening_rate": payload.original_unit_price,
            "counter_rate": payload.target_unit_price,
            "projected_savings": round((payload.original_unit_price - payload.target_unit_price) * payload.quantity, 2)
        },
        status="PENDING"
    )
    db.add(appr)

    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "status": session.status,
        "supplier_name": sup.name,
        "target_price": payload.target_unit_price,
        "draft": draft
    }

@router.post("/send-and-simulate")
def send_counteroffer_and_simulate_reply(
    session_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Simulates sending the approved counteroffer to the vendor and receiving
    a realistic vendor counter-proposal with concession curve.
    """
    session = db.query(NegotiationSession).filter(
        NegotiationSession.id == session_id,
        NegotiationSession.organization_id == org_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Negotiation session not found.")

    sup_name = session.supplier.name if session.supplier else "Vendor"
    current_round = len(session.messages) + 1

    # Simulate vendor response
    vendor_reply = simulate_supplier_response(
        supplier_name=sup_name,
        round_number=current_round,
        original_price=session.original_unit_price,
        current_offered_price=session.current_offered_price,
        buyer_counter_price=session.target_unit_price,
        material_name=session.material_name,
        quantity=session.quantity
    )

    # Record vendor message
    msg = NegotiationMessage(
        session_id=session.id,
        round_number=current_round,
        sender_type="SUPPLIER",
        message_text=vendor_reply["response_message"],
        proposed_unit_price=vendor_reply["revised_unit_price"],
        is_simulated=True
    )
    db.add(msg)

    # Update session price & status
    session.current_offered_price = vendor_reply["revised_unit_price"]
    session.status = "RESPONSE_RECEIVED"
    session.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "status": session.status,
        "current_offered_price": session.current_offered_price,
        "original_price": session.original_unit_price,
        "savings_vs_original": vendor_reply["savings_vs_original"],
        "vendor_reply": vendor_reply
    }

