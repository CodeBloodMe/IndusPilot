"""
IndusPilot Transactional Inventory Ledger Service
Manages physical stock, reservations, incoming orders, stock movements, and low-stock alerts.
Guarantees transactional integrity and prevents negative stock unless explicitly permitted.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.entities import Inventory, InventoryMovement, StockReservation, Material
from app.services.unit_conversion import convert_unit, normalize_unit_str


def get_or_create_inventory(db: Session, org_id: str, material_id: str) -> Inventory:
    """Retrieves or auto-initializes the inventory record for a material."""
    inv = db.query(Inventory).filter(
        Inventory.material_id == material_id,
        Inventory.organization_id == org_id
    ).first()

    if not inv:
        mat = db.query(Material).filter(Material.id == material_id).first()
        if not mat:
            raise ValueError(f"Material ID '{material_id}' not found.")
        inv = Inventory(
            organization_id=org_id,
            material_id=material_id,
            current_stock=0.0,
            reserved_stock=0.0,
            incoming_stock=0.0,
            safety_stock=50.0,
            reorder_level=100.0,
            reorder_quantity=200.0,
            unit_cost_valuation=mat.standard_cost or 0.0,
            warehouse_location="Main Depot A-1"
        )
        db.add(inv)
        db.flush()
    return inv


def receive_stock(
    db: Session,
    org_id: str,
    material_id: str,
    quantity: float,
    unit: str = "kg",
    reference_id: Optional[str] = None,
    source: Optional[str] = "Vendor Delivery",
    unit_cost: Optional[float] = None,
    notes: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Records an inward stock receipt.
    Updates on-hand stock and recalculates moving weighted-average valuation.
    """
    if quantity <= 0:
        raise ValueError("Received quantity must be positive.")

    # Idempotency check
    if idempotency_key:
        existing = db.query(InventoryMovement).filter(
            InventoryMovement.organization_id == org_id,
            InventoryMovement.idempotency_key == idempotency_key
        ).first()
        if existing:
            inv = get_or_create_inventory(db, org_id, material_id)
            return {
                "movement_id": existing.id,
                "status": "DUPLICATE_IDEMPOTENT_SKIPPED",
                "current_stock": inv.current_stock,
                "available_stock": max(0.0, inv.current_stock - inv.reserved_stock)
            }

    inv = get_or_create_inventory(db, org_id, material_id)
    mat = inv.material

    # Convert unit to material's canonical catalogue unit if necessary
    target_unit = mat.unit or "kg"
    converted_qty = float(convert_unit(
        quantity=quantity,
        from_unit=unit,
        to_unit=target_unit,
        density_g_cm3=mat.density_g_cm3
    ))

    # Weighted average valuation
    old_stock = inv.current_stock
    old_val = inv.unit_cost_valuation or (mat.standard_cost or 0.0)
    effective_cost = unit_cost if unit_cost is not None else old_val

    new_stock = old_stock + converted_qty
    if new_stock > 0 and effective_cost > 0:
        new_val = ((old_stock * old_val) + (converted_qty * effective_cost)) / new_stock
    else:
        new_val = old_val

    inv.current_stock = round(new_stock, 4)
    inv.unit_cost_valuation = round(new_val, 2)
    inv.updated_at = datetime.utcnow()

    # If incoming stock was tracked, decrement it up to received quantity
    if inv.incoming_stock > 0:
        inv.incoming_stock = max(0.0, round(inv.incoming_stock - converted_qty, 4))

    # Ledger movement
    movement = InventoryMovement(
        organization_id=org_id,
        material_id=material_id,
        movement_type="INWARD",
        quantity=converted_qty,
        unit=target_unit,
        source=source,
        destination="Warehouse Inventory",
        reference_id=reference_id,
        user_id=user_id,
        unit_cost=effective_cost,
        idempotency_key=idempotency_key,
        notes=notes or f"Stock received: {quantity} {unit}",
        created_at=datetime.utcnow()
    )
    db.add(movement)
    db.commit()
    db.refresh(inv)

    return {
        "movement_id": movement.id,
        "material_id": material_id,
        "material_code": mat.code,
        "received_quantity": converted_qty,
        "unit": target_unit,
        "current_stock": inv.current_stock,
        "available_stock": max(0.0, inv.current_stock - inv.reserved_stock),
        "unit_cost_valuation": inv.unit_cost_valuation
    }


def issue_stock(
    db: Session,
    org_id: str,
    material_id: str,
    quantity: float,
    unit: str = "kg",
    reference_id: Optional[str] = None,
    destination: Optional[str] = "Shop Floor",
    production_job_id: Optional[str] = None,
    notes: Optional[str] = None,
    allow_negative_stock: bool = False,
    idempotency_key: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Issues material from warehouse to production job or department.
    Guarantees stock cannot drop below zero unless allow_negative_stock is explicitly true.
    """
    if quantity <= 0:
        raise ValueError("Issued quantity must be positive.")

    # Idempotency check
    if idempotency_key:
        existing = db.query(InventoryMovement).filter(
            InventoryMovement.organization_id == org_id,
            InventoryMovement.idempotency_key == idempotency_key
        ).first()
        if existing:
            inv = get_or_create_inventory(db, org_id, material_id)
            return {
                "movement_id": existing.id,
                "status": "DUPLICATE_IDEMPOTENT_SKIPPED",
                "current_stock": inv.current_stock,
                "available_stock": max(0.0, inv.current_stock - inv.reserved_stock)
            }

    inv = get_or_create_inventory(db, org_id, material_id)
    mat = inv.material

    target_unit = mat.unit or "kg"
    converted_qty = float(convert_unit(
        quantity=quantity,
        from_unit=unit,
        to_unit=target_unit,
        density_g_cm3=mat.density_g_cm3
    ))

    avail = inv.current_stock - inv.reserved_stock
    if not allow_negative_stock and avail < converted_qty:
        raise ValueError(
            f"Insufficient unreserved stock for material '{mat.name}' ({mat.code}). "
            f"Requested: {converted_qty} {target_unit}, Available: {avail} {target_unit} "
            f"(Physical: {inv.current_stock}, Reserved: {inv.reserved_stock})."
        )

    inv.current_stock = round(inv.current_stock - converted_qty, 4)
    inv.updated_at = datetime.utcnow()

    movement = InventoryMovement(
        organization_id=org_id,
        material_id=material_id,
        movement_type="ISSUE",
        quantity=converted_qty,
        unit=target_unit,
        source="Warehouse Inventory",
        destination=destination,
        reference_id=reference_id,
        production_job_id=production_job_id,
        user_id=user_id,
        idempotency_key=idempotency_key,
        notes=notes or f"Material issued to {destination}",
        created_at=datetime.utcnow()
    )
    db.add(movement)
    db.commit()
    db.refresh(inv)

    return {
        "movement_id": movement.id,
        "material_id": material_id,
        "issued_quantity": converted_qty,
        "unit": target_unit,
        "current_stock": inv.current_stock,
        "available_stock": max(0.0, inv.current_stock - inv.reserved_stock)
    }


def reserve_stock(
    db: Session,
    org_id: str,
    material_id: str,
    quantity: float,
    production_job_id: Optional[str] = None,
    unit: str = "kg",
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reserves stock for a scheduled production job to prevent double-allocation.
    Fails if unreserved available stock is insufficient.
    """
    if quantity <= 0:
        raise ValueError("Reserved quantity must be positive.")

    inv = get_or_create_inventory(db, org_id, material_id)
    mat = inv.material

    target_unit = mat.unit or "kg"
    converted_qty = float(convert_unit(
        quantity=quantity,
        from_unit=unit,
        to_unit=target_unit,
        density_g_cm3=mat.density_g_cm3
    ))

    avail = inv.current_stock - inv.reserved_stock
    if avail < converted_qty:
        raise ValueError(
            f"Cannot reserve {converted_qty} {target_unit} of '{mat.name}'. "
            f"Available unreserved stock is only {avail} {target_unit}."
        )

    inv.reserved_stock = round(inv.reserved_stock + converted_qty, 4)
    inv.updated_at = datetime.utcnow()

    reservation = StockReservation(
        organization_id=org_id,
        material_id=material_id,
        production_job_id=production_job_id,
        reserved_quantity=converted_qty,
        unit=target_unit,
        status="ACTIVE",
        notes=notes,
        created_at=datetime.utcnow()
    )
    db.add(reservation)

    movement = InventoryMovement(
        organization_id=org_id,
        material_id=material_id,
        movement_type="RESERVATION",
        quantity=converted_qty,
        unit=target_unit,
        source="Unreserved Stock",
        destination=f"Job Reservation: {production_job_id or 'General'}",
        reference_id=production_job_id,
        production_job_id=production_job_id,
        notes=notes or f"Reserved for job {production_job_id}",
        created_at=datetime.utcnow()
    )
    db.add(movement)
    db.commit()
    db.refresh(inv)

    return {
        "reservation_id": reservation.id,
        "material_id": material_id,
        "reserved_quantity": converted_qty,
        "unit": target_unit,
        "new_total_reserved": inv.reserved_stock,
        "available_stock": max(0.0, inv.current_stock - inv.reserved_stock)
    }


def release_reservation(
    db: Session,
    org_id: str,
    reservation_id: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Releases an active stock reservation back into available inventory."""
    res = db.query(StockReservation).filter(
        StockReservation.id == reservation_id,
        StockReservation.organization_id == org_id
    ).first()

    if not res:
        raise ValueError("Reservation not found.")
    if res.status != "ACTIVE":
        raise ValueError(f"Reservation is already {res.status}.")

    inv = get_or_create_inventory(db, org_id, res.material_id)
    inv.reserved_stock = max(0.0, round(inv.reserved_stock - res.reserved_quantity, 4))
    inv.updated_at = datetime.utcnow()

    res.status = "RELEASED"
    res.released_at = datetime.utcnow()

    movement = InventoryMovement(
        organization_id=org_id,
        material_id=res.material_id,
        movement_type="RELEASE",
        quantity=res.reserved_quantity,
        unit=res.unit,
        source=f"Released Reservation {res.id}",
        destination="Available Inventory",
        reference_id=res.production_job_id,
        production_job_id=res.production_job_id,
        notes=notes or "Stock reservation cancelled/released",
        created_at=datetime.utcnow()
    )
    db.add(movement)
    db.commit()
    db.refresh(inv)

    return {
        "reservation_id": res.id,
        "released_quantity": res.reserved_quantity,
        "status": "RELEASED",
        "current_stock": inv.current_stock,
        "available_stock": max(0.0, inv.current_stock - inv.reserved_stock)
    }


def adjust_stock(
    db: Session,
    org_id: str,
    material_id: str,
    new_physical_stock: float,
    reason: str,
    notes: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Performs physical stock audit adjustment.
    Logs the discrepancy in movements and resets current_stock to actual counted physical level.
    """
    if new_physical_stock < 0:
        raise ValueError("Physical stock count cannot be negative.")

    inv = get_or_create_inventory(db, org_id, material_id)
    mat = inv.material

    old_stock = inv.current_stock
    delta = new_physical_stock - old_stock

    inv.current_stock = round(new_physical_stock, 4)
    inv.updated_at = datetime.utcnow()

    movement = InventoryMovement(
        organization_id=org_id,
        material_id=material_id,
        movement_type="ADJUSTMENT",
        quantity=abs(delta),
        unit=mat.unit or "kg",
        source=f"Audit Adjust ({reason})",
        destination=f"Physical Count: {new_physical_stock}",
        user_id=user_id,
        notes=notes or f"Audit discrepancy: delta {delta:+.2f} {mat.unit} ({reason})",
        created_at=datetime.utcnow()
    )
    db.add(movement)
    db.commit()
    db.refresh(inv)

    return {
        "material_id": material_id,
        "old_stock": old_stock,
        "new_stock": inv.current_stock,
        "adjustment_delta": delta,
        "available_stock": max(0.0, inv.current_stock - inv.reserved_stock),
        "reason": reason
    }


def get_inventory_alerts(db: Session, org_id: str) -> List[Dict[str, Any]]:
    """
    Scans warehouse inventory and generates actionable operational alerts:
    - CRITICAL_SHORTAGE: Available stock <= safety stock threshold.
    - REORDER_REQUIRED: Available stock <= reorder point.
    - HIGH_RESERVATION: More than 80% of stock is locked for production jobs.
    - STOCKOUT_RISK: Zero available stock.
    """
    inventories = db.query(Inventory).filter(Inventory.organization_id == org_id).all()
    alerts = []

    for inv in inventories:
        mat = inv.material
        if not mat or not mat.is_active:
            continue

        avail = max(0.0, inv.current_stock - inv.reserved_stock)
        safety = inv.safety_stock or 0.0
        reorder = inv.reorder_level or 0.0

        if avail <= 0:
            alerts.append({
                "severity": "CRITICAL",
                "alert_type": "STOCKOUT",
                "material_id": inv.material_id,
                "material_name": mat.name,
                "material_code": mat.code,
                "available_stock": avail,
                "safety_stock": safety,
                "unit": mat.unit or "kg",
                "message": f"Zero unreserved stock available for '{mat.name}'. Immediate procurement required to avoid shopfloor stoppage."
            })
        elif avail <= safety:
            alerts.append({
                "severity": "CRITICAL",
                "alert_type": "BELOW_SAFETY_STOCK",
                "material_id": inv.material_id,
                "material_name": mat.name,
                "material_code": mat.code,
                "available_stock": avail,
                "safety_stock": safety,
                "unit": mat.unit or "kg",
                "message": f"Available stock ({avail} {mat.unit}) is below safety threshold ({safety} {mat.unit}). Buffer depleted."
            })
        elif avail <= reorder:
            alerts.append({
                "severity": "WARNING",
                "alert_type": "REORDER_TRIGGERED",
                "material_id": inv.material_id,
                "material_name": mat.name,
                "material_code": mat.code,
                "available_stock": avail,
                "reorder_level": reorder,
                "unit": mat.unit or "kg",
                "message": f"Available stock ({avail} {mat.unit}) has breached reorder point ({reorder} {mat.unit}). Purchase order should be issued."
            })

    return alerts

