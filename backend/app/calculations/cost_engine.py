"""
IndusPilot Deterministic 14-Factor Manufacturing Cost Engine
Implements strict Decimal financial mathematics for shopfloor manufacturing costing.
Guarantees zero floating-point imprecision and separates commercial pricing from sales tax.
"""

from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, Any, List, Optional


class OverheadAllocationMethod(str, Enum):
    PERCENTAGE_PRIME_COST = "PERCENTAGE_PRIME_COST"
    PERCENTAGE_DIRECT_LABOR = "PERCENTAGE_DIRECT_LABOR"
    MACHINE_HOURS = "MACHINE_HOURS"
    FIXED_PER_BATCH = "FIXED_PER_BATCH"
    FIXED_PER_UNIT = "FIXED_PER_UNIT"


def round_curr(val: Decimal) -> Decimal:
    """Rounds currency to 2 decimal places with ROUND_HALF_UP."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def round_pct(val: Decimal) -> Decimal:
    """Rounds percentage to 2 decimal places with ROUND_HALF_UP."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_manufacturing_cost(
    production_quantity: float | Decimal,
    material_costs_breakdown: List[Dict[str, Any]],
    direct_labor_hours: float | Decimal = 0.0,
    labor_rate_per_hour: float | Decimal = 180.0, # INR/hour
    workers_count: int = 1,
    machine_hours: float | Decimal = 0.0,
    machine_rate_per_hour: float | Decimal = 350.0, # INR/hour
    machine_setup_hours: float | Decimal = 0.0,
    machine_setup_rate_per_hour: Optional[float | Decimal] = None,
    machine_power_kw: float | Decimal = 0.0,
    electricity_kwh: Optional[float | Decimal] = None,
    electricity_tariff_per_kwh: float | Decimal = 8.50, # INR/kWh
    secondary_processes_total: float | Decimal = 0.0, # e.g. plating, heat treatment, powder coating
    transportation_total: float | Decimal = 0.0, # Freight
    packaging_total: float | Decimal = 0.0, # Packaging & crating
    overhead_method: str = "PERCENTAGE_PRIME_COST",
    overhead_rate: float | Decimal = 12.0, # Rate depends on method
    other_expenses_total: float | Decimal = 0.0, # Tooling, consumables, inspection
    recoverable_scrap_value_total: float | Decimal = 0.0,
    target_gross_margin_pct: float | Decimal = 25.0,
    custom_selling_price_per_unit: Optional[float | Decimal] = None,
) -> Dict[str, Any]:
    """
    Deterministic 14-Factor Manufacturing Cost Engine.
    
    Cost Structure:
    1. Net Raw Material Cost
    2. Scrap / Cutting Wastage Cost (minus recoverable scrap credit)
    3. Direct Labour Cost (workers * hours * rate)
    4. Machine Operating & Setup Cost
    5. Electricity Cost (kW * hours * tariff or direct kWh * tariff)
    6. Secondary Processes & Surface Treatments
    7. Inbound/Outbound Transportation
    8. Packaging & Crating
       -> Subtotal: Direct Prime Cost
    9. Factory Overhead Cost (allocated via selected method)
    10. Other Configurable Expenses (tooling, testing)
       -> Total Manufacturing Batch Cost
    11. Unit Production Cost (Break-even threshold)
    12. Suggested Selling Price = Unit Cost / (1 - Target Margin%)
    13. Projected Gross Profit
    14. Gross Profit Margin % and Markup %
    """
    qty = Decimal(str(production_quantity))
    if qty <= Decimal("0.0"):
        raise ValueError("Production quantity must be strictly positive.")

    # 1 & 2: Raw Material and Scrap Wastage
    total_net_mat_cost = Decimal("0.0")
    total_scrap_cost = Decimal("0.0")

    for mat in material_costs_breakdown:
        u_cost = Decimal(str(mat.get("unit_cost") if mat.get("unit_cost") is not None else 0.0))
        g_qty = Decimal(str(mat.get("gross_quantity") if mat.get("gross_quantity") is not None else 0.0))
        raw_net = mat.get("net_quantity")
        n_qty = Decimal(str(raw_net if raw_net is not None else g_qty))

        m_gross = u_cost * g_qty
        m_net = u_cost * n_qty
        m_scrap = m_gross - m_net
        if m_scrap < Decimal("0.0"):
            m_scrap = Decimal("0.0")

        total_net_mat_cost += m_net
        total_scrap_cost += m_scrap

    # Deduct recoverable scrap value if supplied
    scrap_credit = Decimal(str(recoverable_scrap_value_total))
    if scrap_credit > total_scrap_cost:
        scrap_credit = total_scrap_cost # Scrap credit cannot exceed scrap cost
    net_scrap_cost = total_scrap_cost - scrap_credit
    total_material_cost = total_net_mat_cost + net_scrap_cost

    # 3: Direct Labour Cost
    n_workers = Decimal(str(max(1, workers_count)))
    l_hours = Decimal(str(direct_labor_hours))
    l_rate = Decimal(str(labor_rate_per_hour))
    direct_labor_cost = n_workers * l_hours * l_rate

    # 4: Machine Operating & Setup Cost
    m_hours = Decimal(str(machine_hours))
    m_rate = Decimal(str(machine_rate_per_hour))
    m_setup_hours = Decimal(str(machine_setup_hours))
    m_setup_rate = Decimal(str(machine_setup_rate_per_hour if machine_setup_rate_per_hour is not None else m_rate))
    machine_cost = (m_hours * m_rate) + (m_setup_hours * m_setup_rate)

    # 5: Electricity Cost
    tariff = Decimal(str(electricity_tariff_per_kwh))
    if electricity_kwh is not None and Decimal(str(electricity_kwh)) > Decimal("0.0"):
        kwh_consumed = Decimal(str(electricity_kwh))
    else:
        power_kw = Decimal(str(machine_power_kw))
        kwh_consumed = power_kw * (m_hours + m_setup_hours)
    electricity_cost = kwh_consumed * tariff

    # 6: Secondary Processes & Surface Treatments
    sec_proc = Decimal(str(secondary_processes_total))

    # 7: Inbound/Outbound Transportation
    trans = Decimal(str(transportation_total))

    # 8: Packaging & Crating
    pkg = Decimal(str(packaging_total))

    # Direct / Prime Shop Floor Cost
    direct_prime_cost = (
        total_material_cost +
        direct_labor_cost +
        machine_cost +
        electricity_cost +
        sec_proc +
        trans +
        pkg
    )

    # 9: Manufacturing Overhead Allocation
    ovh_m = str(overhead_method).upper().strip()
    ovh_r = Decimal(str(overhead_rate))

    if ovh_m == OverheadAllocationMethod.PERCENTAGE_DIRECT_LABOR.value:
        overhead_cost = direct_labor_cost * (ovh_r / Decimal("100.0"))
    elif ovh_m == OverheadAllocationMethod.MACHINE_HOURS.value:
        overhead_cost = (m_hours + m_setup_hours) * ovh_r
    elif ovh_m == OverheadAllocationMethod.FIXED_PER_BATCH.value:
        overhead_cost = ovh_r
    elif ovh_m == OverheadAllocationMethod.FIXED_PER_UNIT.value:
        overhead_cost = qty * ovh_r
    else: # Default: PERCENTAGE_PRIME_COST
        overhead_cost = direct_prime_cost * (ovh_r / Decimal("100.0"))

    # 10: Other Direct Expenses (Tooling, Consumables, Testing)
    other_exp = Decimal(str(other_expenses_total))

    # 11: Total Manufacturing Cost
    total_production_cost = direct_prime_cost + overhead_cost + other_exp

    # 12: Unit Production Cost / Break-Even Price
    unit_production_cost = total_production_cost / qty
    break_even_price = unit_production_cost

    # 13: Suggested Selling Price based on target gross margin
    target_margin = Decimal(str(target_gross_margin_pct))
    if target_margin >= Decimal("100.0") or target_margin < Decimal("0.0"):
        raise ValueError("Target gross margin percentage must be strictly between 0% and 99.99%.")

    # Price = Cost / (1 - Margin%)
    margin_divisor = Decimal("1.0") - (target_margin / Decimal("100.0"))
    suggested_unit_price = round_curr(unit_production_cost / margin_divisor)

    # If custom selling price provided, evaluate against it
    if custom_selling_price_per_unit is not None:
        effective_unit_price = round_curr(Decimal(str(custom_selling_price_per_unit)))
    else:
        effective_unit_price = suggested_unit_price

    total_revenue = round_curr(effective_unit_price * qty)
    projected_gross_profit = round_curr(total_revenue - total_production_cost)

    # Margin % = Profit / Revenue * 100
    if total_revenue > Decimal("0.0"):
        effective_margin_pct = (projected_gross_profit / total_revenue) * Decimal("100.0")
    else:
        effective_margin_pct = Decimal("0.0")

    # Markup % = (Price - Cost) / Cost * 100
    if unit_production_cost > Decimal("0.0"):
        markup_pct = ((effective_unit_price - unit_production_cost) / unit_production_cost) * Decimal("100.0")
    else:
        markup_pct = Decimal("0.0")

    is_loss_making = effective_unit_price < break_even_price
    is_below_target = effective_margin_pct < target_margin

    return {
        "production_quantity": float(round_curr(qty)),
        "cost_breakdown": {
            "net_raw_material_cost": float(round_curr(total_net_mat_cost)),
            "scrap_wastage_cost": float(round_curr(total_scrap_cost)),
            "recoverable_scrap_credit": float(round_curr(scrap_credit)),
            "effective_raw_material_cost": float(round_curr(total_material_cost)),
            "direct_labor_cost": float(round_curr(direct_labor_cost)),
            "machine_operating_cost": float(round_curr(machine_cost)),
            "electricity_cost": float(round_curr(electricity_cost)),
            "secondary_processes_cost": float(round_curr(sec_proc)),
            "transportation_cost": float(round_curr(trans)),
            "packaging_cost": float(round_curr(pkg)),
            "direct_prime_cost": float(round_curr(direct_prime_cost)),
            "allocated_overhead_cost": float(round_curr(overhead_cost)),
            "other_expenses": float(round_curr(other_exp)),
            "total_production_cost": float(round_curr(total_production_cost)),
        },
        "unit_economics": {
            "unit_cost": float(round_curr(unit_production_cost)),
            "break_even_price": float(round_curr(break_even_price)),
            "suggested_unit_price": float(round_curr(suggested_unit_price)),
            "effective_unit_price": float(round_curr(effective_unit_price)),
            "total_revenue": float(round_curr(total_revenue)),
            "projected_gross_profit": float(round_curr(projected_gross_profit)),
            "target_margin_pct": float(round_pct(target_margin)),
            "effective_margin_pct": float(round_pct(effective_margin_pct)),
            "markup_pct": float(round_pct(markup_pct)),
            "is_loss_making": is_loss_making,
            "is_below_target": is_below_target,
        },
        "operational_assumptions": {
            "workers_count": int(n_workers),
            "labor_hours": float(l_hours),
            "labor_rate_hr": float(l_rate),
            "machine_hours": float(m_hours),
            "machine_rate_hr": float(m_rate),
            "machine_setup_hours": float(m_setup_hours),
            "electricity_kwh": float(kwh_consumed),
            "electricity_tariff_kwh": float(tariff),
            "overhead_method": ovh_m,
            "overhead_rate": float(ovh_r),
        }
    }
