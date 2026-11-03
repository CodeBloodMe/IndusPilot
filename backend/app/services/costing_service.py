"""
IndusPilot Cost Intelligence & What-If Simulation Service
Handles cost estimation persistence, data quality auditing, assumption snapshots,
and baseline vs scenario simulation diffs.
"""

import uuid
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.entities import ProductionCostEstimate, CostingScenario, Product, BillOfMaterials
from app.calculations.cost_engine import calculate_manufacturing_cost


def assess_cost_data_quality(
    material_costs_breakdown: List[Dict[str, Any]],
    direct_labor_hours: float,
    machine_hours: float,
    electricity_tariff: float,
) -> str:
    """
    Classifies the integrity of cost inputs:
    - COMPLETE: Verified supplier quotation prices and specific shopfloor rates provided.
    - ESTIMATED: Standard catalogue or default benchmark rates used.
    - NEEDS_INPUT: Key parameters (e.g. material price or labor hours) are zero or missing.
    - INVALID: Negative or anomalous parameters.
    """
    if direct_labor_hours < 0 or machine_hours < 0 or electricity_tariff < 0:
        return "INVALID"

    has_zero_material = False
    has_estimated_material = False

    for m in material_costs_breakdown:
        cost = float(m.get("unit_cost", 0.0))
        if cost <= 0.0:
            has_zero_material = True
        elif m.get("is_estimated", False):
            has_estimated_material = True

    if has_zero_material:
        return "NEEDS_INPUT"
    if has_estimated_material or direct_labor_hours == 0 or machine_hours == 0:
        return "ESTIMATED"
    return "COMPLETE"


def create_or_save_cost_estimate(
    db: Session,
    org_id: str,
    product_id: str,
    bom_id: str,
    payload_dict: Dict[str, Any],
    calc_result: Dict[str, Any],
    estimate_number: Optional[str] = None,
) -> ProductionCostEstimate:
    """
    Persists a deterministic 14-factor manufacturing cost estimate with complete audit snapshots.
    """
    cb = calc_result["cost_breakdown"]
    ue = calc_result["unit_economics"]
    assumptions = calc_result["operational_assumptions"]

    quality_status = assess_cost_data_quality(
        material_costs_breakdown=payload_dict.get("material_costs_breakdown", []),
        direct_labor_hours=float(payload_dict.get("direct_labor_hours", 0.0)),
        machine_hours=float(payload_dict.get("machine_hours", 0.0)),
        electricity_tariff=float(payload_dict.get("electricity_tariff_per_kwh", 8.5)),
    )

    if not estimate_number:
        seq = db.query(ProductionCostEstimate).filter(ProductionCostEstimate.organization_id == org_id).count() + 1
        estimate_number = f"EST-2026-{seq:04d}"

    estimate = ProductionCostEstimate(
        organization_id=org_id,
        estimate_number=estimate_number,
        product_id=product_id,
        bom_id=bom_id,
        batch_size=calc_result["production_quantity"],
        calculation_version="v1.0",
        data_quality_status=quality_status,
        currency="INR",
        raw_material_cost=cb["effective_raw_material_cost"],
        wastage_cost=cb["scrap_wastage_cost"],
        direct_labor_cost=cb["direct_labor_cost"],
        machine_cost=cb["machine_operating_cost"],
        electricity_cost=cb["electricity_cost"],
        secondary_processes_cost=cb["secondary_processes_cost"],
        transport_cost=cb["transportation_cost"],
        packaging_cost=cb["packaging_cost"],
        overhead_cost=cb["allocated_overhead_cost"],
        other_expenses=cb["other_expenses"],
        total_production_cost=cb["total_production_cost"],
        unit_cost=ue["unit_cost"],
        break_even_price=ue["break_even_price"],
        suggested_selling_price=ue["suggested_unit_price"],
        effective_selling_price=ue["effective_unit_price"],
        target_margin_pct=ue["target_margin_pct"],
        effective_margin_pct=ue["effective_margin_pct"],
        markup_pct=ue["markup_pct"],
        total_revenue=ue["total_revenue"],
        projected_profit=ue["projected_gross_profit"],
        overhead_allocation_method=assumptions.get("overhead_method", "PERCENTAGE_PRIME_COST"),
        is_loss_making=ue["is_loss_making"],
        assumptions_snapshot_json={
            "inputs": payload_dict,
            "operational_assumptions": assumptions,
            "calculated_at": datetime.utcnow().isoformat()
        },
        items_breakdown_json=payload_dict.get("material_costs_breakdown", []),
        created_at=datetime.utcnow()
    )
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    return estimate


def run_what_if_simulation(
    baseline_payload: Dict[str, Any],
    simulation_overrides: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Executes a side-by-side What-If Cost Simulation:
    - Runs baseline calculation.
    - Merges simulation overrides without modifying baseline.
    - Runs simulated scenario calculation.
    - Computes mathematical deltas across cost, selling price, profit, and margins.
    """
    # 1. Baseline Run
    baseline_result = calculate_manufacturing_cost(
        production_quantity=baseline_payload.get("production_quantity", 500.0),
        material_costs_breakdown=baseline_payload.get("material_costs_breakdown", []),
        direct_labor_hours=baseline_payload.get("direct_labor_hours", 120.0),
        labor_rate_per_hour=baseline_payload.get("labor_rate_per_hour", 180.0),
        workers_count=baseline_payload.get("workers_count", 1),
        machine_hours=baseline_payload.get("machine_hours", 45.0),
        machine_rate_per_hour=baseline_payload.get("machine_rate_per_hour", 350.0),
        machine_setup_hours=baseline_payload.get("machine_setup_hours", 0.0),
        machine_power_kw=baseline_payload.get("machine_power_kw", 0.0),
        electricity_kwh=baseline_payload.get("electricity_kwh"),
        electricity_tariff_per_kwh=baseline_payload.get("electricity_tariff_per_kwh", 8.5),
        secondary_processes_total=baseline_payload.get("secondary_processes_total", 0.0),
        transportation_total=baseline_payload.get("transportation_total", 0.0),
        packaging_total=baseline_payload.get("packaging_total", 0.0),
        overhead_method=baseline_payload.get("overhead_method", "PERCENTAGE_PRIME_COST"),
        overhead_rate=baseline_payload.get("overhead_rate", 12.0),
        other_expenses_total=baseline_payload.get("other_expenses_total", 0.0),
        recoverable_scrap_value_total=baseline_payload.get("recoverable_scrap_value_total", 0.0),
        target_gross_margin_pct=baseline_payload.get("target_gross_margin_pct", 25.0),
        custom_selling_price_per_unit=baseline_payload.get("custom_selling_price_per_unit"),
    )

    # 2. Simulated Run with overrides
    merged_payload = dict(baseline_payload)
    merged_payload.update(simulation_overrides)

    simulated_result = calculate_manufacturing_cost(
        production_quantity=merged_payload.get("production_quantity", 500.0),
        material_costs_breakdown=merged_payload.get("material_costs_breakdown", []),
        direct_labor_hours=merged_payload.get("direct_labor_hours", 120.0),
        labor_rate_per_hour=merged_payload.get("labor_rate_per_hour", 180.0),
        workers_count=merged_payload.get("workers_count", 1),
        machine_hours=merged_payload.get("machine_hours", 45.0),
        machine_rate_per_hour=merged_payload.get("machine_rate_per_hour", 350.0),
        machine_setup_hours=merged_payload.get("machine_setup_hours", 0.0),
        machine_power_kw=merged_payload.get("machine_power_kw", 0.0),
        electricity_kwh=merged_payload.get("electricity_kwh"),
        electricity_tariff_per_kwh=merged_payload.get("electricity_tariff_per_kwh", 8.5),
        secondary_processes_total=merged_payload.get("secondary_processes_total", 0.0),
        transportation_total=merged_payload.get("transportation_total", 0.0),
        packaging_total=merged_payload.get("packaging_total", 0.0),
        overhead_method=merged_payload.get("overhead_method", "PERCENTAGE_PRIME_COST"),
        overhead_rate=merged_payload.get("overhead_rate", 12.0),
        other_expenses_total=merged_payload.get("other_expenses_total", 0.0),
        recoverable_scrap_value_total=merged_payload.get("recoverable_scrap_value_total", 0.0),
        target_gross_margin_pct=merged_payload.get("target_gross_margin_pct", 25.0),
        custom_selling_price_per_unit=merged_payload.get("custom_selling_price_per_unit"),
    )

    # 3. Variance & Delta Math
    b_total = baseline_result["cost_breakdown"]["total_production_cost"]
    s_total = simulated_result["cost_breakdown"]["total_production_cost"]
    delta_total = round(s_total - b_total, 2)
    pct_delta_total = round((delta_total / b_total) * 100.0, 2) if b_total > 0 else 0.0

    b_unit = baseline_result["unit_economics"]["unit_cost"]
    s_unit = simulated_result["unit_economics"]["unit_cost"]
    delta_unit = round(s_unit - b_unit, 2)
    pct_delta_unit = round((delta_unit / b_unit) * 100.0, 2) if b_unit > 0 else 0.0

    b_profit = baseline_result["unit_economics"]["projected_gross_profit"]
    s_profit = simulated_result["unit_economics"]["projected_gross_profit"]
    delta_profit = round(s_profit - b_profit, 2)

    b_margin = baseline_result["unit_economics"]["effective_margin_pct"]
    s_margin = simulated_result["unit_economics"]["effective_margin_pct"]
    delta_margin = round(s_margin - b_margin, 2)

    return {
        "baseline": baseline_result,
        "simulated": simulated_result,
        "variance": {
            "delta_total_batch_cost": delta_total,
            "pct_delta_total_batch_cost": pct_delta_total,
            "delta_unit_cost": delta_unit,
            "pct_delta_unit_cost": pct_delta_unit,
            "delta_gross_profit": delta_profit,
            "delta_gross_margin_pct": delta_margin,
            "is_cost_reduced": delta_total < 0,
            "is_profit_increased": delta_profit > 0,
        },
        "overrides_applied": simulation_overrides
    }

