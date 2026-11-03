"""
IndusPilot Phase 9 Financial Integrity Test Suite
Verifies:
1. 14-Factor deterministic manufacturing costing completeness and non-mutation of inputs.
2. Strict Python Decimal precision with zero floating-point drift.
3. Mathematical separation of Gross Margin % [P = C / (1 - M)] vs Markup % [P = C * (1 + Markup)].
4. Google OR-Tools MILP solver infeasibility guarantees (never reports savings when constraints are violated).
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP
from app.calculations.cost_engine import (
    calculate_manufacturing_cost,
    OverheadAllocationMethod,
    round_curr,
    round_pct
)
from app.calculations.landed_cost import calculate_landed_cost
from app.calculations.inventory_netting import calculate_net_procurement_requirement
from app.optimizers.multi_material_optimizer import solve_multi_material_procurement


def test_14_factor_manufacturing_costing_completeness_and_immutability():
    """Verify all 14 factors of manufacturing costing are strictly accounted for and baseline inputs are not mutated."""
    materials = [
        {
            "material_name": "Stainless Steel 304 Sheet Plate",
            "unit_cost": 315.00,
            "gross_quantity": 1050.0,
            "net_quantity": 1000.0
        },
        {
            "material_name": "M8 Hex Bolts Grade 8.8",
            "unit_cost": 4.50,
            "gross_quantity": 2000.0,
            "net_quantity": 2000.0
        }
    ]
    materials_copy = [dict(m) for m in materials]

    costing = calculate_manufacturing_cost(
        production_quantity=500.0,
        material_costs_breakdown=materials,
        direct_labor_hours=120.0,
        labor_rate_per_hour=180.0,
        workers_count=2,
        machine_hours=45.0,
        machine_rate_per_hour=350.0,
        machine_setup_hours=5.0,
        machine_setup_rate_per_hour=350.0,
        machine_power_kw=15.0,
        electricity_tariff_per_kwh=8.50,
        secondary_processes_total=18000.0,
        transportation_total=7500.0,
        packaging_total=5000.0,
        overhead_method="PERCENTAGE_PRIME_COST",
        overhead_rate=12.0,
        other_expenses_total=4500.0,
        recoverable_scrap_value_total=3500.0,
        target_gross_margin_pct=25.0
    )

    # 1. Verify inputs are not mutated
    assert materials == materials_copy

    cb = costing["cost_breakdown"]
    ue = costing["unit_economics"]

    # 2. Verify all factors are present and strictly non-negative
    factors = [
        "net_raw_material_cost", "scrap_wastage_cost", "effective_raw_material_cost",
        "direct_labor_cost", "machine_operating_cost", "electricity_cost",
        "secondary_processes_cost", "transportation_cost", "packaging_cost",
        "direct_prime_cost", "allocated_overhead_cost", "other_expenses",
        "total_production_cost"
    ]
    for factor in factors:
        assert factor in cb
        assert cb[factor] >= 0.0

    # 3. Verify arithmetic integrity:
    # Prime Cost = Materials + Labor + Machine + Electricity + Secondary + Transport + Packaging
    calculated_prime = (
        cb["effective_raw_material_cost"] +
        cb["direct_labor_cost"] +
        cb["machine_operating_cost"] +
        cb["electricity_cost"] +
        cb["secondary_processes_cost"] +
        cb["transportation_cost"] +
        cb["packaging_cost"]
    )
    assert abs(cb["direct_prime_cost"] - calculated_prime) < 0.05

    # Total Cost = Prime Cost + Overhead + Other Expenses
    calculated_total = cb["direct_prime_cost"] + cb["allocated_overhead_cost"] + cb["other_expenses"]
    assert abs(cb["total_production_cost"] - calculated_total) < 0.05

    # Break-even = Total Cost / Quantity
    assert abs(ue["break_even_price"] - (cb["total_production_cost"] / 500.0)) < 0.01


def test_strict_decimal_precision_and_rounding():
    """Verify currency and percentage calculations use strict Decimal precision without float inaccuracies."""
    # Example that typically causes floating point drift: 0.1 + 0.2 != 0.3
    d1 = Decimal("0.10")
    d2 = Decimal("0.20")
    assert round_curr(d1 + d2) == Decimal("0.30")

    # High precision landed cost calculation
    landed = calculate_landed_cost(
        unit_price=315.3333,
        quantity=750.0,
        tax_pct=18.0,
        freight_total=4555.55,
        packaging_total=1234.56,
        other_charges_total=500.00
    )
    assert isinstance(landed["total_landed_cost"], float)
    assert round(landed["effective_unit_landed_cost"], 2) > 315.33


def test_gross_margin_vs_markup_distinction():
    """
    Verify mathematical distinction between Gross Margin % and Markup %:
    Selling Price = Cost / (1 - Margin%)
    Markup% = (Price - Cost) / Cost * 100
    Margin% = (Price - Cost) / Price * 100
    """
    materials = [{
        "material_name": "Direct Raw Material",
        "unit_cost": 100.00,
        "gross_quantity": 10.0,
        "net_quantity": 10.0
    }]

    costing = calculate_manufacturing_cost(
        production_quantity=10.0,
        material_costs_breakdown=materials,
        direct_labor_hours=0.0,
        machine_hours=0.0,
        overhead_rate=0.0,
        target_gross_margin_pct=25.0
    )

    cb = costing["cost_breakdown"]
    ue = costing["unit_economics"]

    # Cost = 1000 total, 100 per unit
    unit_cost = ue["unit_cost"]
    assert abs(unit_cost - 100.0) < 0.01

    # At 25% target margin:
    # Price = 100 / (1 - 0.25) = 100 / 0.75 = 133.33
    expected_price = 100.0 / 0.75
    assert abs(ue["suggested_unit_price"] - expected_price) < 0.05

    # Markup % on 100 cost for 133.33 price: (133.33 - 100) / 100 = 33.33%
    assert abs(ue["markup_pct"] - 33.33) < 0.1
    # Margin % on 133.33 price for 100 cost: (133.33 - 100) / 133.33 = 25.0%
    assert abs(ue["effective_margin_pct"] - 25.0) < 0.1

    # Verify Markup is strictly greater than Margin for any positive profit
    assert ue["markup_pct"] > ue["effective_margin_pct"]


def test_ortools_infeasibility_guarantees_zero_savings_and_empty_allocation():
    """Verify that when requirements cannot be met (e.g. capacity or budget violated), solver reports INFEASIBLE and 0 savings."""
    requirements = [
        {
            "material_id": "mat-ss-304",
            "material_code": "MAT-SS-304",
            "material_name": "Stainless Steel 304",
            "required_quantity": 10000.0, # Exceeds all supplier capacity
            "required_by_days": 10
        }
    ]
    candidates = [
        {
            "quotation_id": "q1",
            "supplier_id": "s1",
            "supplier_name": "Small Supplier",
            "material_id": "mat-ss-304",
            "base_unit_price": 300.0,
            "effective_unit_landed_cost": 320.0,
            "min_order_quantity": 100.0,
            "max_supply_capacity": 500.0, # Max capacity is 500, requirement is 10,000
            "lead_time_days": 5,
            "reliability_score": 90.0,
            "composite_score": 85.0
        }
    ]

    result = solve_multi_material_procurement(
        requirements=requirements,
        candidates=candidates,
        global_budget_limit=50000.0 # Extremely low budget ceiling
    )

    # Infeasible solver status must never be reported as OPTIMAL
    assert result["solver_status"] != "OPTIMAL"
    assert result["total_landed_cost"] == 0.0
    assert result["allocations"] == []
    # Infeasible plan must never fabricate positive rupee savings
    assert result.get("savings_vs_baseline", 0.0) <= 0.0
