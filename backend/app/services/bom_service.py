"""
IndusPilot BOM Management & Validation Service
Handles BOM creation, revisions, duplication, validation, and multi-version comparison.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.entities import Product, BillOfMaterials, BOMItem, Material
from app.services.unit_conversion import get_unit_dimension, normalize_unit_str, UnitDimension


def validate_bom_items(
    db: Session,
    org_id: str,
    items_data: List[Dict[str, Any]],
) -> Tuple[bool, List[str], List[str]]:
    """
    Validates BOM components against business and engineering constraints:
    - Material existence & active status
    - Unit compatibility
    - Positive quantities
    - Duplicate component detection
    - Scrap percentage / yield boundaries (0-100%)
    
    Returns: (is_valid, errors, warnings)
    """
    errors: List[str] = []
    warnings: List[str] = []
    seen_material_ids = set()

    if not items_data:
        errors.append("BOM must contain at least one material component.")
        return False, errors, warnings

    for idx, it in enumerate(items_data):
        pos = idx + 1
        mat_id = it.get("material_id")
        if not mat_id:
            errors.append(f"Component #{pos}: material_id is required.")
            continue

        # Check duplicate materials in same BOM
        if mat_id in seen_material_ids:
            errors.append(f"Component #{pos}: Duplicate material reference (ID: {mat_id}) in BOM. Combine quantities into a single component.")
        seen_material_ids.add(mat_id)

        # Check material in database
        mat = db.query(Material).filter(Material.id == mat_id, Material.organization_id == org_id).first()
        if not mat:
            errors.append(f"Component #{pos}: Material with ID '{mat_id}' does not exist.")
            continue
        if not mat.is_active:
            errors.append(f"Component #{pos}: Material '{mat.name}' ({mat.code}) is INACTIVE in catalogue.")

        # Quantity positive check
        qty = it.get("quantity_per_unit", 0)
        try:
            qty_val = float(qty)
            if qty_val <= 0:
                errors.append(f"Component #{pos} ({mat.name}): Quantity per unit must be strictly positive (got {qty_val}).")
        except (ValueError, TypeError):
            errors.append(f"Component #{pos} ({mat.name}): Invalid quantity value '{qty}'.")

        # Unit compatibility check
        bom_unit = normalize_unit_str(it.get("unit", mat.unit or "kg"))
        mat_unit = normalize_unit_str(mat.unit or "kg")
        bom_dim = get_unit_dimension(bom_unit)
        mat_dim = get_unit_dimension(mat_unit)

        if bom_dim != mat_dim and bom_dim != UnitDimension.UNKNOWN and mat_dim != UnitDimension.UNKNOWN:
            # Cross-dimensional unit requires density/thickness
            if not mat.density_g_cm3:
                warnings.append(
                    f"Component #{pos} ({mat.name}): BOM unit '{bom_unit}' ({bom_dim.value}) differs from catalogue unit "
                    f"'{mat_unit}' ({mat_dim.value}). Density metadata is missing on material."
                )

        # Scrap / Yield validation
        scrap_method = it.get("scrap_allowance_method", "ADDITIVE_SCRAP")
        if scrap_method == "YIELD_BASED":
            yield_pct = float(it.get("expected_yield_pct", 95.0))
            if yield_pct <= 0 or yield_pct > 100:
                errors.append(f"Component #{pos} ({mat.name}): Expected yield percentage must be between 0.1% and 100% (got {yield_pct}%).")
        else:
            scrap_pct = float(it.get("wastage_pct", 5.0))
            if scrap_pct < 0 or scrap_pct > 100:
                errors.append(f"Component #{pos} ({mat.name}): Scrap wastage percentage must be between 0% and 100% (got {scrap_pct}%).")
            elif scrap_pct > 25.0:
                warnings.append(f"Component #{pos} ({mat.name}): Unusually high scrap allowance ({scrap_pct}%). Standard fabrication range is 3% - 15%.")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def create_bom_revision(
    db: Session,
    org_id: str,
    original_bom_id: str,
    new_version_label: str,
    revision_notes: Optional[str] = None,
    updated_items: Optional[List[Dict[str, Any]]] = None,
) -> BillOfMaterials:
    """
    Creates a new BOM revision while preserving the original historical revision.
    Archives previous active BOM and sets the new revision as ACTIVE.
    """
    orig_bom = db.query(BillOfMaterials).filter(
        BillOfMaterials.id == original_bom_id,
        BillOfMaterials.organization_id == org_id
    ).first()

    if not orig_bom:
        raise ValueError("Original BOM not found.")

    # Archive previous revision
    orig_bom.is_active = False
    orig_bom.revision_status = "SUPERSEDED"
    orig_bom.updated_at = datetime.utcnow()

    # Create new revision
    new_bom = BillOfMaterials(
        organization_id=org_id,
        product_id=orig_bom.product_id,
        name=orig_bom.name,
        version=new_version_label,
        effective_date=datetime.utcnow(),
        revision_status="ACTIVE",
        is_active=True,
        batch_quantity=orig_bom.batch_quantity,
        scrap_allowance_method=orig_bom.scrap_allowance_method,
        expected_yield_pct=orig_bom.expected_yield_pct,
        notes=revision_notes or f"Revision created from {orig_bom.version}",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_bom)
    db.flush()

    # If updated items provided, use them; otherwise duplicate original items
    items_source = updated_items if updated_items is not None else [
        {
            "material_id": it.material_id,
            "quantity_per_unit": it.quantity_per_unit,
            "unit": it.unit,
            "wastage_pct": it.wastage_pct,
            "scrap_allowance_method": it.scrap_allowance_method,
            "expected_yield_pct": it.expected_yield_pct,
            "process_stage": it.process_stage,
            "notes": it.notes
        }
        for it in orig_bom.items
    ]

    for it_data in items_source:
        item = BOMItem(
            bom_id=new_bom.id,
            material_id=it_data["material_id"],
            quantity_per_unit=it_data["quantity_per_unit"],
            unit=it_data.get("unit", "kg"),
            wastage_pct=it_data.get("wastage_pct", 5.0),
            scrap_allowance_method=it_data.get("scrap_allowance_method", "ADDITIVE_SCRAP"),
            expected_yield_pct=it_data.get("expected_yield_pct", 95.0),
            process_stage=it_data.get("process_stage", "Cutting & Forming"),
            notes=it_data.get("notes")
        )
        db.add(item)

    db.commit()
    db.refresh(new_bom)
    return new_bom


def compare_bom_revisions(
    db: Session,
    org_id: str,
    bom_id_1: str,
    bom_id_2: str,
) -> Dict[str, Any]:
    """
    Compares two BOM revisions side-by-side:
    - Identifies added, removed, and modified materials.
    - Computes material quantity deltas and scrap rate differences.
    """
    bom1 = db.query(BillOfMaterials).filter(BillOfMaterials.id == bom_id_1, BillOfMaterials.organization_id == org_id).first()
    bom2 = db.query(BillOfMaterials).filter(BillOfMaterials.id == bom_id_2, BillOfMaterials.organization_id == org_id).first()

    if not bom1 or not bom2:
        raise ValueError("One or both BOM revisions could not be found.")

    items1_map = {it.material_id: it for it in bom1.items}
    items2_map = {it.material_id: it for it in bom2.items}

    all_mat_ids = set(items1_map.keys()) | set(items2_map.keys())

    differences = []
    for mat_id in all_mat_ids:
        it1 = items1_map.get(mat_id)
        it2 = items2_map.get(mat_id)
        mat = db.query(Material).filter(Material.id == mat_id).first()
        mat_name = mat.name if mat else "Unknown Material"
        mat_code = mat.code if mat else ""

        if it1 and not it2:
            differences.append({
                "material_id": mat_id,
                "material_name": mat_name,
                "material_code": mat_code,
                "change_type": "REMOVED",
                "old_quantity": it1.quantity_per_unit,
                "new_quantity": 0.0,
                "unit": it1.unit,
                "old_wastage_pct": it1.wastage_pct,
                "new_wastage_pct": 0.0,
            })
        elif not it1 and it2:
            differences.append({
                "material_id": mat_id,
                "material_name": mat_name,
                "material_code": mat_code,
                "change_type": "ADDED",
                "old_quantity": 0.0,
                "new_quantity": it2.quantity_per_unit,
                "unit": it2.unit,
                "old_wastage_pct": 0.0,
                "new_wastage_pct": it2.wastage_pct,
            })
        else: # Both exist
            qty_delta = it2.quantity_per_unit - it1.quantity_per_unit
            waste_delta = (it2.wastage_pct or 0.0) - (it1.wastage_pct or 0.0)
            status = "MODIFIED" if abs(qty_delta) > 0.0001 or abs(waste_delta) > 0.0001 else "UNCHANGED"
            differences.append({
                "material_id": mat_id,
                "material_name": mat_name,
                "material_code": mat_code,
                "change_type": status,
                "old_quantity": it1.quantity_per_unit,
                "new_quantity": it2.quantity_per_unit,
                "quantity_delta": round(qty_delta, 4),
                "unit": it2.unit,
                "old_wastage_pct": it1.wastage_pct,
                "new_wastage_pct": it2.wastage_pct,
                "wastage_delta": round(waste_delta, 2),
            })

    return {
        "bom_1": {"id": bom1.id, "version": bom1.version, "name": bom1.name, "created_at": bom1.created_at.isoformat() if bom1.created_at else None},
        "bom_2": {"id": bom2.id, "version": bom2.version, "name": bom2.name, "created_at": bom2.created_at.isoformat() if bom2.created_at else None},
        "components_count_bom1": len(bom1.items),
        "components_count_bom2": len(bom2.items),
        "differences": differences
    }

