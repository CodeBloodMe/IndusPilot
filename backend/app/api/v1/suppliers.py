from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_org_id
from app.models.entities import Supplier, SupplierMaterial, SupplierQuotation
from app.schemas.domain import SupplierCreate, SupplierUpdate, SupplierOut

router = APIRouter()


def _format_supplier_out(s: Supplier) -> SupplierOut:
    quote_count = len(s.quotations) if s.quotations else 0
    return SupplierOut(
        id=s.id,
        organization_id=s.organization_id,
        name=s.name,
        company_name=s.company_name or s.name,
        contact_person=s.contact_person,
        email=s.email,
        phone=s.phone,
        address=s.address,
        city=s.city,
        state=s.state,
        country=s.country or "India",
        postal_code=s.postal_code,
        website=s.website,
        gst_number=s.gst_number,
        category=s.category or "Primary Raw Materials",
        manufacturing_specialisation=s.manufacturing_specialisation,
        credit_period_days=s.credit_period_days or 30,
        moq_general=s.moq_general or 100.0,
        capacity_monthly_tons=s.capacity_monthly_tons or 50.0,
        lead_time_days=s.lead_time_days or 7,
        quality_rating=s.quality_rating or 4.2,
        reliability_score=s.reliability_score or 85.0,
        on_time_delivery_pct=s.on_time_delivery_pct or 90.0,
        payment_terms_days=s.payment_terms_days or 30,
        total_historical_spend=s.total_historical_spend or 0.0,
        total_orders_count=s.total_orders_count or 0,
        rejection_rate_pct=s.rejection_rate_pct or 0.5,
        quotation_count=quote_count,
        is_active=s.is_active if s.is_active is not None else True,
        is_simulated=s.is_simulated if s.is_simulated is not None else False,
        created_at=s.created_at.isoformat() if s.created_at else None
    )


@router.get("", response_model=List[SupplierOut])
def list_suppliers(
    category: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    material_filter: Optional[str] = None,
    min_rating: Optional[float] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Search and filter suppliers across category, city, materials supplied, rating, and keyword search.
    """
    query = db.query(Supplier).filter(Supplier.organization_id == org_id)

    if is_active is not None:
        query = query.filter(Supplier.is_active == is_active)
    if category:
        query = query.filter(Supplier.category.ilike(f"%{category}%"))
    if city:
        query = query.filter(Supplier.city.ilike(f"%{city}%"))
    if min_rating is not None:
        query = query.filter(Supplier.quality_rating >= min_rating)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Supplier.name.ilike(search_term),
                Supplier.company_name.ilike(search_term),
                Supplier.contact_person.ilike(search_term),
                Supplier.city.ilike(search_term),
                Supplier.gst_number.ilike(search_term)
            )
        )

    suppliers = query.order_by(Supplier.quality_rating.desc()).all()

    if material_filter:
        mf = material_filter.lower().strip()
        filtered = []
        for s in suppliers:
            mat_names = [m.material_name.lower() for m in s.materials_supplied]
            if any(mf in mn for mn in mat_names):
                filtered.append(s)
            elif s.manufacturing_specialisation and mf in s.manufacturing_specialisation.lower():
                filtered.append(s)
        suppliers = filtered

    return [_format_supplier_out(s) for s in suppliers]


@router.post("", response_model=SupplierOut)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Registers a new supplier with duplicate detection on vendor name and GSTIN.
    """
    clean_name = payload.name.strip()

    # Duplicate check on name
    existing_name = db.query(Supplier).filter(
        Supplier.organization_id == org_id,
        Supplier.name.ilike(clean_name)
    ).first()
    if existing_name:
        raise HTTPException(
            status_code=409,
            detail=f"A supplier with name '{clean_name}' already exists (ID: {existing_name.id})."
        )

    # Duplicate check on GSTIN if provided
    if payload.gst_number and payload.gst_number.strip():
        clean_gst = payload.gst_number.strip()
        existing_gst = db.query(Supplier).filter(
            Supplier.organization_id == org_id,
            Supplier.gst_number == clean_gst
        ).first()
        if existing_gst:
            raise HTTPException(
                status_code=409,
                detail=f"A supplier with GSTIN '{clean_gst}' already exists: '{existing_gst.name}' (ID: {existing_gst.id})."
            )

    supplier = Supplier(
        organization_id=org_id,
        name=clean_name,
        company_name=payload.company_name or clean_name,
        contact_person=payload.contact_person,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        country=payload.country or "India",
        postal_code=payload.postal_code,
        website=payload.website,
        gst_number=payload.gst_number,
        category=payload.category,
        manufacturing_specialisation=payload.manufacturing_specialisation,
        credit_period_days=payload.credit_period_days,
        moq_general=payload.moq_general,
        capacity_monthly_tons=payload.capacity_monthly_tons,
        lead_time_days=payload.lead_time_days,
        quality_rating=payload.quality_rating,
        reliability_score=payload.reliability_score,
        on_time_delivery_pct=payload.on_time_delivery_pct,
        payment_terms_days=payload.payment_terms_days,
        is_active=payload.is_active,
        is_simulated=payload.is_simulated
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return _format_supplier_out(supplier)


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(
    supplier_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves full profile and performance analytics of an individual supplier."""
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.organization_id == org_id
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    return _format_supplier_out(supplier)


@router.patch("/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: str,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Updates supplier commercial, contact, and rating fields."""
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.organization_id == org_id
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)
    return _format_supplier_out(supplier)


@router.delete("/{supplier_id}")
def delete_supplier(
    supplier_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Soft-deactivates a supplier record."""
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.organization_id == org_id
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    supplier.is_active = False
    db.commit()
    return {"status": "DEACTIVATED", "supplier_id": supplier_id, "message": f"Supplier '{supplier.name}' has been deactivated."}


@router.get("/{supplier_id}/quotations")
def get_supplier_quotation_history(
    supplier_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Returns chronological quotation history and pricing trends for a specific supplier."""
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.organization_id == org_id
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    quotes = db.query(SupplierQuotation).filter(
        SupplierQuotation.supplier_id == supplier_id,
        SupplierQuotation.organization_id == org_id
    ).order_by(SupplierQuotation.quotation_date.desc()).all()

    return [
        {
            "id": q.id,
            "quotation_number": q.quotation_number,
            "quotation_date": q.quotation_date.strftime("%Y-%m-%d") if q.quotation_date else None,
            "valid_until": q.valid_until.strftime("%Y-%m-%d") if q.valid_until else None,
            "total_amount": q.total_amount,
            "subtotal": q.subtotal,
            "status": q.status,
            "items_count": len(q.items),
            "items": [
                {
                    "material_name": it.material_name_raw,
                    "unit_price": it.unit_price,
                    "unit": it.unit,
                    "lead_time_days": it.lead_time_days
                }
                for it in q.items
            ]
        }
        for q in quotes
    ]
