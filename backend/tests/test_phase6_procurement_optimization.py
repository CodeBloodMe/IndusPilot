from decimal import Decimal
import uuid
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.entities import (
    ProcurementPlan, ProcurementPlanItem, ProcurementPlanAllocation,
    Material, Supplier, SupplierQuotation, QuotationItem, ProductionJob,
    PurchaseRequisition, ApprovalRequest
)
from app.optimizers.multi_material_optimizer import solve_multi_material_procurement
from app.services.procurement_baseline import compute_procurement_baselines
from app.services.procurement_plan_service import (
    create_and_optimize_procurement_plan,
    generate_procurement_candidates,
    request_plan_approval,
    approve_procurement_plan,
    reject_procurement_plan,
    generate_purchase_requisitions_from_plan
)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


# -----------------------------------------------------------------------------
# 1. Multi-Material OR-Tools MILP Solver Tests (Part 4 & 5)
# -----------------------------------------------------------------------------

def test_ortools_multi_material_lowest_cost():
    """Tests multi-material MILP demand fulfillment minimizing total landed cost."""
    requirements = [
        {"material_id": "M1", "material_code": "MAT-SS-304", "material_name": "SS304 Plate", "required_quantity": 450.0, "unit": "kg"},
        {"material_id": "M2", "material_code": "MAT-FAST-M8", "material_name": "M8 Bolts", "required_quantity": 2000.0, "unit": "nos"}
    ]

    candidates = [
        # SS304 Candidates
        {"material_id": "M1", "supplier_id": "S1", "supplier_name": "Apex Steel", "unit_landed_cost": 320.0, "capacity": 300.0, "moq": 100.0, "fixed_freight": 3000.0, "lead_time_days": 6, "quality_rating": 4.6},
        {"material_id": "M1", "supplier_id": "S2", "supplier_name": "Bharat Forgings", "unit_landed_cost": 305.0, "capacity": 500.0, "moq": 200.0, "fixed_freight": 5000.0, "lead_time_days": 10, "quality_rating": 4.1},
        # Fasteners Candidates
        {"material_id": "M2", "supplier_id": "S3", "supplier_name": "Precision Fasteners", "unit_landed_cost": 12.50, "capacity": 5000.0, "moq": 500.0, "fixed_freight": 1000.0, "lead_time_days": 4, "quality_rating": 4.8}
    ]

    res = solve_multi_material_procurement(
        requirements=requirements,
        candidates=candidates,
        strategy="LOWEST_LANDED_COST",
        allow_split_purchasing=True
    )

    assert res["status"] in ["OPTIMAL", "FEASIBLE"]
    assert res["total_landed_cost"] > 0
    assert res["total_units_required"] == 2450.0
    assert res["total_units_allocated"] >= 2450.0

    # Fasteners should be awarded to S3
    m2_alloc = [a for a in res["allocations"] if a["material_id"] == "M2"]
    assert len(m2_alloc) == 1
    assert m2_alloc[0]["supplier_id"] == "S3"
    assert m2_alloc[0]["allocated_quantity"] == 2000.0


def test_ortools_capacity_split_allocation():
    """Tests that solver automatically splits allocation when no single supplier has enough capacity."""
    requirements = [
        {"material_id": "M1", "material_code": "MAT-SS-304", "material_name": "SS304 Plate", "required_quantity": 1000.0, "unit": "kg"}
    ]

    candidates = [
        {"material_id": "M1", "supplier_id": "S1", "supplier_name": "Supplier A", "unit_landed_cost": 310.0, "capacity": 400.0, "moq": 100.0, "fixed_freight": 2000.0, "lead_time_days": 5},
        {"material_id": "M1", "supplier_id": "S2", "supplier_name": "Supplier B", "unit_landed_cost": 315.0, "capacity": 500.0, "moq": 100.0, "fixed_freight": 2000.0, "lead_time_days": 6},
        {"material_id": "M1", "supplier_id": "S3", "supplier_name": "Supplier C", "unit_landed_cost": 325.0, "capacity": 600.0, "moq": 100.0, "fixed_freight": 2000.0, "lead_time_days": 7}
    ]

    res = solve_multi_material_procurement(
        requirements=requirements,
        candidates=candidates,
        strategy="LOWEST_LANDED_COST",
        allow_split_purchasing=True
    )

    assert res["status"] in ["OPTIMAL", "FEASIBLE"]
    # Total allocated must satisfy 1000 kg
    total_alloc = sum(a["allocated_quantity"] for a in res["allocations"])
    assert total_alloc == 1000.0
    # Must use at least 2 suppliers since max capacity of any single supplier is 600 kg
    assert len(res["allocations"]) >= 2
    # Verify no supplier exceeds its capacity
    for a in res["allocations"]:
        cand = next(c for c in candidates if c["supplier_id"] == a["supplier_id"])
        assert a["allocated_quantity"] <= cand["capacity"]


def test_ortools_moq_and_packaging_multiples():
    """Tests packaging multiples and MOQ enforcement."""
    requirements = [
        {"material_id": "M_FAST", "material_code": "MAT-FAST-M8", "material_name": "M8 Bolts", "required_quantity": 1550.0, "unit": "nos", "max_overbuy_pct": 10.0}
    ]

    candidates = [
        {
            "material_id": "M_FAST", "supplier_id": "S_FAST", "supplier_name": "Fastener Hub",
            "unit_landed_cost": 12.0, "capacity": 10000.0, "moq": 500.0,
            "packaging_multiple": 100.0, # Packaged in boxes of 100
            "fixed_freight": 1500.0, "lead_time_days": 5
        }
    ]

    res = solve_multi_material_procurement(
        requirements=requirements,
        candidates=candidates,
        strategy="LOWEST_LANDED_COST",
        max_overbuy_pct=10.0
    )

    assert res["status"] in ["OPTIMAL", "FEASIBLE"]
    alloc = res["allocations"][0]
    # 1550 required with pack size 100 -> must round up to 1600 (16 boxes)
    assert alloc["allocated_quantity"] == 1600.0
    assert alloc["package_count"] == 16
    assert res["excess_units"] == 50.0


def test_ortools_budget_ceiling_constraint():
    """Tests that budget cap is strictly respected or diagnosed as infeasible."""
    requirements = [
        {"material_id": "M1", "material_code": "MAT-SS-304", "material_name": "SS304 Plate", "required_quantity": 500.0, "unit": "kg"}
    ]

    candidates = [
        {"material_id": "M1", "supplier_id": "S1", "supplier_name": "Supplier A", "unit_landed_cost": 300.0, "capacity": 1000.0, "moq": 100.0, "fixed_freight": 5000.0}
    ]

    # Feasible budget: ₹160,000 (Cost = 500 * 300 + 5000 = ₹155,000)
    res_ok = solve_multi_material_procurement(
        requirements=requirements,
        candidates=candidates,
        global_budget_limit=160000.0
    )
    assert res_ok["status"] in ["OPTIMAL", "FEASIBLE"]
    assert res_ok["total_landed_cost"] == 155000.0
    assert res_ok["budget_utilized_pct"] <= 100.0

    # Infeasible budget: ₹100,000 (Cannot meet minimum ₹155,000)
    res_fail = solve_multi_material_procurement(
        requirements=requirements,
        candidates=candidates,
        global_budget_limit=100000.0
    )
    assert res_fail["status"] == "INFEASIBLE"
    assert "budget" in str(res_fail["reasons"]).lower()


def test_ortools_multi_objective_strategies():
    """Tests that different strategies produce distinct supplier award trade-offs."""
    requirements = [
        {"material_id": "M1", "material_code": "MAT-SS-304", "material_name": "SS304 Plate", "required_quantity": 500.0, "unit": "kg"}
    ]

    candidates = [
        # Cheap, but slow and average quality
        {"material_id": "M1", "supplier_id": "S_CHEAP", "supplier_name": "Budget Steel", "unit_landed_cost": 290.0, "capacity": 1000.0, "moq": 100.0, "fixed_freight": 2000.0, "lead_time_days": 18, "quality_rating": 3.6, "reliability_score": 75.0},
        # Fast, but higher cost
        {"material_id": "M1", "supplier_id": "S_FAST", "supplier_name": "Rapid Alloy", "unit_landed_cost": 330.0, "capacity": 1000.0, "moq": 100.0, "fixed_freight": 2000.0, "lead_time_days": 3, "quality_rating": 4.2, "reliability_score": 92.0},
        # High quality, premium cost
        {"material_id": "M1", "supplier_id": "S_QUAL", "supplier_name": "Precision Spec", "unit_landed_cost": 340.0, "capacity": 1000.0, "moq": 100.0, "fixed_freight": 2000.0, "lead_time_days": 7, "quality_rating": 4.9, "reliability_score": 98.0}
    ]

    # Lowest cost strategy should choose Budget Steel
    res_cost = solve_multi_material_procurement(requirements=requirements, candidates=candidates, strategy="LOWEST_LANDED_COST")
    assert res_cost["allocations"][0]["supplier_id"] == "S_CHEAP"

    # Fastest delivery strategy should choose Rapid Alloy
    res_fast = solve_multi_material_procurement(requirements=requirements, candidates=candidates, strategy="FASTEST_DELIVERY")
    assert res_fast["allocations"][0]["supplier_id"] == "S_FAST"

    # Quality-first strategy should choose Precision Spec
    res_qual = solve_multi_material_procurement(requirements=requirements, candidates=candidates, strategy="QUALITY_FIRST")
    assert res_qual["allocations"][0]["supplier_id"] == "S_QUAL"


def test_ortools_infeasibility_diagnostics():
    """Tests bottleneck diagnosis when requirements cannot be fulfilled."""
    requirements = [
        {"material_id": "M_RARE", "material_code": "MAT-TITANIUM", "material_name": "Titanium Grade 5", "required_quantity": 500.0, "unit": "kg"}
    ]

    # 1. Zero eligible suppliers
    res_empty = solve_multi_material_procurement(requirements=requirements, candidates=[])
    assert res_empty["status"] == "INFEASIBLE"
    assert res_empty["diagnostics"][0]["bottleneck"] == "NO_ELIGIBLE_SUPPLIERS"

    # 2. Insufficient total capacity
    small_cap = [
        {"material_id": "M_RARE", "supplier_id": "S1", "supplier_name": "Tiny Shop", "unit_landed_cost": 1500.0, "capacity": 150.0, "moq": 10.0}
    ]
    res_cap = solve_multi_material_procurement(requirements=requirements, candidates=small_cap)
    assert res_cap["status"] == "INFEASIBLE"
    assert res_cap["diagnostics"][0]["bottleneck"] == "INSUFFICIENT_AGGREGATE_CAPACITY"


# -----------------------------------------------------------------------------
# 2. Baseline Comparison Engine Tests (Part 9)
# -----------------------------------------------------------------------------

def test_procurement_baseline_comparison():
    """Tests comparison against Baseline A (single cheapest) and Baseline B (cheapest per material)."""
    requirements = [
        {"material_id": "M1", "material_name": "Steel Sheet", "required_quantity": 400.0, "unit": "kg"},
        {"material_id": "M2", "material_name": "Fasteners", "required_quantity": 1000.0, "unit": "nos"}
    ]

    candidates = [
        # Full portfolio vendor S1
        {"material_id": "M1", "supplier_id": "S1", "supplier_name": "Full Fab Hub", "unit_landed_cost": 320.0, "capacity": 1000.0, "fixed_freight": 2000.0},
        {"material_id": "M2", "supplier_id": "S1", "supplier_name": "Full Fab Hub", "unit_landed_cost": 15.0, "capacity": 5000.0, "fixed_freight": 2000.0},
        # Specialized cheaper vendors
        {"material_id": "M1", "supplier_id": "S2", "supplier_name": "Specialist Steel", "unit_landed_cost": 300.0, "capacity": 1000.0, "fixed_freight": 3000.0},
        {"material_id": "M2", "supplier_id": "S3", "supplier_name": "Specialist Fasteners", "unit_landed_cost": 12.0, "capacity": 5000.0, "fixed_freight": 1000.0}
    ]

    opt_sol = solve_multi_material_procurement(requirements=requirements, candidates=candidates)
    baselines = compute_procurement_baselines(requirements, candidates, opt_sol)

    # Baseline A: Full Fab Hub (S1) supplies both: 400*320 + 1000*15 + 2000 freight = 128000 + 15000 + 2000 = 145000
    b_a = baselines["baseline_a"]
    assert b_a["is_feasible"] is True
    assert b_a["total_cost"] == 145000.0
    assert b_a["supplier_name"] == "Full Fab Hub"

    # Baseline B: S2 (Steel) + S3 (Fasteners): 400*300 + 3000 freight + 1000*12 + 1000 freight = 123000 + 13000 = 136000
    b_b = baselines["baseline_b"]
    assert b_b["is_feasible"] is True
    assert b_b["total_cost"] == 136000.0

    # Savings must be positive vs Baseline A
    assert b_a["savings_vs_baseline_abs"] >= 0


# -----------------------------------------------------------------------------
# 3. Procurement Plan Service & Database Persistence (Part 11 & 14)
# -----------------------------------------------------------------------------

def test_procurement_plan_lifecycle_and_approval(db):
    """Tests end-to-end plan creation, solving, approval, and requisition generation."""
    org_id = "org_tech4bharat_induspilot_demo"
    mat_ss304 = db.query(Material).filter(Material.organization_id == org_id, Material.code == "MAT-SS-304").first()
    mat_fast = db.query(Material).filter(Material.organization_id == org_id, Material.code == "MAT-FAST-M8").first()

    requirements = [
        {"material_id": mat_ss304.id, "material_code": mat_ss304.code, "material_name": mat_ss304.name, "required_quantity": 450.0, "unit": "kg"},
        {"material_id": mat_fast.id, "material_code": mat_fast.code, "material_name": mat_fast.name, "required_quantity": 1000.0, "unit": "nos"}
    ]

    # 1. Create and Optimize Plan
    plan_data = create_and_optimize_procurement_plan(
        db=db,
        org_id=org_id,
        requirements=requirements,
        strategy="LOWEST_LANDED_COST",
        budget_limit=300000.0
    )
    plan_id = plan_data["plan_id"]
    assert plan_data["status"] == "OPTIMIZED"
    assert plan_data["total_landed_cost"] > 0
    assert len(plan_data["allocations"]) >= 1

    # Verify persisted entities
    plan = db.query(ProcurementPlan).filter(ProcurementPlan.id == plan_id).first()
    assert plan is not None
    assert len(plan.items) == 2
    assert len(plan.allocations) >= 1

    # 2. Request Approval
    req_res = request_plan_approval(db, org_id, plan_id, requested_by="Senior Estimator")
    assert req_res["status"] == "AWAITING_APPROVAL"
    assert "approval_id" in req_res

    # 3. Approve Plan
    appr_res = approve_procurement_plan(db, org_id, plan_id, approved_by="Chief Financial Officer")
    assert appr_res["status"] == "APPROVED"
    assert appr_res["approved_by"] == "Chief Financial Officer"

    # 4. Generate Purchase Requisitions from Approved Plan
    gen_res = generate_purchase_requisitions_from_plan(db, org_id, plan_id)
    assert gen_res["requisitions_count"] >= 1
    assert len(gen_res["requisitions"]) == len(plan.allocations)

    # Verify purchase requisitions exist in DB
    for r in gen_res["requisitions"]:
        pr = db.query(PurchaseRequisition).filter(PurchaseRequisition.id == r["requisition_id"]).first()
        assert pr is not None
        assert pr.status == "APPROVED"
        assert pr.selected_supplier_id is not None


def test_procurement_plan_rejection(db):
    """Tests rejecting an unviable procurement plan."""
    org_id = "org_tech4bharat_induspilot_demo"
    mat = db.query(Material).filter(Material.organization_id == org_id, Material.code == "MAT-SS-304").first()

    requirements = [
        {"material_id": mat.id, "material_code": mat.code, "material_name": mat.name, "required_quantity": 300.0, "unit": "kg"}
    ]

    plan_data = create_and_optimize_procurement_plan(db, org_id, requirements)
    plan_id = plan_data["plan_id"]

    request_plan_approval(db, org_id, plan_id)
    rej_res = reject_procurement_plan(db, org_id, plan_id, reason="Alternative supplier quotation pending")
    assert rej_res["status"] == "REJECTED"
    assert rej_res["rejection_reason"] == "Alternative supplier quotation pending"


# -----------------------------------------------------------------------------
# 4. End-to-End REST API Routes Tests (Part 13)
# -----------------------------------------------------------------------------

def test_api_procurement_strategies(client):
    """Tests listing of the 5 mathematical procurement strategies."""
    res = client.get("/api/v1/procurement/strategies")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 5
    ids = [s["id"] for s in data]
    assert "LOWEST_LANDED_COST" in ids
    assert "BALANCED" in ids
    assert "FASTEST_DELIVERY" in ids
    assert "QUALITY_FIRST" in ids
    assert "BUDGET_CONSTRAINED" in ids


def test_api_procurement_plans_crud_and_reoptimize(client, db):
    """Tests complete REST API plan workflow: create, get, reoptimize, and approve."""
    org_id = "org_tech4bharat_induspilot_demo"
    mat_ss = db.query(Material).filter(Material.organization_id == org_id, Material.code == "MAT-SS-304").first()
    mat_bolt = db.query(Material).filter(Material.organization_id == org_id, Material.code == "MAT-FAST-M8").first()

    # 1. Create Plan via API
    create_res = client.post("/api/v1/procurement/plans", json={
        "requirements": [
            {"material_id": mat_ss.id, "material_code": mat_ss.code, "required_quantity": 400.0, "unit": "kg"},
            {"material_id": mat_bolt.id, "material_code": mat_bolt.code, "required_quantity": 1000.0, "unit": "nos"}
        ],
        "strategy": "LOWEST_LANDED_COST",
        "budget_limit": 250000.0,
        "allow_split_purchasing": True
    })
    assert create_res.status_code == 200
    plan_data = create_res.json()
    plan_id = plan_data["plan_id"]
    assert plan_data["plan_number"].startswith("PLAN-2026-")
    assert len(plan_data["allocations"]) >= 1

    # 2. Get Plan Details
    get_res = client.get(f"/api/v1/procurement/plans/{plan_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["id"] == plan_id
    assert len(details["items"]) == 2
    assert "baseline_comparison" in details

    # 3. Reoptimize with BALANCED strategy
    reopt_res = client.post(f"/api/v1/procurement/plans/{plan_id}/reoptimize?strategy=BALANCED")
    assert reopt_res.status_code == 200
    reopt_data = reopt_res.json()
    assert reopt_data["strategy"] == "BALANCED"

    # 4. Request Approval
    req_res = client.post(f"/api/v1/procurement/plans/{plan_id}/request-approval")
    assert req_res.status_code == 200
    assert req_res.json()["status"] == "AWAITING_APPROVAL"

    # 5. Approve
    appr_res = client.post(f"/api/v1/procurement/plans/{plan_id}/approve")
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "APPROVED"

    # 6. Generate Requisitions
    gen_res = client.post(f"/api/v1/procurement/plans/{plan_id}/generate-requisitions")
    assert gen_res.status_code == 200
    assert gen_res.json()["requisitions_count"] >= 1


def test_api_procurement_plan_from_production_job(client, db):
    """Tests creating a procurement plan directly from a production job's BOM shortages."""
    org_id = "org_tech4bharat_induspilot_demo"
    job = db.query(ProductionJob).filter(ProductionJob.organization_id == org_id).first()
    assert job is not None

    # 1. Test with tight budget -> correctly flags NEEDS_REVIEW
    res_tight = client.post("/api/v1/procurement/plans/from-job", json={
        "job_id": job.id,
        "strategy": "BALANCED",
        "budget_limit": 200000.0
    })
    assert res_tight.status_code == 200
    tight_data = res_tight.json()
    assert tight_data["status"] == "NEEDS_REVIEW"
    assert tight_data["solver_status"] == "INFEASIBLE"

    # 2. Test with sufficient budget (₹460,000) -> successfully optimizes
    res_ok = client.post("/api/v1/procurement/plans/from-job", json={
        "job_id": job.id,
        "strategy": "BALANCED",
        "budget_limit": 500000.0
    })
    assert res_ok.status_code == 200
    ok_data = res_ok.json()
    assert ok_data.get("reasons") == []
    assert ok_data["status"] == "OPTIMIZED"
    assert ok_data["solver_status"] == "OPTIMAL"
    assert ok_data["total_landed_cost"] > 0
    assert len(ok_data["allocations"]) >= 1
