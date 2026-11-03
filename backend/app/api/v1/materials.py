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
