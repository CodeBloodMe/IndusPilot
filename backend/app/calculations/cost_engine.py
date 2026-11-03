from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional

def round_curr(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def round_pct(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

def calculate_manufacturing_cost(
    production_quantity: float | Decimal,
    material_costs_breakdown: List[Dict[str, Any]],
    direct_labor_hours: float | Decimal = 0.0,
    labor_rate_per_hour: float | Decimal = 180.0, # INR/hour
    machine_hours: float | Decimal = 0.0,
    machine_rate_per_hour: float | Decimal = 350.0, # INR/hour
    electricity_kwh: float | Decimal = 0.0,
    electricity_tariff_per_kwh: float | Decimal = 8.50, # INR/kWh
    secondary_processes_total: float | Decimal = 0.0, # e.g. powder coating, plating, heat treatment
    transportation_total: float | Decimal = 0.0,
    packaging_total: float | Decimal = 0.0,
    overhead_pct: float | Decimal = 12.0, # factory overhead percentage
    other_expenses_total: float | Decimal = 0.0,
    target_gross_margin_pct: float | Decimal = 25.0,
    custom_selling_price_per_unit: Optional[float | Decimal] = None,
) -> Dict[str, Any]:
    """
    Deterministic 14-factor manufacturing cost and commercial pricing engine.
    Uses strict Decimal arithmetic to guarantee zero financial hallucination.
    """
    qty = Decimal(str(production_quantity))
    if qty <= 0:
        raise ValueError("Production quantity must be positive.")

    # 1 & 2: Raw Material and Wastage Costs
    total_net_material_cost = Decimal("0.0")
    total_scrap_wastage_cost = Decimal("0.0")

    for mat in material_costs_breakdown:
        # mat contains: gross_qty, net_qty, unit_cost
        m_unit_cost = Decimal(str(mat.get("unit_cost", 0.0)))
        m_gross_qty = Decimal(str(mat.get("gross_quantity", 0.0)))
        m_net_qty = Decimal(str(mat.get("net_quantity", m_gross_qty)))

        m_gross_cost = m_unit_cost * m_gross_qty
        m_net_cost = m_unit_cost * m_net_qty
        m_scrap_cost = m_gross_cost - m_net_cost

        total_net_material_cost += m_net_cost
        total_scrap_wastage_cost += m_scrap_cost

    raw_material_total = total_net_material_cost + total_scrap_wastage_cost

    # 3: Direct Labor Cost
    l_hours = Decimal(str(direct_labor_hours))
    l_rate = Decimal(str(labor_rate_per_hour))
    direct_labor_cost = l_hours * l_rate

    # 4: Machine Operating & Depreciation Cost
    m_hours = Decimal(str(machine_hours))
    m_rate = Decimal(str(machine_rate_per_hour))
    machine_cost = m_hours * m_rate

    # 5: Electricity Cost
    kwh = Decimal(str(electricity_kwh))
    tariff = Decimal(str(electricity_tariff_per_kwh))
    electricity_cost = kwh * tariff

    # 6: Secondary Processes & Surface Treatments
    sec_proc = Decimal(str(secondary_processes_total))

    # 7: Inbound/Outbound Transportation
    trans = Decimal(str(transportation_total))

    # 8: Packaging & Crating
    pkg = Decimal(str(packaging_total))

    # Direct / Prime Shop Floor Cost
    direct_prime_cost = (
        raw_material_total +
        direct_labor_cost +
        machine_cost +
        electricity_cost +
        sec_proc +
        trans +
        pkg
    )

    # 9: Factory Overhead Cost (allocated as percentage of direct prime cost)
    ovh_pct = Decimal(str(overhead_pct))
    overhead_cost = direct_prime_cost * (ovh_pct / Decimal("100.0"))

    # 10: Other Configurable Expenses
    other_exp = Decimal(str(other_expenses_total))

    # 11: Total Production Cost
    total_production_cost = direct_prime_cost + overhead_cost + other_exp

    # 12: Production Cost per Unit (Break-even threshold)
    unit_production_cost = total_production_cost / qty
    break_even_price_per_unit = unit_production_cost

    # 13 & 14: Target Margin, Selling Price, Projected Profit
    target_margin = Decimal(str(target_gross_margin_pct))
    if target_margin >= Decimal("100.0"):
        raise ValueError("Target gross margin cannot be 100% or greater.")

    # Suggested Selling Price based on target gross margin: Price = Cost / (1 - Margin%)
    margin_divisor = Decimal("1.0") - (target_margin / Decimal("100.0"))
    suggested_unit_price = unit_production_cost / margin_divisor

    # If user provided a specific custom selling price to test:
    if custom_selling_price_per_unit is not None:
        effective_unit_price = Decimal(str(custom_selling_price_per_unit))
    else:
        effective_unit_price = suggested_unit_price

    total_revenue = effective_unit_price * qty
    projected_gross_profit = total_revenue - total_production_cost
    
    # Margin calculation: Profit / Revenue
    if total_revenue > Decimal("0.0"):
        effective_margin_pct = (projected_gross_profit / total_revenue) * Decimal("100.0")
    else:
        effective_margin_pct = Decimal("0.0")

    is_loss_making = effective_unit_price < break_even_price_per_unit
    is_below_target = effective_margin_pct < target_margin

    return {
        "production_quantity": float(round_curr(qty)),
        "cost_breakdown": {
            "net_raw_material_cost": float(round_curr(total_net_material_cost)),
            "scrap_wastage_cost": float(round_curr(total_scrap_wastage_cost)),
            "total_raw_material_cost": float(round_curr(raw_material_total)),
            "direct_labor_cost": float(round_curr(direct_labor_cost)),
            "machine_operating_cost": float(round_curr(machine_cost)),
            "electricity_cost": float(round_curr(electricity_cost)),
            "secondary_processes_cost": float(round_curr(sec_proc)),
            "transportation_cost": float(round_curr(trans)),
            "packaging_cost": float(round_curr(pkg)),
            "allocated_overhead_cost": float(round_curr(overhead_cost)),
            "other_expenses": float(round_curr(other_exp)),
            "total_production_cost": float(round_curr(total_production_cost)),
        },
        "unit_economics": {
            "unit_cost": float(round_curr(unit_production_cost)),
            "break_even_price": float(round_curr(break_even_price_per_unit)),
            "suggested_unit_price": float(round_curr(suggested_unit_price)),
            "effective_unit_price": float(round_curr(effective_unit_price)),
            "total_revenue": float(round_curr(total_revenue)),
            "projected_gross_profit": float(round_curr(projected_gross_profit)),
            "target_margin_pct": float(round_pct(target_margin)),
            "effective_margin_pct": float(round_pct(effective_margin_pct)),
            "is_loss_making": is_loss_making,
            "is_below_target": is_below_target,
        },
        "operational_rates": {
            "labor_hours": float(l_hours),
            "labor_rate_hr": float(l_rate),
            "machine_hours": float(m_hours),
            "machine_rate_hr": float(m_rate),
            "electricity_kwh": float(kwh),
            "electricity_tariff_kwh": float(tariff),
            "overhead_pct": float(ovh_pct),
        }
    }

