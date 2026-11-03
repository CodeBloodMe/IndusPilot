import os
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_org_id
from app.core.config import settings
from app.models.entities import UploadedDocument, SupplierQuotation, QuotationItem, Supplier, Material
from app.services.document_parser import parse_uploaded_quotation_file
from app.services.material_matcher import match_material_specification
from app.schemas.domain import QuotationConfirmRequest

router = APIRouter()


@router.get("")
def list_quotations(
    supplier_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Lists supplier quotations with filters for supplier, verification status, and reference keyword search."""
    query = db.query(SupplierQuotation).filter(SupplierQuotation.organization_id == org_id)

    if supplier_id:
        query = query.filter(SupplierQuotation.supplier_id == supplier_id)
    if status:
        query = query.filter(SupplierQuotation.status == status)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                SupplierQuotation.quotation_number.ilike(s),
                SupplierQuotation.review_notes.ilike(s)
            )
        )

    quotes = query.order_by(SupplierQuotation.quotation_date.desc()).all()
    results = []
    for q in quotes:
        results.append({
            "id": q.id,
            "quotation_number": q.quotation_number,
            "supplier_id": q.supplier_id,
            "supplier_name": q.supplier.name if q.supplier else "Unknown Supplier",
            "supplier_city": q.supplier.city if q.supplier else None,
            "supplier_rating": q.supplier.quality_rating if q.supplier else 4.0,
            "document_id": q.document_id,
            "quotation_date": q.quotation_date.strftime("%Y-%m-%d") if q.quotation_date else None,
            "valid_until": q.valid_until.strftime("%Y-%m-%d") if q.valid_until else None,
            "subtotal": q.subtotal,
            "tax_amount": q.tax_amount,
            "tax_pct": q.tax_pct,
            "freight_cost": q.freight_cost,
            "other_charges": q.other_charges,
            "is_tax_inclusive": q.is_tax_inclusive,
            "total_amount": q.total_amount,
            "currency": q.currency or "INR",
            "status": q.status,
            "verified_at": q.verified_at.isoformat() if q.verified_at else None,
            "verified_by": q.verified_by,
            "items_count": len(q.items),
            "items": [
                {
                    "id": it.id,
                    "material_id": it.material_id,
                    "material_name": it.material_name_raw,
                    "grade": it.grade,
                    "thickness_mm": it.thickness_mm,
                    "dimensions": it.dimensions,
                    "quantity": it.quantity,
                    "unit": it.unit,
                    "unit_price": it.unit_price,
                    "moq": it.moq,
                    "lead_time_days": it.lead_time_days,
                    "line_total": it.line_total,
                    "match_confidence": it.match_confidence,
                    "is_quarantined": it.is_quarantined,
                    "quarantine_reason": it.quarantine_reason
                }
                for it in q.items
            ]
        })
    return results


@router.get("/{quotation_id}")
def get_quotation_details(
    quotation_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves full details of a quotation including line items, supplier profile, and extraction audit trail."""
    q = db.query(SupplierQuotation).filter(
        SupplierQuotation.id == quotation_id,
        SupplierQuotation.organization_id == org_id
    ).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found.")

    return {
        "id": q.id,
        "quotation_number": q.quotation_number,
        "supplier_id": q.supplier_id,
        "supplier_name": q.supplier.name if q.supplier else "Unknown",
        "supplier_email": q.supplier.email if q.supplier else None,
        "supplier_phone": q.supplier.phone if q.supplier else None,
        "supplier_city": q.supplier.city if q.supplier else None,
        "document_id": q.document_id,
        "quotation_date": q.quotation_date.strftime("%Y-%m-%d") if q.quotation_date else None,
        "valid_until": q.valid_until.strftime("%Y-%m-%d") if q.valid_until else None,
        "subtotal": q.subtotal,
        "tax_pct": q.tax_pct,
        "tax_amount": q.tax_amount,
        "freight_cost": q.freight_cost,
        "other_charges": q.other_charges,
        "is_tax_inclusive": q.is_tax_inclusive,
        "total_amount": q.total_amount,
        "currency": q.currency,
        "status": q.status,
        "review_notes": q.review_notes,
        "original_extracted_json": q.original_extracted_json,
        "user_corrected_json": q.user_corrected_json,
        "verified_at": q.verified_at.isoformat() if q.verified_at else None,
        "verified_by": q.verified_by,
        "items": [
            {
                "id": it.id,
                "material_id": it.material_id,
                "material_name": it.material_name_raw,
                "grade": it.grade,
                "thickness_mm": it.thickness_mm,
                "dimensions": it.dimensions,
                "quantity": it.quantity,
                "unit": it.unit,
                "unit_price": it.unit_price,
                "moq": it.moq,
                "lead_time_days": it.lead_time_days,
                "line_total": it.line_total,
                "match_confidence": it.match_confidence,
                "is_quarantined": it.is_quarantined,
                "quarantine_reason": it.quarantine_reason
            }
            for it in q.items
        ]
    }


@router.post("/confirm")
def confirm_and_save_quotation(
    payload: QuotationConfirmRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Saves human-reviewed and verified quotation into the database.
    Links or registers the supplier, matches catalogue materials, saves line items,
    and preserves both machine-extracted and human-corrected states.
    """
    # 1. Match or create supplier
    supplier = None
    if payload.supplier_id:
        supplier = db.query(Supplier).filter(
            Supplier.id == payload.supplier_id,
            Supplier.organization_id == org_id
        ).first()

    if not supplier:
        supplier = db.query(Supplier).filter(
            Supplier.organization_id == org_id,
            Supplier.name.ilike(f"%{payload.supplier_name.strip()}%")
        ).first()

    if not supplier:
        supplier = Supplier(
            organization_id=org_id,
            name=payload.supplier_name.strip(),
            company_name=payload.supplier_name.strip(),
            category="Primary Raw Materials",
            quality_rating=4.2,
            reliability_score=85.0,
            on_time_delivery_pct=90.0,
            payment_terms_days=30,
            is_active=True,
            is_simulated=True
        )
        db.add(supplier)
        db.flush()

    # Parse dates safely
    q_date = datetime.utcnow()
    if payload.quotation_date:
        try:
            q_date = datetime.strptime(payload.quotation_date[:10], "%Y-%m-%d")
        except ValueError:
            pass

    v_until = None
    if payload.valid_until:
        try:
            v_until = datetime.strptime(payload.valid_until[:10], "%Y-%m-%d")
        except ValueError:
            pass

    # 2. Create SupplierQuotation
    sq = SupplierQuotation(
        organization_id=org_id,
        supplier_id=supplier.id,
        document_id=payload.document_id,
        quotation_number=payload.quotation_number.strip(),
        quotation_date=q_date,
        valid_until=v_until,
        subtotal=payload.subtotal,
        tax_pct=payload.tax_pct,
        tax_amount=payload.tax_amount,
        freight_cost=payload.freight_cost,
        other_charges=payload.other_charges,
        is_tax_inclusive=payload.is_tax_inclusive,
        total_amount=payload.total_amount,
        currency=payload.currency or "INR",
        status="VERIFIED",
        review_notes=payload.review_notes,
        original_extracted_json=payload.original_extracted_json,
        user_corrected_json=payload.user_corrected_json or payload.model_dump(),
        verified_at=datetime.utcnow(),
        verified_by="Human Reviewer (Verified)"
    )
    db.add(sq)
    db.flush()

    # 3. Create QuotationItems
    all_materials = db.query(Material).filter(Material.organization_id == org_id, Material.is_active == True).all()
    catalogue = [
        {
            "id": m.id,
            "code": m.code,
            "name": m.name,
            "grade": m.grade,
            "category": m.category,
            "unit": m.unit,
            "standard_cost": m.standard_cost,
            "manufacturing_forms": m.manufacturing_forms
        }
        for m in all_materials
    ]

    for it in payload.items:
        mat_id = it.material_id
        if not mat_id:
            match_res = match_material_specification(
                query_text=it.material_name,
                catalogue_materials=catalogue,
                declared_grade=it.grade,
                thickness_mm=it.thickness_mm
            )
            if match_res.get("best_match"):
                mat_id = match_res["best_match"]["material_id"]

        qi = QuotationItem(
            quotation_id=sq.id,
            material_id=mat_id,
            material_name_raw=it.material_name,
            grade=it.grade,
            thickness_mm=it.thickness_mm,
            dimensions=it.dimensions,
            quantity=it.quantity,
            unit=it.unit,
            unit_price=it.unit_price,
            moq=it.moq,
            lead_time_days=it.lead_time_days,
            line_total=it.line_total,
            tax_pct=payload.tax_pct,
            match_confidence=it.match_confidence or 0.85,
            is_quarantined=it.is_quarantined,
            quarantine_reason=it.quarantine_reason
        )
        db.add(qi)

    # 4. If uploaded document is linked, update its status to VERIFIED
    if payload.document_id:
        doc = db.query(UploadedDocument).filter(
            UploadedDocument.id == payload.document_id,
            UploadedDocument.organization_id == org_id
        ).first()
        if doc:
            doc.supplier_id = supplier.id
            doc.status = "VERIFIED"
            doc.validation_status = "VERIFIED"

    # Update supplier stats
    supplier.total_orders_count = (supplier.total_orders_count or 0) + 1
    supplier.total_historical_spend = (supplier.total_historical_spend or 0.0) + sq.total_amount

    db.commit()
    db.refresh(sq)

    return {
        "status": "SAVED",
        "quotation_id": sq.id,
        "quotation_number": sq.quotation_number,
        "supplier_id": supplier.id,
        "supplier_name": supplier.name,
        "total_amount": sq.total_amount,
        "items_count": len(payload.items)
    }


@router.post("/{quotation_id}/verify")
def verify_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Explicitly signs off and approves a quotation for procurement and cost estimation."""
    q = db.query(SupplierQuotation).filter(
        SupplierQuotation.id == quotation_id,
        SupplierQuotation.organization_id == org_id
    ).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found.")

    q.status = "VERIFIED"
    q.verified_at = datetime.utcnow()
    q.verified_by = "Estimator / Procurement Lead"

    if q.document_id:
        doc = db.query(UploadedDocument).filter(UploadedDocument.id == q.document_id).first()
        if doc:
            doc.validation_status = "VERIFIED"
            doc.status = "VERIFIED"

    db.commit()
    return {"status": "VERIFIED", "quotation_id": q.id, "verified_at": q.verified_at.isoformat()}


@router.post("/{quotation_id}/reject")
def reject_quotation(
    quotation_id: str,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Rejects or archives an invalid or uncompetitive quotation."""
    q = db.query(SupplierQuotation).filter(
        SupplierQuotation.id == quotation_id,
        SupplierQuotation.organization_id == org_id
    ).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found.")

    q.status = "REJECTED"
    if reason:
        q.review_notes = f"Rejected: {reason}"
    db.commit()
    return {"status": "REJECTED", "quotation_id": q.id, "reason": reason}
