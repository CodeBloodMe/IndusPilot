from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_org_id
from app.models.entities import Material, Inventory, InventoryMovement
from app.schemas.domain import (
    MaterialCreate, MaterialOut, InventoryOut,
    MaterialMatchRequest, MaterialMatchResponse, MaterialMatchCandidate
)
from app.services.material_matcher import match_material_specification

router = APIRouter()


@router.get("", response_model=List[MaterialOut])
def list_materials(
    category: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    query = db.query(Material).filter(Material.organization_id == org_id)
    if is_active is not None:
        query = query.filter(Material.is_active == is_active)
    if category:
        query = query.filter(Material.category == category)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Material.name.ilike(s),
                Material.code.ilike(s),
                Material.grade.ilike(s),
                Material.specifications.ilike(s)
            )
        )
    return query.order_by(Material.code.asc()).all()


@router.post("", response_model=MaterialOut)
def create_material(
    payload: MaterialCreate,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    # Check duplicate code
    existing = db.query(Material).filter(
        Material.organization_id == org_id,
        Material.code.ilike(payload.code.strip())
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Material with code '{payload.code}' already exists.")

    mat = Material(
        organization_id=org_id,
        code=payload.code.strip(),
        name=payload.name.strip(),
        category=payload.category,
        grade=payload.grade,
        specifications=payload.specifications,
        manufacturing_forms=payload.manufacturing_forms or "Sheet, Plate",
        unit=payload.unit,
        density_g_cm3=payload.density_g_cm3,
        standard_cost=payload.standard_cost,
        description=payload.description,
        is_active=payload.is_active
    )
    db.add(mat)
    db.flush()

    # Automatically initialize inventory record
    inv = Inventory(
        organization_id=org_id,
        material_id=mat.id,
        current_stock=0.0,
        reserved_stock=0.0,
        incoming_stock=0.0,
        safety_stock=50.0,
        reorder_level=100.0,
        warehouse_location="Rack A-1"
    )
    db.add(inv)
    db.commit()
    db.refresh(mat)
    return mat


@router.post("/match", response_model=MaterialMatchResponse)
def match_material(
    payload: MaterialMatchRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Matches an extracted raw material description against the organization's catalogue.
    Returns ranked candidates, similarity score, confidence band, and auto-match status.
    """
    materials = db.query(Material).filter(
        Material.organization_id == org_id,
        Material.is_active == True
    ).all()

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
        for m in materials
    ]

    result = match_material_specification(
        query_text=payload.raw_text,
        catalogue_materials=catalogue,
        declared_grade=payload.grade,
        thickness_mm=payload.thickness_mm
    )

    best_cand = None
    if result.get("best_match"):
        bm = result["best_match"]
        best_cand = MaterialMatchCandidate(
            material_id=bm["material_id"],
            code=bm["code"],
            name=bm["name"],
            grade=bm.get("grade"),
            category=bm["category"],
            standard_unit=bm["standard_unit"],
            standard_cost=bm["standard_cost"],
            similarity_score=bm["similarity_score"],
            confidence_band=bm["confidence_band"],
            match_reason=bm["match_reason"]
        )

    cand_list = [
        MaterialMatchCandidate(
            material_id=c["material_id"],
            code=c["code"],
            name=c["name"],
            grade=c.get("grade"),
            category=c["category"],
            standard_unit=c["standard_unit"],
            standard_cost=c["standard_cost"],
            similarity_score=c["similarity_score"],
            confidence_band=c["confidence_band"],
            match_reason=c["match_reason"]
        )
        for c in result.get("candidates", [])
    ]

    return MaterialMatchResponse(
        query_text=payload.raw_text,
        best_match=best_cand,
        candidates=cand_list,
        auto_matched=result.get("auto_matched", False)
    )


@router.get("/inventory", response_model=List[InventoryOut])
def list_inventory(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    inventories = db.query(Inventory).filter(Inventory.organization_id == org_id).all()
    results = []
    for inv in inventories:
        mat = inv.material
        avail = max(0.0, inv.current_stock - inv.reserved_stock)
        status = "HEALTHY"
        if avail <= inv.safety_stock:
            status = "CRITICAL_SHORTAGE"
        elif avail <= inv.reorder_level:
            status = "REORDER_REQUIRED"

        results.append(InventoryOut(
            material_id=inv.material_id,
            material_code=mat.code if mat else "N/A",
            material_name=mat.name if mat else "N/A",
            unit=mat.unit if mat else "kg",
            current_stock=inv.current_stock,
            reserved_stock=inv.reserved_stock,
            available_stock=avail,
            incoming_stock=inv.incoming_stock,
            safety_stock=inv.safety_stock,
            reorder_level=inv.reorder_level,
            warehouse_location=inv.warehouse_location,
            status=status
        ))
    return results


@router.get("/{material_id}/price-history")
def get_material_price_history(
    material_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Returns empirical and historical supplier quotation price points for the selected material.
    Clearly distinguishes verified historical quotations from active current offers and simulation tags.
    """
    mat = db.query(Material).filter(Material.id == material_id, Material.organization_id == org_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found.")

    from app.models.entities import QuotationItem, SupplierQuotation, Supplier
    from app.calculations.landed_cost import calculate_landed_cost

    # Query items matching either this material_id or matching grade & category
    items_query = db.query(QuotationItem).join(SupplierQuotation).filter(
        SupplierQuotation.organization_id == org_id,
        or_(
            QuotationItem.material_id == material_id,
            QuotationItem.grade.ilike(f"%{mat.grade}%") if mat.grade else False,
            QuotationItem.material_name_raw.ilike(f"%{mat.name}%")
        )
    ).order_by(SupplierQuotation.quotation_date.asc()).all()

    price_history = []
    for it in items_query:
        q = it.quotation
        sup = q.supplier if q else None
        
        # Calculate landed economics
        try:
            landed = calculate_landed_cost(
                unit_price=it.unit_price,
                quantity=it.quantity or 100.0,
                tax_pct=q.tax_pct if q else 18.0,
                is_tax_inclusive=q.is_tax_inclusive if q else False,
                freight_total=q.freight_cost if q else 0.0
            )
            unit_landed = landed["effective_unit_landed_cost"]
        except Exception:
            unit_landed = it.unit_price

        # Determine price point classification
        is_current = bool(q.valid_until and q.valid_until >= q.quotation_date)
        if q.status == "ARCHIVED":
            data_type = "HISTORICAL_QUOTATION"
        elif q.status == "VERIFIED" and is_current:
            data_type = "CURRENT_OFFER"
        else:
            data_type = "SIMULATED_DEMO" if getattr(sup, "is_simulated", True) else "HISTORICAL_RECORD"

        price_history.append({
            "quotation_id": q.id,
            "quotation_number": q.quotation_number,
            "quotation_date": q.quotation_date.isoformat() if q.quotation_date else None,
            "valid_until": q.valid_until.isoformat() if q.valid_until else None,
            "supplier_id": sup.id if sup else "N/A",
            "supplier_name": sup.name if sup else "Unknown Vendor",
            "city": sup.city if sup else "",
            "material_name": it.material_name_raw,
            "grade": it.grade or mat.grade,
            "thickness_mm": it.thickness_mm,
            "quantity": it.quantity,
            "unit": it.unit,
            "quoted_unit_price": it.unit_price,
            "effective_unit_landed_cost": unit_landed,
            "freight_cost": q.freight_cost if q else 0.0,
            "payment_terms": sup.credit_period_days if sup else 30,
            "status": q.status,
            "data_type": data_type,
            "is_simulated": getattr(sup, "is_simulated", True)
        })

    return {
        "material_id": mat.id,
        "material_code": mat.code,
        "material_name": mat.name,
        "grade": mat.grade,
        "unit": mat.unit,
        "standard_cost": mat.standard_cost,
        "price_history_records_count": len(price_history),
        "history": price_history
    }
