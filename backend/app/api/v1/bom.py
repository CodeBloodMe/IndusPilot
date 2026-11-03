from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_org_id
from app.models.entities import Product, BillOfMaterials, BOMItem, Inventory, Material
from app.schemas.domain import BOMCreate, BOMExplodeRequest
from app.calculations.bom_engine import explode_bom
from app.calculations.inventory_netting import calculate_net_procurement_requirement

router = APIRouter()

@router.get("/products")
def list_products(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
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
            "active_bom_id": active_bom.id if active_bom else None,
            "active_bom_version": active_bom.version if active_bom else None,
            "components_count": item_count
        })
    return results

@router.get("/{product_id}")
def get_product_bom(
    product_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
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
    calculates scrap/wastage, and nets the requirement against current warehouse stock.
    """
    raw_items = []
    product_info = {"id": None, "name": "Custom BOM", "code": "CUSTOM"}

    if payload.product_id:
        product = db.query(Product).filter(Product.id == payload.product_id, Product.organization_id == org_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found.")
        product_info = {"id": product.id, "name": product.name, "code": product.code}
        active_bom = next((b for b in product.boms if b.is_active), None)
        if not active_bom or not active_bom.items:
            raise HTTPException(status_code=400, detail="Product does not have an active Bill of Materials.")
        for it in active_bom.items:
            m = it.material
            raw_items.append({
                "material_id": it.material_id,
                "material_name": m.name if m else "Material",
                "material_code": m.code if m else "",
                "grade": m.grade if m else "",
                "quantity_per_unit": it.quantity_per_unit,
                "unit": it.unit,
                "wastage_pct": it.wastage_pct,
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
                "process_stage": c.process_stage
            })
    else:
        raise HTTPException(status_code=400, detail="Must provide either product_id or custom_items.")

    bom_summary = explode_bom(payload.production_quantity, raw_items)

    # Net against active inventory for each component
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

