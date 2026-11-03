import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_org_id
from app.core.config import settings
from app.models.entities import CustomerQuotation, Product, ApprovalRequest
from app.schemas.domain import CustomerQuoteGenerateRequest
from app.services.pdf_generator import generate_customer_quotation_pdf

router = APIRouter()

@router.get("")
def list_customer_quotations(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    quotes = db.query(CustomerQuotation).filter(CustomerQuotation.organization_id == org_id).order_by(CustomerQuotation.created_at.desc()).all()
    results = []
    for q in quotes:
        results.append({
            "id": q.id,
            "quote_number": q.quote_number,
            "customer_name": q.customer_name,
            "customer_company": q.customer_company,
            "product_id": q.product_id,
            "quantity": q.quantity,
            "unit_production_cost": q.unit_production_cost,
            "unit_selling_price": q.unit_selling_price,
            "subtotal": q.subtotal,
            "tax_amount": q.tax_amount,
            "total_amount": q.total_amount,
            "margin_pct": q.margin_pct,
            "payment_terms": q.payment_terms,
            "delivery_weeks": q.delivery_weeks,
            "status": q.status,
            "is_loss_making": q.is_loss_making,
            "created_at": q.created_at.strftime("%Y-%m-%d %H:%M") if q.created_at else None
        })
    return results

@router.post("/generate")
def generate_customer_quotation(
    payload: CustomerQuoteGenerateRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Builds commercial customer quotation, checks break-even economics,
    flags loss-making conditions, and generates PDF.
    """
    qty = payload.quantity
    u_cost = payload.unit_cost
    u_price = payload.unit_selling_price

    subtotal = qty * u_price
    tax_amount = subtotal * (payload.tax_pct / 100.0)
    total_amount = subtotal + tax_amount

    # Margin calculation: (Revenue - Cost) / Revenue
    total_prod_cost = qty * u_cost
    gross_profit = subtotal - total_prod_cost
    margin_pct = (gross_profit / subtotal) * 100.0 if subtotal > 0 else 0.0

    is_loss_making = u_price < u_cost

    product_code = "SS304-BRK-500"
    product_name = "Stainless Steel Industrial Bracket"
    if payload.product_id:
        p = db.query(Product).filter(Product.id == payload.product_id).first()
        if p:
            product_code = p.code
            product_name = p.name

    quote_no = f"IP-CQ-{int(qty)}-{db.query(CustomerQuotation).count() + 1:03d}"

    # Generate PDF
    pdf_dir = os.path.join(settings.UPLOAD_DIR, "customer_quotes")
    pdf_path = generate_customer_quotation_pdf(
        quote_number=quote_no,
        customer_name=payload.customer_name,
        customer_company=payload.customer_company,
        product_name=product_name,
        product_code=product_code,
        quantity=qty,
        unit_selling_price=u_price,
        unit_cost=u_cost,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        margin_pct=round(margin_pct, 1),
        payment_terms=payload.payment_terms,
        delivery_weeks=payload.delivery_weeks,
        output_dir=pdf_dir
    )

    cq = CustomerQuotation(
        organization_id=org_id,
        quote_number=quote_no,
        customer_name=payload.customer_name,
        customer_company=payload.customer_company,
        customer_email=payload.customer_email,
        product_id=payload.product_id or "default_product",
        quantity=qty,
        unit_production_cost=u_cost,
        unit_selling_price=u_price,
        subtotal=subtotal,
        tax_pct=payload.tax_pct,
        tax_amount=tax_amount,
        total_amount=total_amount,
        margin_pct=round(margin_pct, 2),
        payment_terms=payload.payment_terms,
        delivery_weeks=payload.delivery_weeks,
        terms_conditions=payload.terms_conditions,
        status="PENDING_APPROVAL",
        is_loss_making=is_loss_making
    )
    db.add(cq)
    db.flush()

    # Human approval record
    appr = ApprovalRequest(
        organization_id=org_id,
        request_type="CUSTOMER_QUOTE",
        entity_id=cq.id,
        requested_by="Customer Quotation Agent",
        details_json={
            "quote_number": quote_no,
            "customer": payload.customer_name,
            "quantity": qty,
            "selling_price": u_price,
            "production_cost": u_cost,
            "total_value": total_amount,
            "margin_pct": round(margin_pct, 1),
            "is_loss_making": is_loss_making
        },
        status="PENDING"
    )
    db.add(appr)

    db.commit()
    db.refresh(cq)

    return {
        "id": cq.id,
        "quote_number": cq.quote_number,
        "customer_name": cq.customer_name,
        "total_amount": cq.total_amount,
        "margin_pct": cq.margin_pct,
        "is_loss_making": cq.is_loss_making,
        "status": cq.status,
        "pdf_available": True,
        "download_url": f"/api/v1/customer-quotes/{cq.id}/download-pdf"
    }

@router.get("/{quote_id}/download-pdf")
def download_quote_pdf(
    quote_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    cq = db.query(CustomerQuotation).filter(
        CustomerQuotation.id == quote_id,
        CustomerQuotation.organization_id == org_id
    ).first()
    if not cq:
        raise HTTPException(status_code=404, detail="Quotation not found.")

    filename = f"Customer_Quote_{cq.quote_number.replace('/', '_')}.pdf"
    file_path = os.path.join(settings.UPLOAD_DIR, "customer_quotes", filename)

    if not os.path.exists(file_path):
        # Regenerate on the fly if missing
        file_path = generate_customer_quotation_pdf(
            quote_number=cq.quote_number,
            customer_name=cq.customer_name,
            customer_company=cq.customer_company or "Customer Enterprise",
            product_name="Stainless Steel Industrial Bracket",
            product_code="SS304-BRK-500",
            quantity=cq.quantity,
            unit_selling_price=cq.unit_selling_price,
            unit_cost=cq.unit_production_cost,
            subtotal=cq.subtotal,
            tax_amount=cq.tax_amount,
            total_amount=cq.total_amount,
            margin_pct=cq.margin_pct,
            payment_terms=cq.payment_terms,
            delivery_weeks=cq.delivery_weeks,
            output_dir=os.path.join(settings.UPLOAD_DIR, "customer_quotes")
        )

    return FileResponse(file_path, media_type="application/pdf", filename=filename)

