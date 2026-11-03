"""
IndusPilot — Critical Procurement Optimisation Regression Test Suite
Tech4Bharat 2026 Problem Statement 4.1

Validates the mathematical and financial integrity of the Google OR-Tools
procurement optimizer and comparative baseline engine:
1. Infeasible solver result cannot receive an OPTIMAL label.
2. Infeasible result cannot generate savings claims.
3. Infeasible result cannot generate supplier allocations.
4. Timed-out solver must not be treated as optimal.
5. Feasible but non-optimal result must be labelled FEASIBLE.
6. Optimal result must have independently verified constraints.
7. Baseline comparisons must use equivalent material and delivery requirements.
8. Negative savings must not be silently converted into positive savings.
9. Savings cannot be claimed against an infeasible baseline.
10. Persisted procurement plan matches solver output exactly.
"""

import pytest
from app.optimizers.multi_material_optimizer import solve_multi_material_procurement
from app.services.procurement_baseline import compute_procurement_baselines
from app.database.session import SessionLocal
from app.models.entities import ProcurementPlan, ProductionJob
from app.api.v1.procurement import create_procurement_plan_from_job
from app.schemas.domain import ProcurementPlanFromJobRequest


@pytest.fixture
def sample_requirements():
    return [
        {
            "material_id": "mat_ss304",
            "material_code": "MAT-SS-304",
            "material_name": "Stainless Steel 304 Sheet",
            "required_quantity": 500.0,
            "unit": "kg",
            "max_lead_time_days": 14
        },
        {
            "material_id": "mat_fast_m8",
            "material_code": "MAT-FAST-M8",
            "material_name": "M8 Hex Fasteners",
            "required_quantity": 200.0,
            "unit": "nos",
            "max_lead_time_days": 10
        }
    ]


@pytest.fixture
def sample_candidates():
    return [
        {
            "material_id": "mat_ss304",
            "material_code": "MAT-SS-304",
            "supplier_id": "sup_1",
            "supplier_name": "Vendor Alpha",
            "unit_price": 300.0,
            "unit_landed_cost": 354.0,
            "fixed_freight": 2500.0,
            "capacity": 2000.0,
            "moq": 100.0,
            "packaging_multiple": 1.0,
            "lead_time_days": 7,
            "quality_rating": 4.5,
            "reliability_score": 92.0
        },
        {
            "material_id": "mat_ss304",
            "material_code": "MAT-SS-304",
            "supplier_id": "sup_2",
            "supplier_name": "Vendor Beta",
            "unit_price": 280.0,
            "unit_landed_cost": 330.4,
            "fixed_freight": 4000.0,
            "capacity": 300.0, # Capacity strictly less than 500 kg
            "moq": 50.0,
            "packaging_multiple": 1.0,
            "lead_time_days": 5,
            "quality_rating": 4.2,
            "reliability_score": 88.0
        },
        {
            "material_id": "mat_fast_m8",
            "material_code": "MAT-FAST-M8",
            "supplier_id": "sup_1",
            "supplier_name": "Vendor Alpha",
            "unit_price": 10.0,
            "unit_landed_cost": 11.8,
            "fixed_freight": 2500.0,
            "capacity": 5000.0,
            "moq": 50.0,
            "packaging_multiple": 100.0,
            "lead_time_days": 4,
            "quality_rating": 4.5,
            "reliability_score": 92.0
        }
    ]


# --------------------------------------------------------------------------
# Test 1: Infeasible solver result cannot receive an OPTIMAL label
# --------------------------------------------------------------------------
def test_regression_1_infeasible_cannot_be_optimal(sample_requirements, sample_candidates):
    # Impossibly tight budget => INFEASIBLE
    res = solve_multi_material_procurement(
        requirements=sample_requirements,
        candidates=sample_candidates,
        strategy="LOWEST_LANDED_COST",
        global_budget_limit=10000.0 # True cost is > 150,000
    )
    assert res["status"] != "OPTIMAL"
    assert res["status"] == "INFEASIBLE"
    assert res["solver_status"] == "INFEASIBLE"


# --------------------------------------------------------------------------
# Test 2: Infeasible result cannot generate savings claims
# --------------------------------------------------------------------------
def test_regression_2_infeasible_cannot_generate_savings(sample_requirements, sample_candidates):
    infeasible_opt = {
        "status": "INFEASIBLE",
        "solver_status": "INFEASIBLE",
        "total_landed_cost": 0.0,
        "allocations": [],
        "strategy": "LOWEST_LANDED_COST"
    }
    baselines = compute_procurement_baselines(sample_requirements, sample_candidates, infeasible_opt)

    # Baseline A savings must be exactly 0.0
    assert baselines["baseline_a"]["savings_vs_baseline_abs"] == 0.0
    assert baselines["baseline_a"]["savings_vs_baseline_pct"] == 0.0

    # Baseline B savings must be exactly 0.0
    assert baselines["baseline_b"]["savings_vs_baseline_abs"] == 0.0
    assert baselines["baseline_b"]["savings_vs_baseline_pct"] == 0.0

    # Baseline C must be marked infeasible
    assert baselines["optimized_c"]["is_feasible"] is False
    assert baselines["optimized_c"]["status_label"] != "Mathematically Optimal"
    assert "Infeasible" in baselines["optimized_c"]["status_label"]
    assert "Zero cost savings" in baselines["summary_headline"]


# --------------------------------------------------------------------------
# Test 3: Infeasible result cannot generate supplier allocations
# --------------------------------------------------------------------------
def test_regression_3_infeasible_allocations_empty(sample_requirements, sample_candidates):
    # Demand exceeds sum of all supplier capacities (10,000 kg required, max cap is 2300 kg)
    impossible_req = [
        {
            "material_id": "mat_ss304",
            "material_code": "MAT-SS-304",
            "material_name": "Stainless Steel 304 Sheet",
            "required_quantity": 10000.0,
            "unit": "kg",
            "max_lead_time_days": 14
        }
    ]
    res = solve_multi_material_procurement(
        requirements=impossible_req,
        candidates=sample_candidates,
        strategy="LOWEST_LANDED_COST"
    )
    assert res["status"] == "INFEASIBLE"
    assert res["allocations"] == []
    assert res["total_landed_cost"] == 0.0
    assert res["excess_units"] == 0.0


# --------------------------------------------------------------------------
# Test 4: Timed-out solver must not be treated as optimal
# --------------------------------------------------------------------------
def test_regression_4_timed_out_not_optimal(sample_requirements, sample_candidates):
    # Using 0 seconds limit forces immediate timeout
    res = solve_multi_material_procurement(
        requirements=sample_requirements,
        candidates=sample_candidates,
        time_limit_seconds=0
    )
    assert res["status"] != "OPTIMAL"
    assert res["solver_status"] in ["TIMED_OUT", "INFEASIBLE", "FEASIBLE"]


# --------------------------------------------------------------------------
# Test 5: Feasible but non-optimal result must be labelled FEASIBLE
# --------------------------------------------------------------------------
def test_regression_5_feasible_label_preservation(sample_requirements, sample_candidates):
    # Simulate a partial solution dictionary from solver
    feasible_sol = {
        "status": "FEASIBLE",
        "solver_status": "FEASIBLE",
        "strategy": "BALANCED",
        "total_landed_cost": 185000.0,
        "allocated_suppliers_count": 2,
        "allocations": [{"supplier_id": "sup_1", "allocated_quantity": 500.0}],
        "explanation_headline": "Feasible allocation within time limit"
    }
    baselines = compute_procurement_baselines(sample_requirements, sample_candidates, feasible_sol)
    assert baselines["optimized_c"]["is_feasible"] is True
    assert "Feasible" in baselines["optimized_c"]["status_label"]
    assert "Mathematically Optimal" not in baselines["optimized_c"]["status_label"]


# --------------------------------------------------------------------------
# Test 6: Optimal result must independently satisfy all physical constraints
# --------------------------------------------------------------------------
def test_regression_6_optimal_constraints_independently_verified(sample_requirements, sample_candidates):
    res = solve_multi_material_procurement(
        requirements=sample_requirements,
        candidates=sample_candidates,
        strategy="LOWEST_LANDED_COST"
    )
    assert res["status"] == "OPTIMAL"
    assert len(res["allocations"]) >= 1

    # Independent verification of constraints on allocation output:
    req_map = {r["material_id"]: r["required_quantity"] for r in sample_requirements}
    allocated_by_mat = {}

    for a in res["allocations"]:
        m_id = a["material_id"]
        qty = a["allocated_quantity"]
        allocated_by_mat[m_id] = allocated_by_mat.get(m_id, 0.0) + qty

        # MOQ check
        cand = next(c for c in sample_candidates if c["supplier_id"] == a["supplier_id"] and c["material_id"] == m_id)
        assert qty >= cand["moq"] - 1e-4

        # Capacity check
        assert qty <= cand["capacity"] + 1e-4

        # Packaging multiple check
        pkg = cand.get("packaging_multiple", 1.0)
        if pkg > 1.0:
            assert abs((qty % pkg)) < 1e-3 or abs(pkg - (qty % pkg)) < 1e-3

    # Demand check
    for m_id, req_qty in req_map.items():
        assert allocated_by_mat.get(m_id, 0.0) >= req_qty - 1e-4


# --------------------------------------------------------------------------
# Test 7: Baseline comparisons must use equivalent material and delivery requirements
# --------------------------------------------------------------------------
def test_regression_7_baseline_uses_equivalent_demand(sample_requirements, sample_candidates):
    opt = solve_multi_material_procurement(sample_requirements, sample_candidates, strategy="LOWEST_LANDED_COST")
    baselines = compute_procurement_baselines(sample_requirements, sample_candidates, opt)

    # In Baseline B, each material allocation must exactly match requirement quantity
    req_map = {r["material_id"]: r["required_quantity"] for r in sample_requirements}
    for b_alloc in baselines["baseline_b"]["allocations"]:
        m_id = b_alloc["material_id"]
        assert b_alloc["allocated_quantity"] == req_map[m_id]


# --------------------------------------------------------------------------
# Test 8: Negative savings must not be silently converted into positive savings
# --------------------------------------------------------------------------
def test_regression_8_negative_savings_not_clamped():
    # If IndusPilot chose a higher quality / faster supplier costing 200,000,
    # while Baseline A was 180,000, savings must be negative (-20,000)
    mock_reqs = [{"material_id": "mat_1", "required_quantity": 100.0, "unit": "kg"}]
    mock_cands = [{
        "material_id": "mat_1",
        "supplier_id": "sup_1",
        "supplier_name": "Vendor A",
        "unit_landed_cost": 1800.0,
        "fixed_freight": 0.0,
        "capacity": 500.0,
        "moq": 10.0
    }]
    # Optimized solution with premium vendor
    premium_opt = {
        "status": "OPTIMAL",
        "solver_status": "OPTIMAL",
        "strategy": "QUALITY_FIRST",
        "total_landed_cost": 200000.0,
        "allocated_suppliers_count": 1,
        "allocations": [{"material_id": "mat_1", "supplier_id": "sup_prem", "allocated_quantity": 100.0}]
    }

    baselines = compute_procurement_baselines(mock_reqs, mock_cands, premium_opt)
    savings_abs = baselines["baseline_a"]["savings_vs_baseline_abs"]
    savings_pct = baselines["baseline_a"]["savings_vs_baseline_pct"]

    # Negative savings must be preserved
    assert savings_abs == -20000.0
    assert savings_pct < 0.0
    assert "premium" in baselines["baseline_a"]["explanation"].lower()


# --------------------------------------------------------------------------
# Test 9: Savings cannot be claimed against an infeasible baseline
# --------------------------------------------------------------------------
def test_regression_9_infeasible_baseline_no_savings(sample_requirements):
    # Candidates where no single supplier supplies all items
    fragmented_cands = [
        {
            "material_id": "mat_ss304",
            "supplier_id": "sup_only_steel",
            "supplier_name": "Steel Only Vendor",
            "unit_landed_cost": 300.0,
            "fixed_freight": 1000.0,
            "capacity": 1000.0,
            "moq": 10.0
        },
        {
            "material_id": "mat_fast_m8",
            "supplier_id": "sup_only_bolts",
            "supplier_name": "Bolts Only Vendor",
            "unit_landed_cost": 12.0,
            "fixed_freight": 500.0,
            "capacity": 5000.0,
            "moq": 10.0
        }
    ]
    opt = solve_multi_material_procurement(sample_requirements, fragmented_cands, strategy="LOWEST_LANDED_COST")
    baselines = compute_procurement_baselines(sample_requirements, fragmented_cands, opt)

    # Baseline A (single supplier) cannot be fulfilled by any single vendor
    assert baselines["baseline_a"]["is_feasible"] is False
    assert baselines["baseline_a"]["savings_vs_baseline_abs"] == 0.0
    assert baselines["baseline_a"]["savings_vs_baseline_pct"] == 0.0


# --------------------------------------------------------------------------
# Test 10: Persisted procurement plan matches solver output exactly
# --------------------------------------------------------------------------
def test_regression_10_persisted_plan_matches_solver(db=None):
    session = SessionLocal()
    try:
        job = session.query(ProductionJob).first()
        if not job:
            pytest.skip("No demo production job found in database.")

        res = create_procurement_plan_from_job(
            ProcurementPlanFromJobRequest(
                job_id=job.id,
                strategy="BALANCED",
                budget_limit=600000.0
            ),
            session,
            "org_tech4bharat_induspilot_demo"
        )

        plan = session.query(ProcurementPlan).filter(ProcurementPlan.id == res["plan_id"]).first()
        assert plan is not None

        # Verify persisted fields match returned payload exactly
        assert plan.solver_status == res["solver_status"]
        assert plan.status == res["status"]
        assert round(plan.total_landed_cost, 2) == round(res["total_landed_cost"], 2)
        assert round(plan.excess_units, 2) == round(res["excess_units"], 2)
        assert len(plan.allocations) == len(res["allocations"])
    finally:
        session.close()

