from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict, Any, List, Optional, Union
from enum import Enum

class TaxTreatment(str, Enum):
    TAX_INCLUDED = "TAX_INCLUDED"
    TAX_EXCLUDED = "TAX_EXCLUDED"
    NO_TAX = "NO_TAX"
    UNKNOWN = "UNKNOWN"

def round_curr(val: Decimal) -> Decimal:
    """Rounds to 2 decimal places using industrial financial ROUND_HALF_UP."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def to_decimal(val: Union[float, int, str, Decimal], field_name: str = "Value") -> Decimal:
    """Safely parses a value into Decimal, raising ValueError on corrupt inputs."""
    if val is None:
        return Decimal("0.00")
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid numeric value '{val}' for financial calculation in {field_name}.")


def calculate_landed_cost(
    unit_price: Union[float, str, Decimal],
    quantity: Union[float, str, Decimal],
    tax_pct: Union[float, str, Decimal] = 18.0,
    tax_treatment: Union[TaxTreatment, str, None] = None,
    is_tax_inclusive: Optional[bool] = None,
    freight_total: Union[float, str, Decimal] = 0.0,
    packaging_total: Union[float, str, Decimal] = 0.0,
    other_charges_total: Union[float, str, Decimal] = 0.0,
    discount_pct: Union[float, str, Decimal] = 0.0,
    discount_amount: Union[float, str, Decimal] = 0.0,
    currency: str = "INR",
    base_currency: str = "INR",
    fx_rate_to_base: Optional[Union[float, Decimal]] = None,
    requested_quantity: Optional[Union[float, Decimal]] = None,
) -> Dict[str, Any]:
    """
    Deterministic total landed cost calculation engine with Decimal precision.
    Follows Indian GST and industrial manufacturing procurement standards.

    Tax Treatment Modes:
    - TAX_EXCLUDED: GST = Taxable Base * (tax_pct / 100)
    - TAX_INCLUDED: Taxable Base = Net Material / (1 + tax_pct / 100), GST = Net Material - Taxable Base
    - NO_TAX: GST = 0.00
    - UNKNOWN: Raises ValueError. Silently assuming inclusivity/exclusivity is strictly forbidden.
    """
    u_price = to_decimal(unit_price, "unit_price")
    qty = to_decimal(quantity, "quantity")
    t_pct = to_decimal(tax_pct, "tax_pct")
    freight = to_decimal(freight_total, "freight_total")
    packaging = to_decimal(packaging_total, "packaging_total")
    other = to_decimal(other_charges_total, "other_charges_total")
    disc_pct = to_decimal(discount_pct, "discount_pct")
    disc_amt = to_decimal(discount_amount, "discount_amount")

    # Resolve currency and FX rates
    curr = (currency or "INR").strip().upper()
    b_curr = (base_currency or "INR").strip().upper()
    fx = Decimal("1.00")

    if curr != b_curr:
        if fx_rate_to_base is None:
            raise ValueError(
                f"Currency mismatch detected: Quotation currency '{curr}' differs from base '{b_curr}', "
                f"and no valid dated foreign exchange conversion rate was configured."
            )
        fx = to_decimal(fx_rate_to_base, "fx_rate_to_base")
        if fx <= 0:
            raise ValueError("Foreign exchange rate must be strictly positive.")

    if qty <= 0:
        raise ValueError("Quantity must be strictly greater than zero.")
    if u_price < 0:
        raise ValueError("Unit price cannot be negative.")
    if t_pct < 0:
        raise ValueError("Tax percentage cannot be negative.")

    # Resolve tax mode
    mode: str
    if tax_treatment is not None:
        if hasattr(tax_treatment, "value"):
            mode = str(tax_treatment.value).strip().upper()
        else:
            mode = str(tax_treatment).strip().upper().replace("TAXTREATMENT.", "")
        valid_modes = [TaxTreatment.TAX_INCLUDED.value, TaxTreatment.TAX_EXCLUDED.value, TaxTreatment.NO_TAX.value, TaxTreatment.UNKNOWN.value]
        if mode not in valid_modes:
            raise ValueError(f"Unrecognized tax treatment mode '{tax_treatment}'.")
    elif is_tax_inclusive is not None:
        mode = TaxTreatment.TAX_INCLUDED.value if is_tax_inclusive else TaxTreatment.TAX_EXCLUDED.value
    else:
        # Backward compatibility default to TAX_EXCLUDED if not specified
        mode = TaxTreatment.TAX_EXCLUDED.value

    if mode == TaxTreatment.UNKNOWN.value:
        raise ValueError(
            "Tax treatment is unstated or UNKNOWN. Quotation cannot be scored until tax status "
            "(TAX_INCLUDED vs TAX_EXCLUDED vs NO_TAX) is verified by the purchasing auditor."
        )

    # 1. Gross Material Cost
    gross_material = u_price * qty

    # 2. Discounts
    if disc_amt > 0:
        actual_discount = disc_amt
    elif disc_pct > 0:
        actual_discount = gross_material * (disc_pct / Decimal("100.0"))
    else:
        actual_discount = Decimal("0.00")

    net_material = gross_material - actual_discount
    if net_material < 0:
        net_material = Decimal("0.00")

    # 3. Tax Base and GST Computation
    if mode == TaxTreatment.TAX_INCLUDED.value:
        # Base = Net / (1 + tax_pct / 100)
        tax_multiplier = Decimal("1.0") + (t_pct / Decimal("100.0"))
        material_base = net_material / tax_multiplier
        gst_amount = net_material - material_base
        is_tax_inc = True
    elif mode == TaxTreatment.NO_TAX.value:
        material_base = net_material
        gst_amount = Decimal("0.00")
        is_tax_inc = False
    else: # TAX_EXCLUDED
        material_base = net_material
        gst_amount = material_base * (t_pct / Decimal("100.0"))
        is_tax_inc = False

    # 4. Total Landed Cost (in quotation currency)
    # Total = Material Base + GST + Freight + Packaging + Other Mandatory Charges
    total_landed_curr = material_base + gst_amount + freight + packaging + other
    effective_unit_landed_curr = total_landed_curr / qty

    # 5. Convert to Base Currency (INR)
    total_landed = total_landed_curr * fx
    effective_unit_landed = effective_unit_landed_curr * fx
    budget_requirement = total_landed

    # 6. Fulfilled Unit Economics if requested quantity differs from quoted
    fulfilled_qty = to_decimal(requested_quantity, "requested_quantity") if requested_quantity else qty
    cost_per_fulfilled_unit = total_landed / fulfilled_qty if fulfilled_qty > 0 else effective_unit_landed

    return {
        "quantity": float(round_curr(qty)),
        "base_unit_price": float(round_curr(u_price)),
        "gross_material_cost": float(round_curr(gross_material * fx)),
        "discount_amount": float(round_curr(actual_discount * fx)),
        "material_base_cost": float(round_curr(material_base * fx)),
        "tax_amount": float(round_curr(gst_amount * fx)),
        "tax_pct": float(t_pct),
        "tax_treatment": mode,
        "is_tax_inclusive": is_tax_inc,
        "freight_cost": float(round_curr(freight * fx)),
        "packaging_charges": float(round_curr(packaging * fx)),
        "other_charges": float(round_curr(other * fx)),
        "total_landed_cost": float(round_curr(total_landed)),
        "effective_unit_landed_cost": float(round_curr(effective_unit_landed)),
        "cost_per_fulfilled_unit": float(round_curr(cost_per_fulfilled_unit)),
        "budget_requirement": float(round_curr(budget_requirement)),
        "currency": b_curr,
        "original_currency": curr,
        "fx_rate_applied": float(fx)
    }


def allocate_charges_across_items(
    items: List[Dict[str, Any]],
    total_freight: Union[float, str, Decimal] = 0.0,
    total_packaging: Union[float, str, Decimal] = 0.0,
    total_other: Union[float, str, Decimal] = 0.0,
    method: str = "PRO_RATA_VALUE" # PRO_RATA_VALUE, PRO_RATA_WEIGHT, EQUAL_SPLIT
) -> List[Dict[str, Any]]:
    """
    Distributes shared freight, packaging, and ancillary logistics charges across
    multiple items in a quotation using documented industrial accounting allocation rules.
    """
    if not items:
        return []

    t_freight = to_decimal(total_freight, "total_freight")
    t_pack = to_decimal(total_packaging, "total_packaging")
    t_other = to_decimal(total_other, "total_other")

    n = len(items)
    if n == 1:
        res = dict(items[0])
        res["allocated_freight"] = float(round_curr(t_freight))
        res["allocated_packaging"] = float(round_curr(t_pack))
        res["allocated_other"] = float(round_curr(t_other))
        return [res]

    allocated_items = []
    method_upper = method.upper()

    if method_upper == "PRO_RATA_WEIGHT":
        # Sum item weights (qty in kg)
        total_weight = sum(to_decimal(it.get("quantity", 0.0), "item_qty") for it in items)
        if total_weight <= 0:
            method_upper = "PRO_RATA_VALUE" # Fallback if weight is 0 or unavailable
        else:
            for it in items:
                w = to_decimal(it.get("quantity", 0.0), "item_qty")
                share = w / total_weight
                item_copy = dict(it)
                item_copy["allocated_freight"] = float(round_curr(t_freight * share))
                item_copy["allocated_packaging"] = float(round_curr(t_pack * share))
                item_copy["allocated_other"] = float(round_curr(t_other * share))
                allocated_items.append(item_copy)
            return allocated_items

    if method_upper == "EQUAL_SPLIT":
        share = Decimal("1.0") / Decimal(str(n))
        for it in items:
            item_copy = dict(it)
            item_copy["allocated_freight"] = float(round_curr(t_freight * share))
            item_copy["allocated_packaging"] = float(round_curr(t_pack * share))
            item_copy["allocated_other"] = float(round_curr(t_other * share))
            allocated_items.append(item_copy)
        return allocated_items

    # Default: PRO_RATA_VALUE
    # Calculate item gross/net line values
    line_values = []
    for it in items:
        u_p = to_decimal(it.get("unit_price", 0.0), "unit_price")
        q = to_decimal(it.get("quantity", 0.0), "quantity")
        line_values.append(u_p * q)

    total_val = sum(line_values)
    if total_val <= 0:
        # Equal split fallback if total value is zero
        share = Decimal("1.0") / Decimal(str(n))
        for it in items:
            item_copy = dict(it)
            item_copy["allocated_freight"] = float(round_curr(t_freight * share))
            item_copy["allocated_packaging"] = float(round_curr(t_pack * share))
            item_copy["allocated_other"] = float(round_curr(t_other * share))
            allocated_items.append(item_copy)
        return allocated_items

    for idx, it in enumerate(items):
        share = line_values[idx] / total_val
        item_copy = dict(it)
        item_copy["allocated_freight"] = float(round_curr(t_freight * share))
        item_copy["allocated_packaging"] = float(round_curr(t_pack * share))
        item_copy["allocated_other"] = float(round_curr(t_other * share))
        allocated_items.append(item_copy)

    return allocated_items


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
