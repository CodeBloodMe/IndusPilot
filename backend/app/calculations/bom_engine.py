from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional
from app.services.unit_conversion import normalize_unit_str

def round_qty(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def calculate_component_requirement(
    quantity_per_unit: float | Decimal,
    production_quantity: float | Decimal,
    wastage_pct: float | Decimal = 5.0,
    scrap_method: str = "ADDITIVE_SCRAP", # "ADDITIVE_SCRAP" or "YIELD_BASED"
    expected_yield_pct: float | Decimal = 95.0,
) -> Dict[str, Decimal]:
    """
    Computes exact net, gross, and scrap quantities for a single BOM line item.
    
    Methods:
    1. ADDITIVE_SCRAP:
       Gross = Net * (1 + Scrap% / 100)
       Scrap = Gross - Net
    2. YIELD_BASED:
       Gross = Net / (Yield% / 100)
       Scrap = Gross - Net
    """
    q_unit = Decimal(str(quantity_per_unit))
    p_qty = Decimal(str(production_quantity))
    
    if q_unit <= Decimal("0.0"):
        raise ValueError("Component quantity per unit must be strictly positive.")
    if p_qty <= Decimal("0.0"):
        raise ValueError("Production quantity must be strictly positive.")

    total_net = q_unit * p_qty

    method = scrap_method.upper().strip() if scrap_method else "ADDITIVE_SCRAP"
    if method == "YIELD_BASED":
        y_pct = Decimal(str(expected_yield_pct))
        if y_pct <= Decimal("0.0") or y_pct > Decimal("100.0"):
            raise ValueError("Expected yield percentage must be between 0.1% and 100%.")
        yield_rate = y_pct / Decimal("100.0")
        gross_per_unit = q_unit / yield_rate
        total_gross = total_net / yield_rate
        total_scrap = total_gross - total_net
    else: # ADDITIVE_SCRAP default
        w_pct = Decimal(str(wastage_pct))
        if w_pct < Decimal("0.0") or w_pct > Decimal("100.0"):
            raise ValueError("Scrap wastage percentage must be between 0% and 100%.")
        scrap_multiplier = Decimal("1.0") + (w_pct / Decimal("100.0"))
        gross_per_unit = q_unit * scrap_multiplier
        total_gross = total_net * scrap_multiplier
        total_scrap = total_gross - total_net

    return {
        "net_per_unit": round_qty(q_unit),
        "gross_per_unit": round_qty(gross_per_unit),
        "total_net": round_qty(total_net),
        "total_scrap": round_qty(total_scrap),
        "total_gross": round_qty(total_gross),
    }


def explode_bom(
    production_quantity: float | Decimal,
    bom_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Calculates gross material requirements across all BOM line items
    incorporating scrap/wastage allowances or yield rates.
    """
    prod_qty = Decimal(str(production_quantity))
    if prod_qty <= 0:
        raise ValueError("Production quantity must be positive.")

    calculated_components = []
    total_raw_mass_kg = Decimal("0.0")

    for item in bom_items:
        qty_unit = item.get("quantity_per_unit", 1.0)
        wastage_pct = item.get("wastage_pct", 5.0)
        scrap_method = item.get("scrap_allowance_method", "ADDITIVE_SCRAP")
        yield_pct = item.get("expected_yield_pct", 95.0)
        unit = normalize_unit_str(item.get("unit", "kg"))

        calc = calculate_component_requirement(
            quantity_per_unit=qty_unit,
            production_quantity=prod_qty,
            wastage_pct=wastage_pct,
            scrap_method=scrap_method,
            expected_yield_pct=yield_pct
        )

        if unit == "kg":
            total_raw_mass_kg += calc["total_gross"]

        calculated_components.append({
            "material_id": item.get("material_id"),
            "material_name": item.get("material_name", "Raw Material"),
            "material_code": item.get("material_code", ""),
            "grade": item.get("grade", ""),
            "unit": unit,
            "scrap_allowance_method": scrap_method,
            "wastage_pct": float(wastage_pct) if scrap_method != "YIELD_BASED" else None,
            "expected_yield_pct": float(yield_pct) if scrap_method == "YIELD_BASED" else None,
            "net_quantity_per_unit": float(calc["net_per_unit"]),
            "gross_quantity_per_unit": float(calc["gross_per_unit"]),
            "total_net_required": float(calc["total_net"]),
            "total_wastage_scrap": float(calc["total_scrap"]),
            "total_gross_required": float(calc["total_gross"]),
            "process_stage": item.get("process_stage", "Primary Processing"),
        })

    return {
        "production_quantity": float(round_qty(prod_qty)),
        "total_components_count": len(calculated_components),
        "total_raw_mass_kg": float(round_qty(total_raw_mass_kg)),
        "components": calculated_components
    }


def aggregate_material_requirements(
    requirements_list: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Aggregates material requirements across multiple BOM explosions or production orders.
    Groups by: (material_id, grade, unit).
    Guarantees incompatible grades or units are never aggregated together.
    """
    aggregated: Dict[str, Dict[str, Any]] = {}

    for req in requirements_list:
        mat_id = str(req.get("material_id", "UNKNOWN"))
        grade = str(req.get("grade", "")).strip().upper()
        unit = normalize_unit_str(req.get("unit", "kg"))
        order_ref = req.get("order_ref") or req.get("job_number") or "DEFAULT"

        # Unique key for exact compatibility
        group_key = f"{mat_id}:{grade}:{unit}"

        net = Decimal(str(req.get("total_net_required", 0.0)))
        gross = Decimal(str(req.get("total_gross_required", 0.0)))
        scrap = Decimal(str(req.get("total_wastage_scrap", 0.0)))

        if group_key not in aggregated:
            aggregated[group_key] = {
                "material_id": mat_id,
                "material_name": req.get("material_name", "Material"),
                "material_code": req.get("material_code", ""),
                "grade": grade,
                "unit": unit,
                "total_net_required": Decimal("0.0"),
                "total_wastage_scrap": Decimal("0.0"),
                "total_gross_required": Decimal("0.0"),
                "order_references": set(),
                "components_count": 0,
            }

        aggregated[group_key]["total_net_required"] += net
        aggregated[group_key]["total_gross_required"] += gross
        aggregated[group_key]["total_wastage_scrap"] += scrap
        aggregated[group_key]["order_references"].add(order_ref)
        aggregated[group_key]["components_count"] += 1

    results = []
    for g in aggregated.values():
        results.append({
            "material_id": g["material_id"],
            "material_name": g["material_name"],
            "material_code": g["material_code"],
            "grade": g["grade"],
            "unit": g["unit"],
            "total_net_required": float(round_qty(g["total_net_required"])),
            "total_wastage_scrap": float(round_qty(g["total_wastage_scrap"])),
            "total_gross_required": float(round_qty(g["total_gross_required"])),
            "order_references": list(g["order_references"]),
            "orders_count": len(g["order_references"]),
            "contributing_components_count": g["components_count"],
        })

    return results
