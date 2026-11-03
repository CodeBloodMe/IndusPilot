"""
IndusPilot — Customer Quotation & Commercial Decision API
Tech4Bharat 2026 Problem Statement 4.1
"""

import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_db, get_current_org_id
from app.core.config import settings
from app.models.entities import Customer, CustomerQuotation, Product, ApprovalRequest
from app.schemas.domain import (
    CustomerCreateRequest,
    CustomerQuoteGenerateRequest,
    CustomerQuoteResponseRecordRequest
)
from app.services.customer_quotation_service import (
    calculate_quotation_pricing,
    create_customer_quotation_record,
    recalculate_customer_quotation,
    approve_customer_quotation,
    record_customer_response
)
from app.services.pdf_generator import generate_customer_quotation_pdf

router = APIRouter()


class CustomerQuoteRecalculateRequest(BaseModel):
    unit_cost: Optional[float] = None
    quantity: Optional[float] = None
    target_margin_pct: Optional[float] = None
    unit_selling_price: Optional[float] = None
    discount_pct: Optional[float] = None
    tax_pct: Optional[float] = None
    min_margin_pct: Optional[float] = None
    payment_terms: Optional[str] = None
    delivery_weeks: Optional[int] = None


class CustomerQuoteApprovalActionRequest(BaseModel):
    approver_name: Optional[str] = "Commercial Director"
    notes: Optional[str] = None


# --- Customer Directory Endpoints ---

@router.get("/customers")
def list_customers(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Lists registered customer accounts for commercial quotation generation."""
    customers = db.query(Customer).filter(
        Customer.organization_id == org_id,
        Customer.is_active == True
    ).order_by(Customer.company_name.asc()).all()

    return [
        {
            "id": c.id,
            "customer_code": c.customer_code,
            "name": c.name,
            "company_name": c.company_name,
            "email": c.email,
            "phone": c.phone,
            "gst_number": c.gst_number,
            "credit_limit": c.credit_limit,
            "payment_terms": c.payment_terms
        }
        for c in customers
    ]


@router.post("/customers")
def create_customer(
    payload: CustomerCreateRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Registers a new industrial customer."""
    code = payload.customer_code
    if not code:
        count = db.query(Customer).filter(Customer.organization_id == org_id).count() + 1
        code = f"CUST-{count:03d}"

    customer = Customer(
        organization_id=org_id,
        customer_code=code,
        name=payload.name,
        company_name=payload.company_name or payload.name,
        email=payload.email,
        phone=payload.phone,
        billing_address=payload.billing_address,
        shipping_address=payload.shipping_address,
        gst_number=payload.gst_number,
        credit_limit=payload.credit_limit,
        payment_terms=payload.payment_terms,
        is_active=True
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    return {
        "id": customer.id,
        "customer_code": customer.customer_code,
        "name": customer.name,
        "company_name": customer.company_name,
        "email": customer.email,
        "credit_limit": customer.credit_limit
    }


# --- Customer Quotation CRUD & Actions ---

@router.get("")
def list_customer_quotations(
    status: Optional[str] = Query(None),
    is_loss_making: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Lists historical and active customer quotations with profitability status."""
    query = db.query(CustomerQuotation).filter(CustomerQuotation.organization_id == org_id)
    if status:
        query = query.filter(CustomerQuotation.status == status)
    if is_loss_making is not None:
        query = query.filter(CustomerQuotation.is_loss_making == is_loss_making)

    quotes = query.order_by(CustomerQuotation.created_at.desc()).all()
    results = []
    for q in quotes:
        results.append({
            "id": q.id,
            "quote_number": q.quote_number,
            "customer_id": q.customer_id,
            "customer_name": q.customer_name,
            "customer_company": q.customer_company,
            "product_id": q.product_id,
            "quantity": q.quantity,
            "unit_production_cost": q.unit_production_cost,
            "unit_selling_price": q.unit_selling_price,
            "markup_pct": q.markup_pct or 0.0,
            "margin_pct": q.margin_pct,
            "min_margin_pct": q.min_margin_pct or 15.0,
            "gross_profit": q.gross_profit or 0.0,
            "subtotal": q.subtotal,
            "discount_pct": q.discount_pct or 0.0,
            "discount_amount": q.discount_amount or 0.0,
            "tax_pct": q.tax_pct or 18.0,
            "tax_amount": q.tax_amount,
            "total_amount": q.total_amount,
            "payment_terms": q.payment_terms,
            "delivery_weeks": q.delivery_weeks,
            "status": q.status,
            "profitability_status": q.profitability_status or ("LOSS_MAKING" if q.is_loss_making else "PROFITABLE"),
            "is_loss_making": q.is_loss_making,
            "version": q.version or 1,
            "approval_status": q.approval_status or "DRAFT",
            "approved_by": q.approved_by,
            "customer_response": q.customer_response,
            "pdf_available": bool(q.pdf_path and os.path.exists(q.pdf_path)),
            "created_at": q.created_at.strftime("%Y-%m-%d %H:%M") if q.created_at else None
        })
    return results


@router.post("")
def create_customer_quotation(
    payload: CustomerQuoteGenerateRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Creates and calculates a customer quotation using deterministic Python Decimal arithmetic.
    Distinguishes Gross Margin from Markup, classifies profitability, and generates PDF.
    """
    try:
        quote_dict = create_customer_quotation_record(
            db=db,
            org_id=org_id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            customer_id=payload.customer_id,
            customer_name=payload.customer_name,
            customer_company=payload.customer_company,
            customer_email=payload.customer_email,
            cost_estimate_id=payload.cost_estimate_id,
            unit_cost=payload.unit_cost,
            unit_selling_price=payload.unit_selling_price,
            target_margin_pct=payload.target_margin_pct,
            discount_pct=payload.discount_pct,
            tax_pct=payload.tax_pct,
            min_margin_pct=payload.min_margin_pct,
            payment_terms=payload.payment_terms,
            delivery_weeks=payload.delivery_weeks,
            validity_days=payload.validity_days,
            terms_conditions=payload.terms_conditions
        )
        return quote_dict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate")
def generate_customer_quotation_legacy_alias(
    payload: CustomerQuoteGenerateRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Legacy alias supporting previous frontends while utilizing the modern calculation engine."""
    return create_customer_quotation(payload=payload, db=db, org_id=org_id)


@router.get("/{quote_id}")
def get_customer_quotation(
    quote_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves full details of a specific customer quotation."""
    cq = db.query(CustomerQuotation).filter(
        CustomerQuotation.id == quote_id,
        CustomerQuotation.organization_id == org_id
    ).first()
    if not cq:
        raise HTTPException(status_code=404, detail="Quotation not found.")

    prod = db.query(Product).filter(Product.id == cq.product_id).first()

    return {
        "id": cq.id,
        "quote_number": cq.quote_number,
        "version": cq.version or 1,
        "customer_id": cq.customer_id,
        "customer_name": cq.customer_name,
        "customer_company": cq.customer_company,
        "customer_email": cq.customer_email,
        "product_id": cq.product_id,
        "product_name": prod.name if prod else "Industrial Component",
        "product_code": prod.code if prod else "IND-PRD",
        "cost_estimate_id": cq.cost_estimate_id,
        "quantity": cq.quantity,
        "unit_production_cost": cq.unit_production_cost,
        "unit_selling_price": cq.unit_selling_price,
        "markup_pct": cq.markup_pct or 0.0,
        "margin_pct": cq.margin_pct,
        "min_margin_pct": cq.min_margin_pct or 15.0,
        "gross_profit": cq.gross_profit or 0.0,
        "subtotal": cq.subtotal,
        "discount_pct": cq.discount_pct or 0.0,
        "discount_amount": cq.discount_amount or 0.0,
        "tax_pct": cq.tax_pct or 18.0,
        "tax_amount": cq.tax_amount,
        "total_amount": cq.total_amount,
        "payment_terms": cq.payment_terms,
        "delivery_weeks": cq.delivery_weeks,
        "validity_days": cq.validity_days,
        "terms_conditions": cq.terms_conditions,
        "status": cq.status,
        "profitability_status": cq.profitability_status or ("LOSS_MAKING" if cq.is_loss_making else "PROFITABLE"),
        "is_loss_making": cq.is_loss_making,
        "approval_status": cq.approval_status or "DRAFT",
        "approved_by": cq.approved_by,
        "approved_at": cq.approved_at.isoformat() if cq.approved_at else None,
        "customer_response": cq.customer_response,
        "customer_notes": cq.customer_notes,
        "items": cq.items_json or [],
        "pdf_available": bool(cq.pdf_path and os.path.exists(cq.pdf_path)),
        "download_url": f"/api/v1/customer-quotes/{cq.id}/pdf",
        "created_at": cq.created_at.strftime("%Y-%m-%d %H:%M") if cq.created_at else None
    }


@router.post("/{quote_id}/recalculate")
def recalculate_quotation(
    quote_id: str,
    payload: CustomerQuoteRecalculateRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Recalculates an existing customer quotation with updated prices, margin targets, or volume,
    increments revision version, and generates a new official PDF.
    """
    try:
        updated = recalculate_customer_quotation(
            db=db,
            org_id=org_id,
            quotation_id=quote_id,
            unit_cost=payload.unit_cost,
            quantity=payload.quantity,
            unit_selling_price=payload.unit_selling_price,
            target_margin_pct=payload.target_margin_pct,
            discount_pct=payload.discount_pct,
            tax_pct=payload.tax_pct,
            min_margin_pct=payload.min_margin_pct,
            payment_terms=payload.payment_terms,
            delivery_weeks=payload.delivery_weeks
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{quote_id}/request-approval")
def request_quotation_approval(
    quote_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Submits quotation to commercial workflow for human review."""
    cq = db.query(CustomerQuotation).filter(
        CustomerQuotation.id == quote_id,
        CustomerQuotation.organization_id == org_id
    ).first()
    if not cq:
        raise HTTPException(status_code=404, detail="Quotation not found.")

    cq.status = "READY_FOR_APPROVAL"
    cq.approval_status = "PENDING_APPROVAL"

    # Add approval request record
    appr = db.query(ApprovalRequest).filter(
        ApprovalRequest.organization_id == org_id,
        ApprovalRequest.entity_id == cq.id,
        ApprovalRequest.request_type == "CUSTOMER_QUOTE"
    ).first()
    if not appr:
        appr = ApprovalRequest(
            organization_id=org_id,
            request_type="CUSTOMER_QUOTE",
            entity_id=cq.id,
            requested_by="Commercial Estimator",
            details_json={
                "quote_number": cq.quote_number,
                "customer": cq.customer_name,
                "quantity": cq.quantity,
                "selling_price": cq.unit_selling_price,
                "production_cost": cq.unit_production_cost,
                "total_value": cq.total_amount,
                "margin_pct": cq.margin_pct,
                "is_loss_making": cq.is_loss_making
            },
            status="PENDING"
        )
        db.add(appr)

    db.commit()
    return {"status": "SUCCESS", "approval_status": "PENDING_APPROVAL"}


@router.post("/{quote_id}/approve")
def approve_quotation(
    quote_id: str,
    payload: CustomerQuoteApprovalActionRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Authorizes quotation for customer dispatch with executive checks."""
    try:
        res = approve_customer_quotation(
            db=db,
            org_id=org_id,
            quotation_id=quote_id,
            approver_name=payload.approver_name or "Commercial Director"
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{quote_id}/pdf")
@router.get("/{quote_id}/download-pdf")
def download_quote_pdf(
    quote_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Streams the official PDF quotation with professional industrial styling."""
    cq = db.query(CustomerQuotation).filter(
        CustomerQuotation.id == quote_id,
        CustomerQuotation.organization_id == org_id
    ).first()
    if not cq:
        raise HTTPException(status_code=404, detail="Quotation not found.")

    filename = f"Customer_Quote_{cq.quote_number.replace('/', '_')}.pdf"
    file_path = cq.pdf_path

    if not file_path or not os.path.exists(file_path):
        prod = db.query(Product).filter(Product.id == cq.product_id).first()
        prod_name = prod.name if prod else "Industrial Component"
        prod_code = prod.code if prod else "IND-PRD"

        pdf_dir = os.path.join(settings.UPLOAD_DIR, "customer_quotes")
        file_path = generate_customer_quotation_pdf(
            quote_number=cq.quote_number,
            customer_name=cq.customer_name,
            customer_company=cq.customer_company or "Customer Enterprise",
            product_name=prod_name,
            product_code=prod_code,
            quantity=cq.quantity,
            unit_selling_price=cq.unit_selling_price,
            unit_cost=cq.unit_production_cost,
            subtotal=cq.subtotal,
            tax_amount=cq.tax_amount,
            total_amount=cq.total_amount,
            margin_pct=cq.margin_pct,
            payment_terms=cq.payment_terms,
            delivery_weeks=cq.delivery_weeks,
            output_dir=pdf_dir
        )
        cq.pdf_path = file_path
        db.commit()

    return FileResponse(file_path, media_type="application/pdf", filename=filename)


@router.post("/{quote_id}/record-response")
def record_customer_response_endpoint(
    quote_id: str,
    payload: CustomerQuoteResponseRecordRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Records customer decision (ACCEPTED, REJECTED, COUNTER_REQUESTED) on the quote."""
    try:
        res = record_customer_response(
            db=db,
            org_id=org_id,
            quotation_id=quote_id,
            response=payload.response,
            notes=payload.notes
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
