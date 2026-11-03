import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    assert res.json()["service"] == "IndusPilot"

def test_dashboard_metrics(client):
    res = client.get("/api/v1/dashboard/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["active_suppliers_count"] >= 10
    assert data["verified_quotations_count"] >= 3
    assert data["procurement_spend_total"] > 0

def test_dashboard_summary(client):
    res = client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["active_suppliers_count"] >= 10
    assert "critical_shortages" in data

def test_suppliers_directory(client):
    res = client.get("/api/v1/suppliers")
    assert res.status_code == 200
    suppliers = res.json()
    assert len(suppliers) >= 10
    # Verify Apex Steel is present
    apex = next((s for s in suppliers if "Apex Steel" in s["name"]), None)
    assert apex is not None
    assert apex["quality_rating"] >= 4.0

def test_materials_and_inventory(client):
    res = client.get("/api/v1/materials")
    assert res.status_code == 200
    assert len(res.json()) >= 15

    res_inv = client.get("/api/v1/materials/inventory")
    assert res_inv.status_code == 200
    inv_items = res_inv.json()
    ss304_inv = next((i for i in inv_items if "SS-304" in i["material_code"]), None)
    assert ss304_inv is not None
    assert ss304_inv["current_stock"] == 400.0
    assert ss304_inv["reserved_stock"] == 50.0
    assert ss304_inv["available_stock"] == 350.0

def test_bom_explosion_and_netting(client):
    products_res = client.get("/api/v1/bom/products")
    assert products_res.status_code == 200
    products = products_res.json()
    assert len(products) >= 1

    prod_id = products[0]["id"]
    explode_res = client.post("/api/v1/bom/explode", json={
        "product_id": prod_id,
        "production_quantity": 500.0
    })
    assert explode_res.status_code == 200
    data = explode_res.json()
    assert data["production_quantity"] == 500.0
    assert data["components_count"] >= 4

    # Check SS304 component
    ss304_comp = next((c for c in data["components"] if "MAT-SS-304" in c["material_code"]), None)
    assert ss304_comp is not None
    # 500 brackets * 2.0 kg/bracket * (1 + 0.05 scrap) = 1,050 kg gross
    assert ss304_comp["total_gross_required"] == 1050.0
    # Net shortage: 1050 required + 50 safety - 350 available = 750 kg shortage
    assert ss304_comp["inventory_status"]["has_shortage"] is True
    assert ss304_comp["inventory_status"]["net_shortage"] == 750.0

def test_supplier_comparison_scoring(client):
    quotes_res = client.get("/api/v1/quotations?status=VERIFIED")
    assert quotes_res.status_code == 200
    quotes = quotes_res.json()
    assert len(quotes) >= 3

    compare_res = client.post("/api/v1/compare/evaluate", json={
        "quotation_ids": [q["id"] for q in quotes[:3]],
        "quantity": 800.0
    })
    assert compare_res.status_code == 200
    comp_data = compare_res.json()
    assert comp_data["compared_quotations_count"] == 3
    assert "recommended_candidate" in comp_data
    rec = comp_data["recommended_candidate"]
    assert rec["composite_score"] >= 70.0
    assert rec["decision_band"] in ["STRONGLY_RECOMMENDED", "VIABLE_ALTERNATIVE"]

def test_google_ortools_optimization(client):
    candidates = [
        {"supplier_id": "sup-apex", "supplier_name": "Apex Steel & Alloys Pvt Ltd", "unit_landed_cost": 320.0, "fixed_freight": 4500.0, "capacity": 1000.0, "moq": 200.0, "lead_time_days": 6, "quality_rating": 4.6},
        {"supplier_id": "sup-bharat", "supplier_name": "Bharat Forgings & Metals", "unit_landed_cost": 305.0, "fixed_freight": 6000.0, "capacity": 500.0, "moq": 500.0, "lead_time_days": 12, "quality_rating": 4.0},
        {"supplier_id": "sup-deccan", "supplier_name": "Deccan Precision Alloys", "unit_landed_cost": 333.0, "fixed_freight": 3000.0, "capacity": 1200.0, "moq": 100.0, "lead_time_days": 4, "quality_rating": 4.8}
    ]

    opt_res = client.post("/api/v1/optimizer/solve", json={
        "required_quantity": 800.0,
        "budget_limit": 300000.0,
        "candidates": candidates
    })
    assert opt_res.status_code == 200
    opt_data = opt_res.json()
    assert opt_data["status"] == "OPTIMAL"
    assert opt_data["total_cost"] > 0
    assert opt_data["allocated_suppliers_count"] >= 1
    # Check that sum of allocated quantities matches 800.0
    alloc_sum = sum(a["allocated_quantity"] for a in opt_data["allocations"])
    assert pytest.approx(alloc_sum, 0.1) == 800.0

def test_manufacturing_cost_engine(client):
    cost_res = client.post("/api/v1/costing/calculate", json={
        "production_quantity": 500.0,
        "material_costs_breakdown": [
            {"material_name": "SS304 Plate", "unit_cost": 315.0, "gross_quantity": 1050.0, "net_quantity": 1000.0}
        ],
        "direct_labor_hours": 120.0,
        "labor_rate_per_hour": 180.0,
        "machine_hours": 45.0,
        "machine_rate_per_hour": 350.0,
        "electricity_kwh": 650.0,
        "electricity_tariff_per_kwh": 8.50,
        "secondary_processes_total": 18000.0,
        "transportation_total": 6500.0,
        "packaging_total": 4500.0,
        "overhead_pct": 12.0,
        "target_gross_margin_pct": 25.0
    })
    assert cost_res.status_code == 200
    cost_data = cost_res.json()
    cb = cost_data["cost_breakdown"]
    ue = cost_data["unit_economics"]

    assert cb["total_production_cost"] > 0
    assert ue["unit_cost"] > 0
    assert ue["break_even_price"] == ue["unit_cost"]
    assert ue["suggested_unit_price"] > ue["break_even_price"]
    assert ue["effective_margin_pct"] == 25.0
    assert ue["is_loss_making"] is False

def test_negotiation_workflow_and_simulation(client):
    suppliers = client.get("/api/v1/suppliers").json()
    apex = next(s for s in suppliers if "Apex Steel" in s["name"])

    # 1. Start session
    start_res = client.post("/api/v1/negotiation/start", json={
        "supplier_id": apex["id"],
        "material_name": "Stainless Steel 304 Plate",
        "quantity": 800.0,
        "original_unit_price": 315.0,
        "target_unit_price": 295.0,
        "payment_terms": "15 Days Prompt Net"
    })
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]
    assert start_res.json()["status"] in ["READY_FOR_APPROVAL", "AWAITING_APPROVAL"]

    # 2. Simulate vendor counteroffer
    sim_res = client.post(f"/api/v1/negotiation/send-and-simulate?session_id={session_id}")
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["status"] == "RESPONSE_RECEIVED"
    assert sim_data["current_offered_price"] < 315.0 # Vendor made a concession
    assert sim_data["savings_vs_original"] > 0

def test_customer_quotation_and_pdf(client):
    cq_res = client.post("/api/v1/customer-quotes/generate", json={
        "customer_name": "Larsen Heavy Machinery",
        "customer_company": "L&H Industrial Division",
        "customer_email": "orders@larsen.com",
        "quantity": 500.0,
        "unit_cost": 637.0,
        "unit_selling_price": 850.0,
        "tax_pct": 18.0,
        "payment_terms": "50% Advance, 50% on Dispatch",
        "delivery_weeks": 3
    })
    assert cq_res.status_code == 200
    cq_data = cq_res.json()
    assert cq_data["margin_pct"] == 25.06
    assert cq_data["is_loss_making"] is False
    assert cq_data["pdf_available"] is True

    # Test PDF download endpoint
    pdf_res = client.get(f"/api/v1/customer-quotes/{cq_data['id']}/download-pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000

def test_multilingual_copilot(client):
    # English Query
    en_res = client.post("/api/v1/copilot/chat", json={
        "query": "Compare supplier quotations and find the best supplier for stainless steel 304"
    })
    assert en_res.status_code == 200
    assert "Supplier Intelligence Agent" in en_res.json()["agent_name"]

    # Hindi/Hinglish Query
    hi_res = client.post("/api/v1/copilot/chat", json={
        "query": "500 brackets ke liye material shortage check karo aur batao kitna stock chahiye"
    })
    assert hi_res.status_code == 200
    assert "Procurement Planning Agent" in hi_res.json()["agent_name"]
    assert "data" in hi_res.json()

def test_approvals_flow(client):
    apprs_res = client.get("/api/v1/approvals?status=PENDING")
    assert apprs_res.status_code == 200
    apprs = apprs_res.json()
    assert len(apprs) >= 1

    first_appr = apprs[0]
    action_res = client.post(f"/api/v1/approvals/{first_appr['id']}/action", json={
        "action": "APPROVE",
        "reason": "Authorized after verifying landed savings and delivery timeline."
    })
    assert action_res.status_code == 200
    assert action_res.json()["status"] == "APPROVED"

