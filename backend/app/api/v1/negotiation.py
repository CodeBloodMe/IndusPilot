import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_db, get_current_org_id
from app.models.entities import (
    NegotiationSession, NegotiationMessage, Supplier, SupplierQuotation,
    QuotationItem, Material, ApprovalRequest
)
from app.schemas.domain import (
    NegotiationStartRequest, NegotiationProposalRequest, NegotiationCounterRequest,
    NegotiationTransitionRequest, NegotiationSimulateRequest,
    NegotiationAnalyzeResponseRequest, NegotiationApprovalRequest
)
from app.services.negotiation_service import (
    NegotiationState, NegotiationStrategy,
    generate_negotiation_message_text,
    analyze_negotiation_opportunity,
    analyze_supplier_response,
    simulate_supplier_response,
    apply_negotiated_quotation_revision,
    MockCommunicationProvider
)

router = APIRouter()


class NegotiationSessionCreateRequest(BaseModel):
    quotation_id: str
    strategy: Optional[str] = "BALANCED_COMMERCIAL"
    target_price: Optional[float] = None
    max_acceptable_price: Optional[float] = None
    supplier_id: Optional[str] = None
    material_id: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = "kg"
    payment_terms: Optional[str] = None
    delivery_deadline_days: Optional[int] = None
    language: Optional[str] = "en"


class NegotiationGenerateMessageRequest(BaseModel):
    strategy: Optional[str] = None
    language: Optional[str] = "en"
    custom_notes: Optional[str] = None


class NegotiationFinalizeRequest(BaseModel):
    agreed_price: float
    agreed_lead_time_days: Optional[int] = 14
    agreed_payment_terms: Optional[str] = "Net 30"
    agreed_freight: Optional[float] = 0.0
    accepted_by: Optional[str] = "Procurement Director"


@router.get("/opportunities/{quotation_id}")
def get_negotiation_opportunity(
    quotation_id: str,
    target_discount_pct: Optional[float] = None,
    strategy: str = "BALANCED_COMMERCIAL",
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Calculates data-driven negotiation benchmark targets and savings potential."""
    try:
        opp = analyze_negotiation_opportunity(
            db=db,
            org_id=org_id,
            quotation_id=quotation_id,
            desired_strategy=strategy,
            target_discount_pct=target_discount_pct
        )
        return opp
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions")
def create_negotiation_session(
    payload: NegotiationSessionCreateRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Initializes a structured negotiation session entity."""
    quote = db.query(SupplierQuotation).filter(
        SupplierQuotation.id == payload.quotation_id,
        SupplierQuotation.organization_id == org_id
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quotation not found.")

    q_item = quote.items[0] if quote.items else None
    sup = quote.supplier
    mat = q_item.material if q_item and q_item.material else None

    raw_price = float(q_item.unit_price) if q_item else float(quote.subtotal)
    target_p = payload.target_price or round(raw_price * 0.95, 2)
    max_p = payload.max_acceptable_price or round(raw_price * 0.98, 2)
    qty = payload.quantity or (float(q_item.quantity) if q_item else 100.0)

    opp = analyze_negotiation_opportunity(
        db=db,
        org_id=org_id,
        quotation_id=quote.id,
        desired_strategy=payload.strategy or "BALANCED_COMMERCIAL",
        user_target_price=target_p,
        max_acceptable_price=max_p
    )

    session_count = db.query(NegotiationSession).filter(NegotiationSession.organization_id == org_id).count() + 1
    session_number = f"NEG-2026-{session_count:04d}"

    session = NegotiationSession(
        organization_id=org_id,
        session_number=session_number,
        supplier_id=sup.id if sup else quote.supplier_id,
        quotation_id=quote.id,
        material_id=mat.id if mat else (q_item.material_id if q_item else None),
        material_name=mat.name if mat else (q_item.material_name_raw if q_item else "Material"),
        material_specs=q_item.grade if q_item else "Standard",
        strategy=payload.strategy or "BALANCED_COMMERCIAL",
        quantity=qty,
        original_unit_price=raw_price,
        target_unit_price=target_p,
        max_acceptable_price=max_p,
        current_offered_price=raw_price,
        original_landed_cost=opp["original_total_landed_cost"],
        current_landed_cost=opp["original_total_landed_cost"],
        delivery_deadline_days=payload.delivery_deadline_days or 14,
        payment_terms=payload.payment_terms or "Net 30",
        status=NegotiationState.DRAFT,
        approval_status="DRAFT",
        simulation_mode=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "id": session.id,
        "session_number": session.session_number,
        "state": session.status,
        "status": session.status,
        "original_unit_price": session.original_unit_price,
        "target_unit_price": session.target_unit_price,
        "supplier_name": sup.name if sup else "Supplier"
    }


@router.post("/sessions/{session_id}/generate-message")
def generate_message_for_session(
    session_id: str,
    payload: NegotiationGenerateMessageRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Generates multilingual negotiation message text for session."""
    session = db.query(NegotiationSession).filter(
        NegotiationSession.id == session_id,
        NegotiationSession.organization_id == org_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Negotiation session not found.")

    opp = analyze_negotiation_opportunity(
        db=db,
        org_id=org_id,
        quotation_id=session.quotation_id,
        desired_strategy=payload.strategy or session.strategy,
        user_target_price=session.target_unit_price,
        max_acceptable_price=session.max_acceptable_price
    )

    msg_dict = generate_negotiation_message_text(
        strategy=payload.strategy or session.strategy,
        analysis=opp,
        language=payload.language or "en",
        notes=payload.custom_notes
    )

    current_round = len(session.messages) + 1
    msg = NegotiationMessage(
        session_id=session.id,
        round_number=current_round,
        sender_type="BUYER_AGENT",
        language=payload.language or "en",
        subject=msg_dict["subject"],
        message_text=msg_dict["body"],
        proposed_unit_price=session.target_unit_price,
        is_simulated=True
    )
    db.add(msg)
    session.status = NegotiationState.MESSAGE_GENERATED
    db.commit()
    db.refresh(msg)

    return {
        "id": msg.id,
        "session_id": session.id,
        "round_number": msg.round_number,
        "subject": msg.subject,
        "body": msg.message_text,
        "message_text": msg.message_text,
        "language": msg.language
    }


@router.post("/messages/{message_id}/approve")
def approve_message_dispatch(
    message_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Human approval gate for negotiation message dispatch."""
    msg = db.query(NegotiationMessage).filter(NegotiationMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found.")

    msg.session.status = NegotiationState.SENT
    msg.session.approval_status = "APPROVED"
    msg.session.approved_by = "Commercial Director"
    msg.session.approved_at = datetime.utcnow()
    db.commit()

    return {
        "message_id": msg.id,
        "session_id": msg.session_id,
        "human_approved": True,
        "status": "APPROVED",
        "session_state": msg.session.status
    }


@router.post("/sessions/{session_id}/finalize-agreement")
def finalize_negotiation_agreement(
    session_id: str,
    payload: NegotiationFinalizeRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Finalizes agreement, creates revised quotation without mutating original, and closes session."""
    session = db.query(NegotiationSession).filter(
        NegotiationSession.id == session_id,
        NegotiationSession.organization_id == org_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Negotiation session not found.")

    res = apply_negotiated_quotation_revision(
        db=db,
        org_id=org_id,
        session_id=session.id,
        accepted_by=payload.accepted_by or "Procurement Director",
        agreed_unit_price=payload.agreed_price,
        agreed_lead_time_days=payload.agreed_lead_time_days,
        agreed_payment_terms=payload.agreed_payment_terms,
        agreed_freight=payload.agreed_freight
    )

    return {
        "status": "ACCEPTED",
        "state": "ACCEPTED",
        "session_id": session.id,
        "final_agreed_price": payload.agreed_price,
        "revised_quotation_id": res["revised_quotation_id"] if isinstance(res, dict) else res.id,
        "net_savings_abs": res.get("net_savings_abs") if isinstance(res, dict) else 0.0
    }


@router.get("/sessions")
def list_negotiation_sessions(
    supplier_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Lists all active and historical supplier negotiation sessions."""
    query = db.query(NegotiationSession).filter(NegotiationSession.organization_id == org_id)
    if supplier_id:
        query = query.filter(NegotiationSession.supplier_id == supplier_id)
    if status:
        query = query.filter(NegotiationSession.status == status)

    sessions = query.order_by(NegotiationSession.updated_at.desc()).all()
    results = []
    for s in sessions:
        results.append({
            "id": s.id,
            "session_number": s.session_number or f"NEG-{s.id[:8].upper()}",
            "supplier_id": s.supplier_id,
            "supplier_name": s.supplier.name if s.supplier else "Unknown",
            "quotation_id": s.quotation_id,
            "quotation_number": s.quotation.quotation_number if s.quotation else None,
            "material_id": s.material_id,
            "material_name": s.material_name,
            "material_specs": s.material_specs,
            "strategy": s.strategy,
            "quantity": s.quantity,
            "original_unit_price": s.original_unit_price,
            "target_unit_price": s.target_unit_price,
            "max_acceptable_price": s.max_acceptable_price,
            "current_offered_price": s.current_offered_price,
            "original_landed_cost": s.original_landed_cost,
            "current_landed_cost": s.current_landed_cost,
            "final_agreed_price": s.final_agreed_price,
            "final_landed_cost": s.final_landed_cost,
            "net_savings_abs": s.net_savings_abs,
            "net_savings_pct": s.net_savings_pct,
            "status": s.status,
            "approval_status": s.approval_status,
            "approved_by": s.approved_by,
            "approved_at": s.approved_at.isoformat() if s.approved_at else None,
            "simulation_mode": s.simulation_mode,
            "rounds_count": len(s.messages),
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "messages": [
                {
                    "id": m.id,
                    "round_number": m.round_number,
                    "sender_type": m.sender_type,
                    "language": m.language,
                    "subject": m.subject,
                    "message_text": m.message_text,
                    "proposed_unit_price": m.proposed_unit_price,
                    "classification": m.classification,
                    "is_simulated": m.is_simulated,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in s.messages
            ]
        })
    return results


@router.get("/sessions/{session_id}")
def get_negotiation_session_details(
    session_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves full commercial negotiation details including audit messages and impact."""
    session = db.query(NegotiationSession).filter(
        NegotiationSession.id == session_id,
        NegotiationSession.organization_id == org_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Negotiation session not found.")

    return {
        "id": session.id,
        "session_number": session.session_number,
        "supplier_id": session.supplier_id,
        "supplier_name": session.supplier.name if session.supplier else "Unknown",
        "quotation_id": session.quotation_id,
        "quotation_number": session.quotation.quotation_number if session.quotation else None,
        "material_id": session.material_id,
        "material_name": session.material_name,
        "material_specs": session.material_specs,
        "strategy": session.strategy,
        "quantity": session.quantity,
        "original_unit_price": session.original_unit_price,
        "target_unit_price": session.target_unit_price,
        "max_acceptable_price": session.max_acceptable_price,
        "current_offered_price": session.current_offered_price,
        "original_landed_cost": session.original_landed_cost,
        "current_landed_cost": session.current_landed_cost,
        "final_agreed_price": session.final_agreed_price,
        "final_landed_cost": session.final_landed_cost,
        "net_savings_abs": session.net_savings_abs,
        "net_savings_pct": session.net_savings_pct,
        "delivery_deadline_days": session.delivery_deadline_days,
        "payment_terms": session.payment_terms,
        "status": session.status,
        "approval_status": session.approval_status,
        "approved_by": session.approved_by,
        "approved_at": session.approved_at.isoformat() if session.approved_at else None,
        "commercial_impact": session.commercial_impact_json,
        "simulation_mode": session.simulation_mode,
        "messages": [
            {
                "id": m.id,
                "round_number": m.round_number,
                "sender_type": m.sender_type,
                "language": m.language,
                "subject": m.subject,
                "message_text": m.message_text,
                "proposed_unit_price": m.proposed_unit_price,
                "classification": m.classification,
                "extracted_terms": m.extracted_terms_json,
                "is_simulated": m.is_simulated,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in session.messages
        ]
    }


@router.post("/start")
def start_negotiation_session(
    payload: NegotiationStartRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Initializes a structured negotiation session, evaluates alternative offers,
    generates an opening counteroffer message, and places session in AWAITING_APPROVAL.
    """
    sup = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    # Guardrail: target price must not be below 50% of original price (prevents absurd numbers)
    if payload.target_unit_price < (payload.original_unit_price * 0.50):
        raise HTTPException(status_code=400, detail="Target price cannot be lower than 50% of the original quoted price.")

    # Guardrail: target price must not be higher than original price
    if payload.target_unit_price >= payload.original_unit_price:
        raise HTTPException(status_code=400, detail="Target price must be strictly less than original price to initiate negotiation.")

    # Opportunity analysis
    opp = analyze_negotiation_opportunity(
        db=db,
        org_id=org_id,
        quotation_id=payload.quotation_id or "",
        material_id=payload.material_id,
        desired_strategy=payload.strategy,
        user_target_price=payload.target_unit_price,
        max_acceptable_price=payload.max_acceptable_price
    ) if payload.quotation_id else {
        "original_total_landed_cost": payload.original_unit_price * payload.quantity * 1.18,
        "original_unit_landed_cost": payload.original_unit_price * 1.18,
        "competitor_benchmark": None,
        "material_specs": payload.material_specs or "Industrial Grade"
    }

    comp = opp.get("competitor_benchmark")

    # Generate sequential session number
    session_count = db.query(NegotiationSession).filter(NegotiationSession.organization_id == org_id).count() + 1
    session_number = f"NEG-2026-{session_count:04d}"

    # Generate opening counteroffer email
    msg_dict = generate_negotiation_message_text(
        supplier_name=sup.name,
        material_name=payload.material_name,
        quantity=payload.quantity,
        unit=payload.unit,
        current_offered_price=payload.original_unit_price,
        target_price=payload.target_unit_price,
        strategy=payload.strategy,
        competitor_price=comp["unit_price"] if comp else None,
        competitor_supplier=comp["supplier_name"] if comp else None,
        improved_payment_terms=payload.payment_terms,
        delivery_deadline_days=payload.delivery_deadline_days,
        language=payload.language
    )

    session = NegotiationSession(
        organization_id=org_id,
        session_number=session_number,
        supplier_id=sup.id,
        quotation_id=payload.quotation_id,
        material_id=payload.material_id,
        material_name=payload.material_name,
        material_specs=opp.get("material_specs") or payload.material_specs,
        strategy=payload.strategy,
        quantity=payload.quantity,
        original_unit_price=payload.original_unit_price,
        target_unit_price=payload.target_unit_price,
        max_acceptable_price=payload.max_acceptable_price or (payload.original_unit_price * 0.98),
        current_offered_price=payload.original_unit_price,
        original_landed_cost=opp["original_total_landed_cost"],
        current_landed_cost=opp["original_total_landed_cost"],
        delivery_deadline_days=payload.delivery_deadline_days,
        payment_terms=payload.payment_terms,
        competitor_quote_id=comp["quotation_id"] if comp else None,
        status=NegotiationState.AWAITING_APPROVAL,
        approval_status="PENDING_APPROVAL",
        simulation_mode=True
    )
    db.add(session)
    db.flush()

    # Create message record
    msg = NegotiationMessage(
        session_id=session.id,
        round_number=1,
        sender_type="BUYER_AGENT",
        language=payload.language,
        subject=msg_dict["subject"],
        message_text=msg_dict["body"],
        proposed_unit_price=payload.target_unit_price,
        payment_terms=payload.payment_terms,
        delivery_days=payload.delivery_deadline_days,
        is_simulated=True
    )
    db.add(msg)

    # Formal Approval Request
    appr = ApprovalRequest(
        organization_id=org_id,
        request_type="NEGOTIATION_DISPATCH",
        entity_id=session.id,
        requested_by="Autonomous Negotiation Agent",
        details_json={
            "session_number": session_number,
            "supplier_name": sup.name,
            "material": payload.material_name,
            "quantity": payload.quantity,
            "unit": payload.unit,
            "opening_rate": payload.original_unit_price,
            "target_rate": payload.target_unit_price,
            "projected_savings_inr": round((payload.original_unit_price - payload.target_unit_price) * payload.quantity, 2),
            "strategy": payload.strategy,
            "language": payload.language
        },
        status="PENDING"
    )
    db.add(appr)

    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "session_number": session.session_number,
        "status": session.status,
        "approval_status": session.approval_status,
        "supplier_name": sup.name,
        "target_price": payload.target_unit_price,
        "original_total_landed_cost": session.original_landed_cost,
        "generated_message": msg_dict
    }


@router.post("/sessions/{session_id}/generate-proposal")
def generate_proposal_message(
    session_id: str,
    payload: NegotiationProposalRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Generates an edited counteroffer proposal message in specified language without dispatching."""
    session = db.query(NegotiationSession).filter(
        NegotiationSession.id == session_id,
        NegotiationSession.organization_id == org_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Negotiation session not found.")

    target_price = payload.target_unit_price or session.target_unit_price
    strategy = payload.strategy or session.strategy
    language = payload.language or "en"
    terms = payload.payment_terms or session.payment_terms or "15 Days Prompt Payment"

    if payload.custom_message_text:
        return {
            "session_id": session.id,
            "subject": f"Commercial Negotiation — {session.material_name}",
            "body": payload.custom_message_text,
            "language": language
        }

    msg_dict = generate_negotiation_message_text(
        supplier_name=session.supplier.name if session.supplier else "Vendor",
        material_name=session.material_name,
        quantity=session.quantity,
        unit="kg",
        current_offered_price=session.current_offered_price,
        target_price=target_price,
        strategy=strategy,
        improved_payment_terms=terms,
        delivery_deadline_days=session.delivery_deadline_days,
        language=language
    )
    return {
        "session_id": session.id,
        "subject": msg_dict["subject"],
        "body": msg_dict["body"],
        "language": language
    }


@router.post("/sessions/{session_id}/approve-message")
def approve_negotiation_message(
    session_id: str,
    payload: NegotiationApprovalRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Managerial approval gate: authorizes outbound counteroffer communication.
    Transitions status from AWAITING_APPROVAL to APPROVED_TO_SEND / SENT.
    """
    session = db.query(NegotiationSession).filter(
        NegotiationSession.id == session_id,
        NegotiationSession.organization_id == org_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Negotiation session not found.")

    if payload.action == "APPROVE":
        session.approval_status = "APPROVED"
        session.approved_by = payload.approver_name
        session.approved_at = datetime.utcnow()
        session.status = NegotiationState.SENT

        # Close pending approval request
        appr = db.query(ApprovalRequest).filter(
            ApprovalRequest.entity_id == session.id,
            ApprovalRequest.request_type == "NEGOTIATION_DISPATCH",
            ApprovalRequest.status == "PENDING"
        ).first()
        if appr:
            appr.status = "APPROVED"
            appr.decided_by = payload.approver_name
            appr.decided_at = datetime.utcnow()

        db.commit()
        return {
            "session_id": session.id,
            "status": session.status,
            "approval_status": session.approval_status,
            "message": "Counteroffer approved and authorized for vendor transmission."
        }
    else:
        session.approval_status = "REJECTED"
        session.rejection_reason = payload.notes or "Counteroffer rejected by management."
        session.status = NegotiationState.CANCELLED

        appr = db.query(ApprovalRequest).filter(
            ApprovalRequest.entity_id == session.id,
            ApprovalRequest.request_type == "NEGOTIATION_DISPATCH",
            ApprovalRequest.status == "PENDING"
        ).first()
        if appr:
            appr.status = "REJECTED"
            appr.decided_by = payload.approver_name
            appr.decided_at = datetime.utcnow()

        db.commit()
        return {
            "session_id": session.id,
            "status": session.status,
            "approval_status": session.approval_status,
            "message": "Counteroffer proposal rejected. Session cancelled."
        }


@router.post("/sessions/{session_id}/simulate-response")
def simulate_response_round(
    session_id: str,
    payload: Optional[NegotiationSimulateRequest] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Simulates receiving a realistic vendor counter-proposal.
    Calculates deterministic landed costs and classifies the response.
    Explicitly tags the output as SIMULATED.
    """
    session = db.query(NegotiationSession).filter(
        NegotiationSession.id == session_id,
        NegotiationSession.organization_id == org_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Negotiation session not found.")

    scenario = payload.scenario if payload else "CONCESSION_PARTIAL"
    sup_name = session.supplier.name if session.supplier else "Vendor"
    current_round = len(session.messages) + 1

    sim_reply = simulate_supplier_response(
        supplier_name=sup_name,
        round_number=current_round,
        original_price=session.original_unit_price,
        current_offered_price=session.current_offered_price,
        buyer_counter_price=session.target_unit_price,
        material_name=session.material_name,
        quantity=session.quantity,
        scenario=scenario
    )

    # Analyze response impact
    analysis = analyze_supplier_response(
        response_text=sim_reply["response_message"],
        original_unit_price=session.original_unit_price,
        original_landed_cost=session.original_landed_cost,
        target_unit_price=session.target_unit_price,
        quantity=session.quantity,
        parsed_price=sim_reply["revised_unit_price"]
    )

    # Persist message
    msg = NegotiationMessage(
        session_id=session.id,
        round_number=current_round,
        sender_type="SUPPLIER",
        message_text=sim_reply["response_message"],
        proposed_unit_price=sim_reply["revised_unit_price"],
        classification=analysis["classification"],
        extracted_terms_json=analysis,
        is_simulated=True
    )
    db.add(msg)

    # Update session metrics
    session.current_offered_price = sim_reply["revised_unit_price"]
    session.current_landed_cost = analysis["revised_total_landed_cost"]
    session.net_savings_abs = analysis["net_savings_abs"]
    session.net_savings_pct = analysis["net_savings_pct"]
    session.status = NegotiationState.RESPONSE_RECEIVED
    session.commercial_impact_json = analysis
    session.updated_at = datetime.utcnow()

    db.commit()

    return {
        "session_id": session.id,
        "status": session.status,
        "round_number": current_round,
        "revised_unit_price": session.current_offered_price,
        "counter_unit_price": session.current_offered_price,
        "current_offered_price": session.current_offered_price,
        "savings_vs_original": session.net_savings_abs,
        "revised_total_landed_cost": session.current_landed_cost,
        "net_savings_abs": session.net_savings_abs,
        "net_savings_pct": session.net_savings_pct,
        "classification": analysis["classification"],
        "action_recommendation": analysis["action_recommendation"],
        "vendor_reply": sim_reply,
        "is_simulated": True
    }


@router.post("/sessions/{session_id}/analyze-response")
def analyze_vendor_message(
    session_id: str,
    payload: NegotiationAnalyzeResponseRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Parses an incoming text message (e.g. from email/WhatsApp), extracts terms,
    and recalculates exact landed costs without using LLMs for math.
    """
    session = db.query(NegotiationSession).filter(
        NegotiationSession.id == session_id,
        NegotiationSession.organization_id == org_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Negotiation session not found.")

    analysis = analyze_supplier_response(
        response_text=payload.response_text,
        original_unit_price=session.original_unit_price,
        original_landed_cost=session.original_landed_cost,
        target_unit_price=session.target_unit_price,
        quantity=session.quantity,
        parsed_price=payload.parsed_price,
        parsed_freight=payload.parsed_freight,
        parsed_delivery_days=payload.parsed_delivery_days
    )

    current_round = len(session.messages) + 1
    msg = NegotiationMessage(
        session_id=session.id,
        round_number=current_round,
        sender_type="SUPPLIER",
        message_text=payload.response_text,
        proposed_unit_price=analysis["revised_unit_price"],
        classification=analysis["classification"],
        extracted_terms_json=analysis,
        is_simulated=False
    )
    db.add(msg)

    session.current_offered_price = analysis["revised_unit_price"]
    session.current_landed_cost = analysis["revised_total_landed_cost"]
    session.net_savings_abs = analysis["net_savings_abs"]
    session.net_savings_pct = analysis["net_savings_pct"]
    session.status = NegotiationState.RESPONSE_ANALYSED
    session.commercial_impact_json = analysis
    session.updated_at = datetime.utcnow()

    db.commit()

    return {
        "session_id": session.id,
        "analysis": analysis
    }


@router.post("/sessions/{session_id}/complete")
def complete_negotiation(
    session_id: str,
    accepted_by: str = "Procurement Lead",
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Finalizes an accepted negotiation: creates an immutable revised SupplierQuotation record
    (preserving original quotation), recalculates landed cost, and closes session.
    """
    try:
        res = apply_negotiated_quotation_revision(
            db=db,
            org_id=org_id,
            session_id=session_id,
            accepted_by=accepted_by
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to finalize negotiation: {str(e)}")


# Backward-compatible endpoint for existing UI calls
@router.post("/send-and-simulate")
def send_and_simulate_legacy(
    session_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Legacy backward-compatible simulation trigger."""
    return simulate_response_round(session_id=session_id, payload=None, db=db, org_id=org_id)
