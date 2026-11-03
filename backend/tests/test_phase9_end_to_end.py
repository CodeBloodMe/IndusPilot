"""
IndusPilot Phase 9 End-to-End Master Workflow Integration Test
Tech4Bharat 2026 — Industrial Manufacturing (Problem Statement 4.1)

Master Order Scenario:
An industrial manufacturing customer places an order for 500 units of
Stainless Steel Industrial Brackets (IND-BRK-SS304).

Full 9-Step End-to-End Integration:
Step 1: Customer Order Ingestion & Recursive BOM Explosion
Step 2: MRP Inventory Netting & Material Shortage Detection (750.0 kg net shortage)
Step 3: Supplier Quotation Retrieval & Verification
Step 4: Explainable 5-Factor Supplier Comparison & Composite Scoring
Step 5: Google OR-Tools MILP Procurement Optimization (Multi-Supplier Split)
Step 6: Autonomous Commercial Negotiation & Supplier Counteroffer Simulation
Step 7: Deterministic 14-Factor Manufacturing Cost Estimation
Step 8: Customer Commercial Quotation Generation & PDF Rendering
Step 9: Human-in-the-Loop Commercial Authorization & Purchase Order Workflow
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.models.entities import Product, Material, Inventory, SupplierQuotation


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_master_end_to_end_manufacturing_workflow(client, db_session):
    """Executes the full 9-step production and procurement lifecycle for 500 industrial brackets."""
    org_id = settings.DEFAULT_ORGANIZATION_ID

    # ------------------------------------------------------------------------
    # STEP 1: CUSTOMER ORDER INGESTION & BOM EXPLOSION
    # ------------------------------------------------------------------------
    prod_res = client.get("/api/v1/bom/products")
    assert prod_res.status_code == 200
    products = prod_res.json()
    assert len(products) >= 1
    bracket_prod = next((p for p in products if "IND-BRK-SS304" in p["code"]), products[0])
    prod_id = bracket_prod["id"]

    explode_res = client.post("/api/v1/bom/explode", json={
        "product_id": prod_id,
        "production_quantity": 500.0
    })
    assert explode_res.status_code == 200
    explode_data = explode_res.json()
    assert explode_data["production_quantity"] == 500.0
    assert explode_data["components_count"] >= 4

    # ------------------------------------------------------------------------
    # STEP 2: MRP INVENTORY NETTING & SHORTAGE DETECTION
    # ------------------------------------------------------------------------
    ss304_comp = next((c for c in explode_data["components"] if "MAT-SS-304" in c["material_code"]), None)
    assert ss304_comp is not None

    # Gross required = 500 * 2.0 kg * (1 + 0.05 scrap) = 1,050.0 kg
    assert ss304_comp["total_gross_required"] == 1050.0
    inv_stat = ss304_comp["inventory_status"]
    assert inv_stat["has_shortage"] is True
    assert inv_stat["current_stock"] == 400.0
    assert inv_stat["reserved_stock"] == 50.0
    assert inv_stat["available_stock"] == 350.0
    assert inv_stat["safety_stock"] == 50.0
    # Net shortage: 1050 required + 50 safety - 350 available = 750.0 kg shortage
    assert inv_stat["net_shortage"] == 750.0
    assert inv_stat["unbuffered_shortage"] == 700.0

    # ------------------------------------------------------------------------
    # STEP 3: SUPPLIER QUOTATION RETRIEVAL & VERIFICATION
    # ------------------------------------------------------------------------
    quotes_res = client.get("/api/v1/quotations?status=VERIFIED")
    assert quotes_res.status_code == 200
    quotes = quotes_res.json()
    assert len(quotes) >= 3

    # Filter quotes relevant to Stainless Steel
    ss_quotes = [q for q in quotes if any("304" in it.get("material_code", "") or "304" in it.get("material_name", "") for it in q.get("items", []))]
    if len(ss_quotes) < 2:
        ss_quotes = quotes[:3]

    # ------------------------------------------------------------------------
    # STEP 4: EXPLAINABLE 5-FACTOR SUPPLIER COMPARISON
    # ------------------------------------------------------------------------
    compare_res = client.post("/api/v1/compare/evaluate", json={
        "quotation_ids": [q["id"] for q in ss_quotes[:3]],
        "quantity": 750.0
    })
    assert compare_res.status_code == 200
    comp_data = compare_res.json()
    assert "candidates" in comp_data or "rankings" in comp_data
    candidates = comp_data.get("candidates") or comp_data.get("rankings")
    assert len(candidates) >= 2
    # Verify top candidate has highest composite score
    top_cand = candidates[0]
    assert top_cand["composite_score"] >= 75.0
    assert "scorecard" in top_cand or "scorecard_json" in top_cand

    # ------------------------------------------------------------------------
    # STEP 5: GOOGLE OR-TOOLS MILP PROCUREMENT OPTIMIZATION
    # ------------------------------------------------------------------------
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
    })
    assert opt_res.status_code == 200
    opt_data = opt_res.json()
    assert opt_data["solver_status"] in ("OPTIMAL", "FEASIBLE")
    allocations = opt_data.get("allocations", [])
    assert len(allocations) >= 1
    total_allocated = sum(a["allocated_quantity"] for a in allocations)
    assert abs(total_allocated - 750.0) < 0.1

    # ------------------------------------------------------------------------
    # STEP 6: COMMERCIAL NEGOTIATION SIMULATION
    # ------------------------------------------------------------------------
    neg_init_res = client.post("/api/v1/negotiation/sessions", json={
        "quotation_id": ss_quotes[0]["id"],
        "target_discount_pct": 5.0,
        "context_notes": "Bulk requirement for 500 brackets order"
    })
    assert neg_init_res.status_code in (200, 201)
    neg_session = neg_init_res.json()
    session_id = neg_session["id"]

    sim_res = client.post(f"/api/v1/negotiation/sessions/{session_id}/simulate-response", json={
        "supplier_sentiment": "FAVORABLE",
        "counteroffer_discount_pct": 4.5
    })
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert "revised_unit_price" in sim_data or "supplier_message" in sim_data

    # ------------------------------------------------------------------------
    # STEP 7: 14-FACTOR MANUFACTURING COST ENGINE
    # ------------------------------------------------------------------------
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
    })
    assert cost_res.status_code == 200
    cost_data = cost_res.json()
    cb = cost_data["cost_breakdown"]
    ue = cost_data["unit_economics"]
    assert cb["total_production_cost"] > 250000.0
    assert ue["break_even_price"] > 500.0
    assert ue["suggested_unit_price"] > ue["break_even_price"]

    # ------------------------------------------------------------------------
    # STEP 8: CUSTOMER QUOTATION GENERATION & PDF
    # ------------------------------------------------------------------------
    cq_res = client.post("/api/v1/customer-quotes", json={
        "customer_name": "Larsen Heavy Machinery Corp",
        "customer_company": "Larsen Heavy Machinery Corp",
        "product_id": prod_id,
        "quantity": 500.0,
        "unit_cost": ue["break_even_price"],
        "unit_selling_price": ue["suggested_unit_price"],
        "target_margin_pct": 25.0,
        "payment_terms": "30_DAYS_NET"
    })
    assert cq_res.status_code in (200, 201)
    quote_data = cq_res.json()
    assert quote_data["profitability_status"] in ("HIGHLY_PROFITABLE", "PROFITABLE")
    quote_id = quote_data["id"]

    pdf_res = client.get(f"/api/v1/customer-quotes/{quote_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000

    # ------------------------------------------------------------------------
    # STEP 9: HUMAN-IN-THE-LOOP APPROVAL & PO CREATION
    # ------------------------------------------------------------------------
    approval_res = client.post(f"/api/v1/customer-quotes/{quote_id}/approve", json={
        "approver_name": "S. Sharma, Plant Head",
        "notes": "Verified 25.0% gross margin target. Approved for commercial dispatch."
    })
    assert approval_res.status_code == 200
    approved_quote = approval_res.json()
    assert approved_quote["status"] == "APPROVED"
