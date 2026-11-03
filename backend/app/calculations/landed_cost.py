from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional

def round_curr(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def calculate_landed_cost(
    unit_price: float | Decimal,
    quantity: float | Decimal,
    tax_pct: float | Decimal = 18.0,
    is_tax_inclusive: bool = False,
    freight_total: float | Decimal = 0.0,
    other_charges_total: float | Decimal = 0.0,
    discount_pct: float | Decimal = 0.0,
) -> Dict[str, Any]:
    """
    Computes total landed cost deterministically with Decimal precision.
    Correctly accounts for tax-inclusivity to prevent double-counting taxes.
    """
    u_price = Decimal(str(unit_price))
    qty = Decimal(str(quantity))
    t_pct = Decimal(str(tax_pct))
    freight = Decimal(str(freight_total))
    other = Decimal(str(other_charges_total))
    disc_pct = Decimal(str(discount_pct))

    if qty <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if u_price < 0:
        raise ValueError("Unit price cannot be negative.")

    # Base line amount
    gross_material = u_price * qty
    discount_amount = gross_material * (disc_pct / Decimal("100.0"))
    net_material = gross_material - discount_amount

    if is_tax_inclusive:
        # Net material already includes tax: Base = Net / (1 + tax_pct/100)
        tax_multiplier = Decimal("1.0") + (t_pct / Decimal("100.0"))
        material_base = net_material / tax_multiplier
        tax_amount = net_material - material_base
    else:
        material_base = net_material
        tax_amount = material_base * (t_pct / Decimal("100.0"))

    # Total landed cost = material_base + tax_amount + freight + other charges
    total_landed = material_base + tax_amount + freight + other
    effective_unit_landed = total_landed / qty

    return {
        "quantity": float(round_curr(qty)),
        "base_unit_price": float(round_curr(u_price)),
        "gross_material_cost": float(round_curr(gross_material)),
        "discount_amount": float(round_curr(discount_amount)),
        "material_base_cost": float(round_curr(material_base)),
        "tax_amount": float(round_curr(tax_amount)),
        "tax_pct": float(t_pct),
        "is_tax_inclusive": is_tax_inclusive,
        "freight_cost": float(round_curr(freight)),
        "other_charges": float(round_curr(other)),
        "total_landed_cost": float(round_curr(total_landed)),
        "effective_unit_landed_cost": float(round_curr(effective_unit_landed)),
    }

def convert_units(
    quantity: float,
    from_unit: str,
    to_unit: str,
    density_g_cm3: Optional[float] = None
) -> float:
    """
    Safe unit conversion. Raises ValueError on incompatible units.
    """
    from_u = from_unit.strip().lower()
    to_u = to_unit.strip().lower()

    if from_u == to_u:
        return quantity

    # Mass conversions
    mass_conversions = {
        ("ton", "kg"): 1000.0,
        ("mt", "kg"): 1000.0,
        ("metric ton", "kg"): 1000.0,
        ("kg", "ton"): 0.001,
        ("kg", "mt"): 0.001,
        ("g", "kg"): 0.001,
        ("kg", "g"): 1000.0,
        ("lbs", "kg"): 0.453592,
        ("kg", "lbs"): 2.20462,
    }

    if (from_u, to_u) in mass_conversions:
        return quantity * mass_conversions[(from_u, to_u)]

    raise ValueError(f"Incompatible or unsupported unit conversion from '{from_unit}' to '{to_unit}'.")

