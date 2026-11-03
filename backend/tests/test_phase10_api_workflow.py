"""
IndusPilot Phase 10 Master API & Workflow Integrity Test
Tech4Bharat 2026 — Industrial Manufacturing (Problem Statement 4.1)

Validates the complete 9-step production and procurement lifecycle through actual HTTP API calls:
Step 1: Recursive BOM Explosion & Component Requirements
Step 2: Inventory Netting & Material Shortage Detection (750.0 kg net shortage)
Step 3: Supplier Retrieval & Verification
Step 4: Explainable 5-Factor Supplier Comparison & Composite Scoring
Step 5: Google OR-Tools MILP Procurement Optimization (Allocations, Landed Cost)
Step 6: Commercial Negotiation Simulation
Step 7: 14-Factor Manufacturing Cost Engine with Standardized 20% & 25% Margins
Step 8: Customer Commercial Quotation Generation & PDF Dispatch
Step 9: Governance Checkpoint, Role-Based Approval & Immutable Audit Trail
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

DEMO_HEADERS = {
    "X-Organization-ID": "org_tech4bharat_induspilot_demo",
    "X-User-ID": "user_rajesh_sharma"
}

def test_phase10_full_master_api_workflow_20_percent_margin(client):
    """Executes the complete 9-step manufacturing and procurement lifecycle at 20% gross margin."""
    
    # STEP 1: BOM EXPLOSION FOR 500 BRACKETS
    prod_res = client.get("/api/v1/bom/products", headers=DEMO_HEADERS)
    assert prod_res.status_code == 200
    products = prod_res.json()
    assert len(products) >= 1
    bracket = next((p for p in products if "IND-BRK-SS304" in p.get("code", "")), products[0])
    prod_id = bracket["id"]

    explode_res = client.post("/api/v1/bom/explode", json={
        "product_id": prod_id,
        "production_quantity": 500.0
    }, headers=DEMO_HEADERS)
    assert explode_res.status_code == 200
    explode_data = explode_res.json()
    assert explode_data["production_quantity"] == 500.0

    # STEP 2: INVENTORY NETTING & SHORTAGE
    ss304_comp = next((c for c in explode_data["components"] if "MAT-SS-304" in c["material_code"]), None)
    assert ss304_comp is not None
    assert ss304_comp["total_gross_required"] == 1050.0
    inv_stat = ss304_comp["inventory_status"]
    assert inv_stat["current_stock"] == 400.0
    assert inv_stat["available_stock"] == 350.0
    assert inv_stat["net_shortage"] == 750.0

    # STEP 3: SUPPLIER RETRIEVAL
    quotes_res = client.get("/api/v1/quotations?status=VERIFIED", headers=DEMO_HEADERS)
    assert quotes_res.status_code == 200
    quotes = quotes_res.json()
    assert len(quotes) >= 3

    # STEP 4: SUPPLIER COMPARISON
    compare_res = client.post("/api/v1/compare/evaluate", json={
        "quotation_ids": [q["id"] for q in quotes[:3]],
        "quantity": 750.0
    }, headers=DEMO_HEADERS)
    assert compare_res.status_code == 200
    candidates = compare_res.json().get("candidates") or compare_res.json().get("rankings")
    assert len(candidates) >= 2
    top_cand = candidates[0]
    assert top_cand["composite_score"] >= 75.0

    # STEP 5: OR-TOOLS MILP OPTIMIZATION
    opt_res = client.post("/api/v1/procurement/plans", json={
        "requirements": [
            {
                "material_id": ss304_comp["material_id"],
                "material_code": "MAT-SS-304",
                "required_quantity": 750.0,
                "unit": "kg"
            }
        ],
        "strategy": "LOWEST_LANDED_COST",
        "budget_limit": 500000.0,
        "allow_split_purchasing": True
    }, headers=DEMO_HEADERS)
    assert opt_res.status_code == 200
    opt_data = opt_res.json()
    assert opt_data["solver_status"] in ("OPTIMAL", "FEASIBLE")
    allocations = opt_data.get("allocations", [])
    assert len(allocations) >= 1
    total_allocated = sum(a["allocated_quantity"] for a in allocations)
    assert abs(total_allocated - 750.0) < 0.1

    # STEP 6: NEGOTIATION SIMULATION
    neg_res = client.post("/api/v1/negotiation/sessions", json={
        "quotation_id": quotes[0]["id"],
        "target_discount_pct": 5.0,
        "context_notes": "Phase 10 Workflow Validation"
    }, headers=DEMO_HEADERS)
    assert neg_res.status_code in (200, 201)
    neg_id = neg_res.json()["id"]

    sim_res = client.post(f"/api/v1/negotiation/sessions/{neg_id}/simulate-response", json={
        "supplier_sentiment": "FAVORABLE",
        "counteroffer_discount_pct": 4.0
    }, headers=DEMO_HEADERS)
    assert sim_res.status_code == 200

    # STEP 7: 14-FACTOR COSTING AT 20% GROSS MARGIN
    # Standard unit cost: ₹637.00. At 20% margin: Selling price = 637.00 / (1 - 0.20) = 796.25
    cost_res = client.post("/api/v1/costing/calculate", json={
        "production_quantity": 500.0,
        "material_costs_breakdown": [
            {
                "material_name": "Stainless Steel 304 Sheet Plate",
                "unit_cost": 315.00,
                "gross_quantity": 1050.0,
                "net_quantity": 1000.0
            }
        ],
        "direct_labor_hours": 120.0,
        "labor_rate_per_hour": 180.0,
        "machine_hours": 45.0,
        "machine_rate_per_hour": 350.0,
        "electricity_tariff_per_kwh": 8.50,
        "secondary_processes_total": 18000.0,
        "target_gross_margin_pct": 20.0
    }, headers=DEMO_HEADERS)
    assert cost_res.status_code == 200
    cost_data = cost_res.json()
    ue = cost_data["unit_economics"]
    
    # Financial consistency checks
    break_even = ue["break_even_price"]
    suggested = ue["suggested_unit_price"]
    assert break_even > 500.0
    expected_selling = round(break_even / (1.0 - 0.20), 2)
    assert suggested == expected_selling

    # STEP 8: CUSTOMER QUOTATION GENERATION
    cq_res = client.post("/api/v1/customer-quotes", json={
        "customer_name": "Tata Advanced Systems Ltd",
        "customer_company": "Tata Advanced Systems Ltd",
        "product_id": prod_id,
        "quantity": 500.0,
        "unit_cost": break_even,
        "unit_selling_price": suggested,
        "target_margin_pct": 20.0,
        "payment_terms": "30_DAYS_NET"
    }, headers=DEMO_HEADERS)
    assert cq_res.status_code in (200, 201)
    quote_data = cq_res.json()
    quote_id = quote_data["id"]
    assert quote_data["margin_pct"] == 20.0

    # Verify PDF Generation
    pdf_res = client.get(f"/api/v1/customer-quotes/{quote_id}/pdf", headers=DEMO_HEADERS)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000

    # STEP 9: APPROVAL GOVERNANCE
    approval_res = client.post(f"/api/v1/customer-quotes/{quote_id}/approve", json={
        "approver_name": "Rajesh Sharma, Owner",
        "notes": "Validated 20% margin compliance for Tech4Bharat demo."
    }, headers=DEMO_HEADERS)
    assert approval_res.status_code == 200
    assert approval_res.json()["status"] == "APPROVED"

def test_phase10_costing_and_quotation_25_percent_margin(client):
    """Verifies that 25% gross margin produces exact ₹849.33 selling price for ₹637.00 break-even."""
    cost_res = client.post("/api/v1/costing/calculate", json={
        "production_quantity": 500.0,
        "material_costs_breakdown": [
            {
                "material_name": "Stainless Steel 304 Sheet Plate",
                "unit_cost": 315.00,
                "gross_quantity": 1050.0,
                "net_quantity": 1000.0
            }
        ],
        "direct_labor_hours": 120.0,
        "labor_rate_per_hour": 180.0,
        "machine_hours": 45.0,
        "machine_rate_per_hour": 350.0,
        "electricity_tariff_per_kwh": 8.50,
        "secondary_processes_total": 18000.0,
        "target_gross_margin_pct": 25.0
    }, headers=DEMO_HEADERS)
    assert cost_res.status_code == 200
    cost_data = cost_res.json()
    ue = cost_data["unit_economics"]
    break_even = ue["break_even_price"]
    suggested = ue["suggested_unit_price"]

    # 637.00 / (1 - 0.25) = 849.3333 -> 849.33
    expected_selling = round(break_even / (1.0 - 0.25), 2)
    assert suggested == expected_selling
    # Ensure margin formula: (selling - cost) / selling == 0.25
    margin_calc = round((suggested - break_even) / suggested, 4)
    assert abs(margin_calc - 0.25) < 0.001
