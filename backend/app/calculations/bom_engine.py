from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any

def round_qty(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

def explode_bom(
    production_quantity: float | Decimal,
    bom_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Calculates gross material requirements across all BOM line items
    incorporating scrap/wastage allowances.
    
    Formula per item:
      net_per_unit = quantity_per_unit
      gross_per_unit = net_per_unit * (1 + wastage_pct / 100)
      total_gross_required = gross_per_unit * production_quantity
    """
    prod_qty = Decimal(str(production_quantity))
    if prod_qty <= 0:
        raise ValueError("Production quantity must be positive.")

    calculated_components = []
    total_raw_mass_kg = Decimal("0.0")

    for item in bom_items:
        qty_unit = Decimal(str(item.get("quantity_per_unit", 1.0)))
        wastage_pct = Decimal(str(item.get("wastage_pct", 5.0)))
        unit = str(item.get("unit", "kg")).strip().lower()

        # Gross calculation
        wastage_multiplier = Decimal("1.0") + (wastage_pct / Decimal("100.0"))
        gross_per_unit = qty_unit * wastage_multiplier
        total_gross_qty = gross_per_unit * prod_qty
        wastage_quantity = total_gross_qty - (qty_unit * prod_qty)

        if unit == "kg":
            total_raw_mass_kg += total_gross_qty

        calculated_components.append({
            "material_id": item.get("material_id"),
            "material_name": item.get("material_name", "Raw Material"),
            "material_code": item.get("material_code", ""),
            "grade": item.get("grade", ""),
            "unit": unit,
            "net_quantity_per_unit": float(round_qty(qty_unit)),
            "wastage_pct": float(wastage_pct),
            "gross_quantity_per_unit": float(round_qty(gross_per_unit)),
            "total_net_required": float(round_qty(qty_unit * prod_qty)),
            "total_wastage_scrap": float(round_qty(wastage_quantity)),
            "total_gross_required": float(round_qty(total_gross_qty)),
            "process_stage": item.get("process_stage", "Primary Processing"),
        })

    return {
        "production_quantity": float(round_qty(prod_qty)),
        "total_components_count": len(calculated_components),
        "total_raw_mass_kg": float(round_qty(total_raw_mass_kg)),
        "components": calculated_components
    }

