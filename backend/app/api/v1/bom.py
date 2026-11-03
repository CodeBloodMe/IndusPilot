from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_org_id
from app.models.entities import Product, BillOfMaterials, BOMItem, Inventory, Material
from app.schemas.domain import BOMCreate, BOMRevisionRequest, BOMExplodeRequest
from app.calculations.bom_engine import explode_bom
from app.calculations.inventory_netting import calculate_net_procurement_requirement
from app.services.bom_service import validate_bom_items, create_bom_revision, compare_bom_revisions

router = APIRouter()


@router.get("/products")
def list_products_compat(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Backward compatibility alias for list products."""
    products = db.query(Product).filter(Product.organization_id == org_id).all()
    results = []
    for p in products:
        active_bom = next((b for b in p.boms if b.is_active), None)
        item_count = len(active_bom.items) if active_bom else 0
        results.append({
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "category": p.category,
            "description": p.description,
            "manufacturing_process": p.manufacturing_process,
            "base_unit": p.base_unit or "units",
            "default_batch_size": p.default_batch_size or 500.0,
            "active_bom_id": active_bom.id if active_bom else None,
            "active_bom_version": active_bom.version if active_bom else None,
            "components_count": item_count
        })
    return results


@router.get("")
def list_boms(
    product_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    query = db.query(BillOfMaterials).filter(BillOfMaterials.organization_id == org_id)
    if product_id:
        query = query.filter(BillOfMaterials.product_id == product_id)
    if is_active is not None:
        query = query.filter(BillOfMaterials.is_active == is_active)

    boms = query.order_by(BillOfMaterials.created_at.desc()).all()
    results = []
    for b in boms:
        p = b.product
        results.append({
            "id": b.id,
            "product_id": b.product_id,
            "product_name": p.name if p else "Unknown Product",
            "product_code": p.code if p else "",
            "name": b.name,
            "version": b.version,
            "revision_status": b.revision_status,
            "is_active": b.is_active,
            "batch_quantity": b.batch_quantity,
            "scrap_allowance_method": b.scrap_allowance_method,
            "expected_yield_pct": b.expected_yield_pct,
            "components_count": len(b.items),
            "effective_date": b.effective_date.isoformat() if b.effective_date else None,
            "created_at": b.created_at.isoformat() if b.created_at else None
        })
    return results


@router.post("", status_code=201)
def create_bom(
    payload: BOMCreate,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Creates a new Bill of Materials.
    Supports either linking to an existing product_id or auto-creating product via product_name/code.
    Validates components against catalogue and engineering constraints.
    """
    prod_id = payload.product_id
    if not prod_id:
        if not payload.product_code or not payload.product_name:
            raise HTTPException(status_code=400, detail="Must provide either product_id or (product_name and product_code).")
        # Check or create product
        prod = db.query(Product).filter(
            Product.organization_id == org_id,
            Product.code.ilike(payload.product_code.strip())
        ).first()
        if not prod:
            prod = Product(
                organization_id=org_id,
                code=payload.product_code.strip(),
                name=payload.product_name.strip(),
                category=payload.category,
                description=payload.description,
                created_at=datetime.utcnow()
            )
            db.add(prod)
            db.flush()
        prod_id = prod.id
    else:
        prod = db.query(Product).filter(Product.id == prod_id, Product.organization_id == org_id).first()
        if not prod:
            raise HTTPException(status_code=404, detail="Specified product_id not found.")

    # Validate items
    items_raw = [it.model_dump() for it in payload.items]
    is_valid, errors, warnings = validate_bom_items(db, org_id, items_raw)
    if not is_valid:
        raise HTTPException(status_code=422, detail={"message": "BOM validation failed.", "errors": errors, "warnings": warnings})

    # Deactivate existing active BOM for product if this one is active
    existing_boms = db.query(BillOfMaterials).filter(
        BillOfMaterials.product_id == prod_id,
        BillOfMaterials.organization_id == org_id
    ).all()
    for eb in existing_boms:
        eb.is_active = False
        eb.revision_status = "SUPERSEDED"

    bom = BillOfMaterials(
        organization_id=org_id,
        product_id=prod_id,
        name=payload.name,
        version=payload.version,
        effective_date=datetime.utcnow(),
        revision_status="ACTIVE",
        is_active=True,
        batch_quantity=payload.batch_quantity,
        scrap_allowance_method=payload.scrap_allowance_method,
        expected_yield_pct=payload.expected_yield_pct,
        notes=payload.notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(bom)
    db.flush()

    for it in payload.items:
        bi = BOMItem(
            bom_id=bom.id,
            material_id=it.material_id,
            quantity_per_unit=it.quantity_per_unit,
            unit=it.unit,
            wastage_pct=it.wastage_pct,
            scrap_allowance_method=it.scrap_allowance_method,
            expected_yield_pct=it.expected_yield_pct,
            process_stage=it.process_stage,
            notes=it.notes
        )
        db.add(bi)

    db.commit()
    db.refresh(bom)

    return {
        "id": bom.id,
        "product_id": bom.product_id,
        "product_name": prod.name,
        "version": bom.version,
        "revision_status": bom.revision_status,
        "is_active": bom.is_active,
        "components_count": len(bom.items),
        "warnings": warnings,
        "created_at": bom.created_at.isoformat()
    }


@router.get("/compare")
def compare_boms(
    bom1: str = Query(..., description="First BOM revision ID"),
    bom2: str = Query(..., description="Second BOM revision ID"),
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Compares two BOM revisions side-by-side with item-level diffs."""
    try:
        diff = compare_bom_revisions(db, org_id, bom1, bom2)
        return diff
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/details/{bom_id}")
def get_bom_details(
    bom_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    bom = db.query(BillOfMaterials).filter(
        BillOfMaterials.id == bom_id,
        BillOfMaterials.organization_id == org_id
    ).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found.")

    p = bom.product
    items = []
    for it in bom.items:
        m = it.material
        items.append({
            "id": it.id,
            "material_id": it.material_id,
            "material_name": m.name if m else "Unknown",
            "material_code": m.code if m else "",
            "grade": m.grade if m else "",
            "quantity_per_unit": it.quantity_per_unit,
            "unit": it.unit,
            "wastage_pct": it.wastage_pct,
            "scrap_allowance_method": it.scrap_allowance_method,
            "expected_yield_pct": it.expected_yield_pct,
            "process_stage": it.process_stage,
            "notes": it.notes
        })

    return {
        "id": bom.id,
        "product_id": bom.product_id,
        "product_name": p.name if p else "Product",
        "product_code": p.code if p else "",
        "name": bom.name,
        "version": bom.version,
        "revision_status": bom.revision_status,
        "is_active": bom.is_active,
        "batch_quantity": bom.batch_quantity,
        "scrap_allowance_method": bom.scrap_allowance_method,
        "expected_yield_pct": bom.expected_yield_pct,
        "items": items,
        "created_at": bom.created_at.isoformat() if bom.created_at else None
    }


@router.post("/{bom_id}/revisions")
def create_revision_endpoint(
    bom_id: str,
    payload: BOMRevisionRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Creates a new BOM revision from an existing BOM, archiving the old version."""
    items_raw = [it.model_dump() for it in payload.items] if payload.items else None
    if items_raw:
        is_valid, errors, _ = validate_bom_items(db, org_id, items_raw)
        if not is_valid:
            raise HTTPException(status_code=422, detail={"message": "Invalid items in revision.", "errors": errors})

    try:
        new_bom = create_bom_revision(
            db=db,
            org_id=org_id,
            original_bom_id=bom_id,
            new_version_label=payload.new_version,
            revision_notes=payload.revision_notes,
            updated_items=items_raw
        )
        return {
            "id": new_bom.id,
            "product_id": new_bom.product_id,
            "version": new_bom.version,
            "revision_status": new_bom.revision_status,
            "components_count": len(new_bom.items),
            "created_at": new_bom.created_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{bom_id}/validate")
def validate_bom_endpoint(
    bom_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Validates an existing BOM against current material catalog data."""
    bom = db.query(BillOfMaterials).filter(
        BillOfMaterials.id == bom_id,
        BillOfMaterials.organization_id == org_id
    ).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found.")

    items_raw = [
        {
            "material_id": it.material_id,
            "quantity_per_unit": it.quantity_per_unit,
            "unit": it.unit,
            "wastage_pct": it.wastage_pct,
            "scrap_allowance_method": it.scrap_allowance_method,
            "expected_yield_pct": it.expected_yield_pct
        }
        for it in bom.items
    ]
    is_valid, errors, warnings = validate_bom_items(db, org_id, items_raw)
    return {
        "bom_id": bom.id,
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "components_count": len(bom.items)
    }


@router.get("/{product_id}")
def get_product_active_bom(
    product_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves the active BOM for a product."""
    product = db.query(Product).filter(Product.id == product_id, Product.organization_id == org_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    active_bom = next((b for b in product.boms if b.is_active), None)
    items = []
    if active_bom:
        for it in active_bom.items:
            m = it.material
            items.append({
                "id": it.id,
                "material_id": it.material_id,
                "material_name": m.name if m else "Unknown",
                "material_code": m.code if m else "",
                "grade": m.grade if m else "",
                "quantity_per_unit": it.quantity_per_unit,
                "unit": it.unit,
                "wastage_pct": it.wastage_pct,
                "scrap_allowance_method": it.scrap_allowance_method,
                "expected_yield_pct": it.expected_yield_pct,
                "process_stage": it.process_stage,
                "notes": it.notes
            })

    return {
        "product_id": product.id,
        "product_name": product.name,
        "product_code": product.code,
        "bom_id": active_bom.id if active_bom else None,
        "version": active_bom.version if active_bom else "None",
        "items": items
    }


@router.post("/explode")
def explode_product_bom(
    payload: BOMExplodeRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Explodes the Bill of Materials for a specific production quantity,
    calculates scrap/wastage (additive or yield-based), and nets the requirement against current warehouse stock.
    """
    raw_items = []
    product_info = {"id": None, "name": "Custom BOM", "code": "CUSTOM"}

    if payload.product_id:
        p_key = str(payload.product_id).strip()
        alias_map = {"SS304-BRK-500": "IND-BRK-SS304", "BRK-SS-304": "IND-BRK-SS304"}
        canonical_code = alias_map.get(p_key, p_key)
        product = db.query(Product).filter(
            (Product.id == p_key) | (Product.code == p_key) | (Product.code == canonical_code),
            Product.organization_id == org_id
        ).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found.")
        product_info = {"id": product.id, "name": product.name, "code": product.code}

        if payload.bom_id:
            target_bom = db.query(BillOfMaterials).filter(
                BillOfMaterials.id == payload.bom_id,
                BillOfMaterials.product_id == product.id
            ).first()
        else:
            target_bom = next((b for b in product.boms if b.is_active), None)

        if not target_bom or not target_bom.items:
            raise HTTPException(status_code=400, detail="Product does not have an active Bill of Materials.")

        for it in target_bom.items:
            m = it.material
            raw_items.append({
                "material_id": it.material_id,
                "material_name": m.name if m else "Material",
                "material_code": m.code if m else "",
                "grade": m.grade if m else "",
                "quantity_per_unit": it.quantity_per_unit,
                "unit": it.unit,
                "wastage_pct": it.wastage_pct,
                "scrap_allowance_method": it.scrap_allowance_method,
                "expected_yield_pct": it.expected_yield_pct,
                "process_stage": it.process_stage
            })
    elif payload.custom_items:
        for c in payload.custom_items:
            m = db.query(Material).filter(Material.id == c.material_id).first()
            raw_items.append({
                "material_id": c.material_id,
                "material_name": m.name if m else "Material",
                "material_code": m.code if m else "",
                "grade": m.grade if m else "",
                "quantity_per_unit": c.quantity_per_unit,
                "unit": c.unit,
                "wastage_pct": c.wastage_pct,
                "scrap_allowance_method": c.scrap_allowance_method,
                "expected_yield_pct": c.expected_yield_pct,
                "process_stage": c.process_stage
            })
    else:
        raise HTTPException(status_code=400, detail="Must provide either product_id or custom_items.")

    bom_summary = explode_bom(payload.production_quantity, raw_items)

    # Net against active warehouse inventory for each component
    annotated_components = []
    shortage_count = 0
    total_shortage_mass_kg = 0.0

    for comp in bom_summary["components"]:
        mat_id = comp["material_id"]
        inv = db.query(Inventory).filter(Inventory.material_id == mat_id, Inventory.organization_id == org_id).first()
        cur_stock = inv.current_stock if inv else 0.0
        res_stock = inv.reserved_stock if inv else 0.0
        inc_stock = inv.incoming_stock if inv else 0.0
        saf_stock = inv.safety_stock if inv else 0.0

        netting = calculate_net_procurement_requirement(
            gross_requirement=comp["total_gross_required"],
            current_stock=cur_stock,
            reserved_stock=res_stock,
            incoming_stock=inc_stock,
            safety_stock=saf_stock
        )
        comp["inventory_status"] = netting
        if netting["has_shortage"]:
            shortage_count += 1
            if comp["unit"] == "kg":
                total_shortage_mass_kg += netting["net_shortage"]

        annotated_components.append(comp)

    return {
        "product": product_info,
        "production_quantity": payload.production_quantity,
        "components_count": len(annotated_components),
        "shortages_count": shortage_count,
        "total_raw_mass_kg": bom_summary["total_raw_mass_kg"],
        "total_shortage_mass_kg": round(total_shortage_mass_kg, 2),
        "components": annotated_components
    }
