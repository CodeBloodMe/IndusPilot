from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any

def round_qty(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

def calculate_net_procurement_requirement(
    gross_requirement: float | Decimal,
    current_stock: float | Decimal,
    reserved_stock: float | Decimal = 0.0,
    incoming_stock: float | Decimal = 0.0,
    safety_stock: float | Decimal = 0.0,
) -> Dict[str, Any]:
    """
    Computes net purchasing shortage strictly:
    Available Stock = max(0, Current Stock - Reserved Stock)
    Effective Inventory = Available Stock + Incoming Stock
    Net Shortage = max(0, Gross Requirement + Safety Stock - Effective Inventory)
    """
    gross = Decimal(str(gross_requirement))
    current = Decimal(str(current_stock))
    reserved = Decimal(str(reserved_stock))
    incoming = Decimal(str(incoming_stock))
    safety = Decimal(str(safety_stock))

    if gross < 0:
        raise ValueError("Gross requirement cannot be negative.")

    available_stock = max(Decimal("0.0"), current - reserved)
    effective_inventory = available_stock + incoming
    target_inventory_need = gross + safety
    
    raw_shortage = target_inventory_need - effective_inventory
    net_procurement_needed = max(Decimal("0.0"), raw_shortage)

    has_shortage = net_procurement_needed > Decimal("0.0")
    is_fully_covered = net_procurement_needed == Decimal("0.0")

    return {
        "gross_requirement": float(round_qty(gross)),
        "current_stock": float(round_qty(current)),
        "reserved_stock": float(round_qty(reserved)),
        "available_stock": float(round_qty(available_stock)),
        "incoming_stock": float(round_qty(incoming)),
        "safety_stock": float(round_qty(safety)),
        "effective_inventory": float(round_qty(effective_inventory)),
        "net_shortage": float(round_qty(net_procurement_needed)),
        "mrp_net_shortage": float(round_qty(net_procurement_needed)),
        "unbuffered_shortage": float(round_qty(max(Decimal("0.0"), gross - effective_inventory))),
        "safety_stock_buffer": float(round_qty(safety)),
        "has_shortage": has_shortage,
        "is_fully_covered": is_fully_covered,
        "status_message": (
            f"Shortage of {float(round_qty(net_procurement_needed))} units detected. Purchase requisition required."
            if has_shortage else
            "Existing inventory and incoming orders adequately cover the production requirement."
        )
    }

