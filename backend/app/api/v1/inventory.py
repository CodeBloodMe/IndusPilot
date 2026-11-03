from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_org_id
from app.models.entities import Inventory, InventoryMovement, Material, StockReservation
from app.schemas.domain import (
    InventoryOut, StockReceiveRequest, StockIssueRequest,
    StockReserveRequest, StockReleaseRequest, StockAdjustRequest,
    StockAvailabilityCheckRequest
)
from app.services.inventory_service import (
    receive_stock, issue_stock, reserve_stock, release_reservation,
    adjust_stock, get_inventory_alerts, get_or_create_inventory
)
from app.calculations.inventory_netting import calculate_net_procurement_requirement

router = APIRouter()


@router.get("", response_model=List[InventoryOut])
def list_inventory_overview(
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    inventories = db.query(Inventory).filter(Inventory.organization_id == org_id).all()
    results = []

    for inv in inventories:
        mat = inv.material
        if not mat:
            continue

        if search:
            s = search.lower().strip()
            if s not in mat.name.lower() and s not in mat.code.lower():
                continue

        avail = max(0.0, inv.current_stock - inv.reserved_stock)
        status = "HEALTHY"
        if avail <= 0:
            status = "CRITICAL_SHORTAGE"
        elif avail <= inv.safety_stock:
            status = "CRITICAL_SHORTAGE"
        elif avail <= inv.reorder_level:
            status = "REORDER_REQUIRED"

        if status_filter and status != status_filter:
            continue

        results.append(InventoryOut(
            material_id=inv.material_id,
            material_code=mat.code,
            material_name=mat.name,
            unit=mat.unit or "kg",
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


@router.get("/alerts")
def get_operational_alerts(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Returns low-stock, safety stock breach, and reorder alerts with explanations."""
    alerts = get_inventory_alerts(db, org_id)
    return {
        "alerts_count": len(alerts),
        "alerts": alerts
    }


@router.get("/movements")
def list_movements(
    material_id: Optional[str] = None,
    movement_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves transactional inventory ledger audit movements."""
    query = db.query(InventoryMovement).filter(InventoryMovement.organization_id == org_id)
    if material_id:
        query = query.filter(InventoryMovement.material_id == material_id)
    if movement_type:
        query = query.filter(InventoryMovement.movement_type == movement_type.upper().strip())

    movements = query.order_by(InventoryMovement.created_at.desc()).limit(limit).all()
    results = []
    for m in movements:
        mat = db.query(Material).filter(Material.id == m.material_id).first()
        results.append({
            "id": m.id,
            "material_id": m.material_id,
            "material_name": mat.name if mat else "Material",
            "material_code": mat.code if mat else "",
            "movement_type": m.movement_type,
            "quantity": m.quantity,
            "unit": m.unit,
            "source": m.source,
            "destination": m.destination,
            "reference_id": m.reference_id,
            "production_job_id": m.production_job_id,
            "unit_cost": m.unit_cost,
            "notes": m.notes,
            "created_at": m.created_at.isoformat() if m.created_at else None
        })
    return results


@router.post("/receive", status_code=201)
def receive_stock_endpoint(
    payload: StockReceiveRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    try:
        res = receive_stock(
            db=db,
            org_id=org_id,
            material_id=payload.material_id,
            quantity=payload.quantity,
            unit=payload.unit,
            reference_id=payload.reference_id,
            source=payload.source,
            unit_cost=payload.unit_cost,
            notes=payload.notes,
            idempotency_key=payload.idempotency_key
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/issue")
def issue_stock_endpoint(
    payload: StockIssueRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    try:
        res = issue_stock(
            db=db,
            org_id=org_id,
            material_id=payload.material_id,
            quantity=payload.quantity,
            unit=payload.unit,
            reference_id=payload.reference_id,
            destination=payload.destination,
            production_job_id=payload.production_job_id,
            notes=payload.notes,
            allow_negative_stock=payload.allow_negative_stock,
            idempotency_key=payload.idempotency_key
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reserve")
def reserve_stock_endpoint(
    payload: StockReserveRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    try:
        res = reserve_stock(
            db=db,
            org_id=org_id,
            material_id=payload.material_id,
            quantity=payload.quantity,
            production_job_id=payload.production_job_id,
            unit=payload.unit,
            notes=payload.notes
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/release")
def release_stock_endpoint(
    payload: StockReleaseRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    try:
        res = release_reservation(
            db=db,
            org_id=org_id,
            reservation_id=payload.reservation_id,
            notes=payload.notes
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/adjust")
def adjust_stock_endpoint(
    payload: StockAdjustRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    try:
        res = adjust_stock(
            db=db,
            org_id=org_id,
            material_id=payload.material_id,
            new_physical_stock=payload.new_physical_stock,
            reason=payload.reason,
            notes=payload.notes
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/availability-check")
def check_material_availability(
    payload: StockAvailabilityCheckRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Checks multiple material requirements against real-time unreserved stock.
    Returns shortage analysis and procurement recommendations.
    """
    summary = []
    shortage_count = 0

    for item in payload.items:
        inv = db.query(Inventory).filter(
            Inventory.material_id == item.material_id,
            Inventory.organization_id == org_id
        ).first()

        cur_stock = inv.current_stock if inv else 0.0
        res_stock = inv.reserved_stock if inv else 0.0
        inc_stock = inv.incoming_stock if inv else 0.0
        saf_stock = inv.safety_stock if inv else 0.0

        netting = calculate_net_procurement_requirement(
            gross_requirement=item.gross_quantity_required,
            current_stock=cur_stock,
            reserved_stock=res_stock,
            incoming_stock=inc_stock,
            safety_stock=saf_stock
        )

        mat = inv.material if inv else db.query(Material).filter(Material.id == item.material_id).first()

        if netting["has_shortage"]:
            shortage_count += 1

        summary.append({
            "material_id": item.material_id,
            "material_name": mat.name if mat else "Material",
            "material_code": mat.code if mat else "",
            "unit": item.unit,
            "gross_required": item.gross_quantity_required,
            "netting": netting
        })

    return {
        "checked_items_count": len(summary),
        "shortages_count": shortage_count,
        "is_production_ready": shortage_count == 0,
        "items": summary
    }


@router.get("/{material_id}")
def get_single_material_inventory(
    material_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    inv = db.query(Inventory).filter(
        Inventory.material_id == material_id,
        Inventory.organization_id == org_id
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found.")

    mat = inv.material
    avail = max(0.0, inv.current_stock - inv.reserved_stock)
    return {
        "material_id": inv.material_id,
        "material_code": mat.code if mat else "N/A",
        "material_name": mat.name if mat else "N/A",
        "current_stock": inv.current_stock,
        "reserved_stock": inv.reserved_stock,
        "available_stock": avail,
        "incoming_stock": inv.incoming_stock,
        "safety_stock": inv.safety_stock,
        "reorder_level": inv.reorder_level,
        "reorder_quantity": inv.reorder_quantity,
        "unit_cost_valuation": inv.unit_cost_valuation,
        "warehouse_location": inv.warehouse_location,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None
    }

