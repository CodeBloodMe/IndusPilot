from decimal import Decimal
import uuid
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.models.entities import Product, BillOfMaterials, BOMItem, Material, Inventory, ProductionJob
from app.services.unit_conversion import convert_unit, normalize_unit_str, get_unit_dimension, UnitDimension
from app.calculations.bom_engine import calculate_component_requirement, explode_bom, aggregate_material_requirements
from app.calculations.cost_engine import calculate_manufacturing_cost, OverheadAllocationMethod
from app.services.inventory_service import (
    receive_stock, issue_stock, reserve_stock, release_reservation,
    adjust_stock, get_inventory_alerts, get_or_create_inventory
)
from app.services.bom_service import validate_bom_items, create_bom_revision, compare_bom_revisions
from app.services.costing_service import run_what_if_simulation, assess_cost_data_quality

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

# -------------------------------------------------------------
# 1. Unit Conversion Tests (Part 3.3)
# -------------------------------------------------------------

def test_unit_conversions_mass_length_volume():
    # Mass
    assert convert_unit(1.0, "tonne", "kg") == Decimal("1000.0000")
    assert convert_unit(500.0, "grams", "kg") == Decimal("0.5000")
    assert convert_unit(2.5, "kg", "grams") == Decimal("2500.0000")

    # Length
    assert convert_unit(1.5, "metres", "mm") == Decimal("1500.0000")
    assert convert_unit(250.0, "mm", "cm") == Decimal("25.0000")

    # Area
    assert convert_unit(2.0, "sq_metre", "sq_cm") == Decimal("20000.0000")
    assert convert_unit(1000000.0, "sq_mm", "sq_metre") == Decimal("1.0000")

    # Volume
    assert convert_unit(3.5, "litres", "ml") == Decimal("3500.0000")

    # Count
    assert convert_unit(12.0, "pcs", "units") == Decimal("12.0000")

def test_cross_dimensional_unit_conversion():
    # Area (sq_metre) to Mass (kg) with thickness=2.0mm and density=7.93 g/cm3 (SS304)
    # Weight per m2 = 2.0 * 7.93 = 15.86 kg/m2
    # 10 sq_metres * 15.86 = 158.6 kg
    converted_kg = convert_unit(10.0, "sq_metre", "kg", density_g_cm3=7.93, thickness_mm=2.0)
    assert converted_kg == Decimal("158.6000")

    # Mass to Area
    converted_sqm = convert_unit(158.6, "kg", "sq_metre", density_g_cm3=7.93, thickness_mm=2.0)
    assert converted_sqm == Decimal("10.0000")

    # Volume to Mass (Litres to kg with density=1.2)
    # 5 litres * 1.2 = 6.0 kg
    converted_vol = convert_unit(5.0, "litres", "kg", density_g_cm3=1.2)
    assert converted_vol == Decimal("6.0000")

    # Refusal when required physical properties missing
    with pytest.raises(ValueError, match="requires both 'density_g_cm3' and 'thickness_mm'"):
        convert_unit(10.0, "sq_metre", "kg")

    with pytest.raises(ValueError, match="is not supported"):
        convert_unit(10.0, "metres", "litres")

# -------------------------------------------------------------
# 2. BOM & Material Requirement Calculations (Parts 2 & 3)
# -------------------------------------------------------------

def test_bom_scrap_additive_calculation():
    # 500 units * 2.0 kg/unit with 5% scrap
    # Net = 1,000 kg, Gross = 1,000 * 1.05 = 1,050 kg, Scrap = 50 kg
    res = calculate_component_requirement(
        quantity_per_unit=2.0,
        production_quantity=500.0,
        wastage_pct=5.0,
        scrap_method="ADDITIVE_SCRAP"
    )
    assert res["total_net"] == Decimal("1000.000")
    assert res["total_gross"] == Decimal("1050.000")
    assert res["total_scrap"] == Decimal("50.000")

def test_bom_yield_based_calculation():
    # 500 units * 1.9 kg/unit with 95% yield
    # Net = 950 kg, Gross = 950 / 0.95 = 1,000 kg, Scrap = 50 kg
    res = calculate_component_requirement(
        quantity_per_unit=1.9,
        production_quantity=500.0,
        scrap_method="YIELD_BASED",
        expected_yield_pct=95.0
    )
    assert res["total_net"] == Decimal("950.000")
    assert res["total_gross"] == Decimal("1000.000")
    assert res["total_scrap"] == Decimal("50.000")

def test_bom_material_aggregation_multi_orders():
    reqs = [
        {"material_id": "mat-1", "material_name": "SS304", "grade": "SS304", "unit": "kg", "total_net_required": 100.0, "total_gross_required": 105.0, "total_wastage_scrap": 5.0, "order_ref": "ORD-1"},
        {"material_id": "mat-1", "material_name": "SS304", "grade": "SS304", "unit": "kg", "total_net_required": 150.0, "total_gross_required": 157.5, "total_wastage_scrap": 7.5, "order_ref": "ORD-2"},
        {"material_id": "mat-1", "material_name": "SS304", "grade": "SS316", "unit": "kg", "total_net_required": 80.0, "total_gross_required": 84.0, "total_wastage_scrap": 4.0, "order_ref": "ORD-3"}, # Different grade!
    ]
    agg = aggregate_material_requirements(reqs)
    assert len(agg) == 2 # SS304 and SS316 separated!

    ss304_group = next(g for g in agg if g["grade"] == "SS304")
    assert ss304_group["total_net_required"] == 250.0
    assert ss304_group["total_gross_required"] == 262.5
    assert ss304_group["orders_count"] == 2

def test_bom_validation_rejections(db):
    org_id = "org_tech4bharat_induspilot_demo"
    mat = db.query(Material).filter(Material.organization_id == org_id).first()

    # Negative quantity
    is_valid, errors, _ = validate_bom_items(db, org_id, [{"material_id": mat.id, "quantity_per_unit": -1.0}])
    assert not is_valid
    assert any("strictly positive" in e for e in errors)

    # Duplicate component in same BOM
    is_valid, errors, _ = validate_bom_items(db, org_id, [
        {"material_id": mat.id, "quantity_per_unit": 1.0},
        {"material_id": mat.id, "quantity_per_unit": 2.0}
    ])
    assert not is_valid
    assert any("Duplicate material reference" in e for e in errors)

    # Invalid scrap percentage > 100%
    is_valid, errors, _ = validate_bom_items(db, org_id, [{"material_id": mat.id, "quantity_per_unit": 1.0, "wastage_pct": 150.0}])
    assert not is_valid
    assert any("between 0% and 100%" in e for e in errors)

def test_bom_revision_and_comparison(db):
    org_id = "org_tech4bharat_induspilot_demo"
    # Create isolated product for revision test so seed data active BOM remains untouched
    test_prod = Product(
        organization_id=org_id,
        code=f"PROD-REV-{uuid.uuid4().hex[:6]}",
        name="Test Reversible Assembly",
        base_unit="units"
    )
    db.add(test_prod)
    db.flush()

    orig_bom = BillOfMaterials(
        organization_id=org_id,
        product_id=test_prod.id,
        name="Base Revision v1.0",
        version="v1.0",
        revision_status="ACTIVE",
        is_active=True
    )
    db.add(orig_bom)
    db.flush()

    mat = db.query(Material).filter(Material.organization_id == org_id).first()
    db.add(BOMItem(bom_id=orig_bom.id, material_id=mat.id, quantity_per_unit=2.0, wastage_pct=3.0))
    db.commit()

    # Create new revision v2.0
    new_bom = create_bom_revision(
        db=db,
        org_id=org_id,
        original_bom_id=orig_bom.id,
        new_version_label="v2.0",
        revision_notes="Test revision with increased scrap tolerance."
    )
    assert new_bom.version == "v2.0"
    assert new_bom.is_active is True
    assert orig_bom.is_active is False
    assert orig_bom.revision_status == "SUPERSEDED"

    # Compare revisions
    diff = compare_bom_revisions(db, org_id, orig_bom.id, new_bom.id)
    assert diff["bom_1"]["version"] == orig_bom.version
    assert diff["bom_2"]["version"] == "v2.0"
    assert len(diff["differences"]) > 0

# -------------------------------------------------------------
# 3. Inventory Ledger & Operations (Part 4)
# -------------------------------------------------------------

def test_inventory_receive_and_moving_average_cost(db):
    org_id = "org_tech4bharat_induspilot_demo"
    mat = db.query(Material).filter(Material.organization_id == org_id, Material.code == "MAT-SS-304").first()
    inv = get_or_create_inventory(db, org_id, mat.id)
    initial_stock = inv.current_stock
    initial_reserved = inv.reserved_stock

    try:
        test_key = f"IDEMP-REC-{uuid.uuid4()}"
        # Receive 100 kg at ₹320.0/kg with idempotency key
        res = receive_stock(
            db=db,
            org_id=org_id,
            material_id=mat.id,
            quantity=100.0,
            unit="kg",
            unit_cost=320.0,
            reference_id="PO-TEST-001",
            idempotency_key=test_key
        )
        assert res["received_quantity"] == 100.0
        assert res["current_stock"] == initial_stock + 100.0

        # Repeat with same idempotency key: must be skipped
        res_repeat = receive_stock(
            db=db,
            org_id=org_id,
            material_id=mat.id,
            quantity=100.0,
            unit="kg",
            idempotency_key=test_key
        )
        assert res_repeat["status"] == "DUPLICATE_IDEMPOTENT_SKIPPED"
        assert res_repeat["current_stock"] == initial_stock + 100.0
    finally:
        # Restore stock to initial baseline
        inv.current_stock = initial_stock
        inv.reserved_stock = initial_reserved
        db.commit()

def test_inventory_issue_and_negative_stock_prevention(db):
    org_id = "org_tech4bharat_induspilot_demo"
    mat = db.query(Material).filter(Material.organization_id == org_id, Material.code == "MAT-SS-304").first()
    inv = get_or_create_inventory(db, org_id, mat.id)
    initial_stock = inv.current_stock
    initial_reserved = inv.reserved_stock

    try:
        avail = inv.current_stock - inv.reserved_stock
        # Attempt to issue more than available stock: must fail
        with pytest.raises(ValueError, match="Insufficient unreserved stock"):
            issue_stock(db, org_id, mat.id, quantity=avail + 500.0, allow_negative_stock=False)

        # Issue safe quantity
        res = issue_stock(db, org_id, mat.id, quantity=10.0, destination="CNC Laser 01")
        assert res["issued_quantity"] == 10.0
    finally:
        inv.current_stock = initial_stock
        inv.reserved_stock = initial_reserved
        db.commit()

def test_inventory_reservation_and_release(db):
    org_id = "org_tech4bharat_induspilot_demo"
    mat = db.query(Material).filter(Material.organization_id == org_id, Material.code == "MAT-SS-304").first()
    inv = get_or_create_inventory(db, org_id, mat.id)
    init_reserved = inv.reserved_stock

    # Reserve 25 kg
    res = reserve_stock(db, org_id, mat.id, quantity=25.0, production_job_id="JOB-TEST-99")
    assert res["reserved_quantity"] == 25.0
    assert res["new_total_reserved"] == init_reserved + 25.0

    # Release reservation
    rel = release_reservation(db, org_id, res["reservation_id"])
    assert rel["status"] == "RELEASED"
    assert rel["released_quantity"] == 25.0
    assert inv.reserved_stock == init_reserved

def test_inventory_physical_audit_adjustment(db):
    org_id = "org_tech4bharat_induspilot_demo"
    mat = db.query(Material).filter(Material.organization_id == org_id, Material.code == "MAT-SS-304").first()
    inv = get_or_create_inventory(db, org_id, mat.id)
    initial_stock = inv.current_stock

    try:
        target_count = 300.0
        res = adjust_stock(db, org_id, mat.id, new_physical_stock=target_count, reason="Q4 Physical Audit")
        assert res["new_stock"] == 300.0
        assert "adjustment_delta" in res
    finally:
        db.expire_all()
        inv_restore = db.query(Inventory).filter(Inventory.material_id == mat.id, Inventory.organization_id == org_id).first()
        if inv_restore:
            inv_restore.current_stock = initial_stock
            db.commit()

def test_inventory_operational_alerts(db):
    org_id = "org_tech4bharat_induspilot_demo"
    alerts = get_inventory_alerts(db, org_id)
    assert isinstance(alerts, list)
    # Check that each alert contains message and material code
    for a in alerts:
        assert "alert_type" in a
        assert "message" in a
        assert "material_code" in a

# -------------------------------------------------------------
# 4. Manufacturing Costing & What-If Simulation (Parts 6, 7, 8, 9)
# -------------------------------------------------------------

def test_manufacturing_costing_14_factors():
    # 500 units batch
    materials = [
        {"material_name": "SS304 Sheet", "unit_cost": 315.0, "gross_quantity": 1050.0, "net_quantity": 1000.0},
        {"material_name": "Fasteners M8", "unit_cost": 12.0, "gross_quantity": 2040.0, "net_quantity": 2000.0},
    ]
    # Net mat: 1000*315 + 2000*12 = 315,000 + 24,000 = 339,000
    # Scrap: 50*315 + 40*12 = 15,750 + 480 = 16,230
    # Effective raw: 355,230

    res = calculate_manufacturing_cost(
        production_quantity=500.0,
        material_costs_breakdown=materials,
        direct_labor_hours=120.0,
        labor_rate_per_hour=180.0, # 21,600
        machine_hours=45.0,
        machine_rate_per_hour=350.0, # 15,750
        electricity_kwh=650.0,
        electricity_tariff_per_kwh=8.5, # 5,525
        secondary_processes_total=18000.0,
        transportation_total=6500.0,
        packaging_total=4500.0,
        overhead_method="PERCENTAGE_PRIME_COST",
        overhead_rate=12.0, # 12% of prime
        target_gross_margin_pct=25.0
    )

    cb = res["cost_breakdown"]
    ue = res["unit_economics"]

    assert cb["effective_raw_material_cost"] == 355230.0
    assert cb["direct_labor_cost"] == 21600.0
    assert cb["machine_operating_cost"] == 15750.0
    assert cb["electricity_cost"] == 5525.0
    assert cb["direct_prime_cost"] > 0
    assert cb["total_production_cost"] > cb["direct_prime_cost"]

    # Margin check: Selling price = unit_cost / (1 - 0.25)
    expected_price = round(ue["unit_cost"] / 0.75, 2)
    assert abs(ue["suggested_unit_price"] - expected_price) <= 0.05
    assert ue["is_loss_making"] is False

def test_manufacturing_costing_overhead_allocation_methods():
    materials = [{"material_name": "Steel", "unit_cost": 100.0, "gross_quantity": 100.0}] # 10,000

    # 1. PERCENTAGE_DIRECT_LABOR (50% of direct labor 2,000 = 1,000)
    res_lab = calculate_manufacturing_cost(
        production_quantity=100.0,
        material_costs_breakdown=materials,
        direct_labor_hours=10.0,
        labor_rate_per_hour=200.0, # 2,000
        overhead_method="PERCENTAGE_DIRECT_LABOR",
        overhead_rate=50.0
    )
    assert res_lab["cost_breakdown"]["allocated_overhead_cost"] == 1000.0

    # 2. FIXED_PER_BATCH (Fixed ₹5,000)
    res_fixed = calculate_manufacturing_cost(
        production_quantity=100.0,
        material_costs_breakdown=materials,
        overhead_method="FIXED_PER_BATCH",
        overhead_rate=5000.0
    )
    assert res_fixed["cost_breakdown"]["allocated_overhead_cost"] == 5000.0

def test_manufacturing_costing_loss_making_detection():
    materials = [{"material_name": "Steel", "unit_cost": 500.0, "gross_quantity": 100.0}]
    # Unit cost is >= 500. Custom selling price = 400 (loss-making)
    res = calculate_manufacturing_cost(
        production_quantity=100.0,
        material_costs_breakdown=materials,
        custom_selling_price_per_unit=400.0
    )
    assert res["unit_economics"]["is_loss_making"] is True
    assert res["unit_economics"]["projected_gross_profit"] < 0

def test_what_if_simulation_without_baseline_mutation():
    baseline = {
        "production_quantity": 500.0,
        "material_costs_breakdown": [{"material_name": "Steel", "unit_cost": 315.0, "gross_quantity": 1050.0}],
        "direct_labor_hours": 120.0,
        "labor_rate_per_hour": 180.0,
        "machine_hours": 45.0,
        "machine_rate_per_hour": 350.0,
        "target_gross_margin_pct": 25.0
    }

    # Simulate: Negotiated steel price down to ₹290.0/kg and reduced labor hours to 100h
    overrides = {
        "material_costs_breakdown": [{"material_name": "Steel", "unit_cost": 290.0, "gross_quantity": 1050.0}],
        "direct_labor_hours": 100.0
    }

    sim = run_what_if_simulation(baseline, overrides)
    assert "baseline" in sim
    assert "simulated" in sim
    assert "variance" in sim

    # Cost should be reduced
    assert sim["variance"]["is_cost_reduced"] is True
    assert sim["variance"]["delta_total_batch_cost"] < 0
    # Confirm baseline material price was NOT mutated
    assert baseline["material_costs_breakdown"][0]["unit_cost"] == 315.0

# -------------------------------------------------------------
# 5. End-to-End API Routes Tests (Part 11)
# -------------------------------------------------------------

def test_api_products_crud(client):
    code = f"PROD-TEST-{int(datetime.utcnow().timestamp())}"
    # Create Product
    res = client.post("/api/v1/products", json={
        "code": code,
        "name": "Precision Flange Assembly",
        "category": "Flanges",
        "manufacturing_process": "CNC Turning & Broaching",
        "base_unit": "units",
        "default_batch_size": 250.0
    })
    assert res.status_code == 201
    prod = res.json()
    assert prod["code"] == code

    # List Products
    list_res = client.get("/api/v1/products")
    assert list_res.status_code == 200
    assert any(p["code"] == code for p in list_res.json())

    # Patch Product
    patch_res = client.patch(f"/api/v1/products/{prod['id']}", json={"default_batch_size": 300.0})
    assert patch_res.status_code == 200
    assert patch_res.json()["default_batch_size"] == 300.0

def test_api_boms_endpoints(client, db):
    org_id = "org_tech4bharat_induspilot_demo"
    mat = db.query(Material).filter(Material.organization_id == org_id).first()

    # Create isolated product for this BOM test
    p_code = f"PROD-BOMTEST-{uuid.uuid4().hex[:6]}"
    p_res = client.post("/api/v1/products", json={
        "code": p_code,
        "name": "BOM Test Assembly",
        "category": "Test Components",
        "manufacturing_process": "Assembly",
        "base_unit": "units"
    })
    prod_id = p_res.json()["id"]

    # Create new BOM
    bom_res = client.post("/api/v1/boms", json={
        "product_id": prod_id,
        "name": "Alternative Assembly BOM",
        "version": "v1.2",
        "scrap_allowance_method": "ADDITIVE_SCRAP",
        "items": [
            {"material_id": mat.id, "quantity_per_unit": 1.5, "unit": "kg", "wastage_pct": 4.0}
        ]
    })
    assert bom_res.status_code == 201
    bom_data = bom_res.json()
    assert bom_data["version"] == "v1.2"

    # Validate BOM
    val_res = client.post(f"/api/v1/boms/{bom_data['id']}/validate")
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

def test_api_inventory_endpoints(client, db):
    org_id = "org_tech4bharat_induspilot_demo"
    mat = db.query(Material).filter(Material.organization_id == org_id, Material.code == "MAT-SS-304").first()
    inv = get_or_create_inventory(db, org_id, mat.id)
    initial_stock = inv.current_stock

    try:
        # Receive
        rec_res = client.post("/api/v1/inventory/receive", json={
            "material_id": mat.id,
            "quantity": 50.0,
            "unit": "kg",
            "reference_id": f"PO-API-{uuid.uuid4().hex[:6]}"
        })
        assert rec_res.status_code == 201
        assert rec_res.json()["received_quantity"] == 50.0

        # Alerts
        alt_res = client.get("/api/v1/inventory/alerts")
        assert alt_res.status_code == 200
        assert "alerts" in alt_res.json()

        # Movements
        mov_res = client.get(f"/api/v1/inventory/movements?material_id={mat.id}")
        assert mov_res.status_code == 200
        assert len(mov_res.json()) >= 1
    finally:
        db.expire_all()
        inv_restore = db.query(Inventory).filter(Inventory.material_id == mat.id, Inventory.organization_id == org_id).first()
        if inv_restore:
            inv_restore.current_stock = initial_stock
            db.commit()

def test_api_production_job_mrp_flow(client, db):
    org_id = "org_tech4bharat_induspilot_demo"
    prod = db.query(Product).filter(Product.organization_id == org_id).first()

    # 1. Create Job
    job_res = client.post("/api/v1/production/jobs", json={
        "product_id": prod.id,
        "production_quantity": 500.0,
        "customer_order_ref": "CUST-PO-991"
    })
    assert job_res.status_code == 201
    job = job_res.json()
    job_id = job["id"]

    # 2. Run Material Check (MRP)
    check_res = client.post(f"/api/v1/production/jobs/{job_id}/material-check")
    assert check_res.status_code == 200
    check_data = check_res.json()
    assert "shortages_count" in check_data
    assert len(check_data["requirements"]) > 0

    # 3. Procurement Handoff
    handoff_res = client.post(f"/api/v1/production/jobs/{job_id}/procurement-handoff")
    assert handoff_res.status_code == 200
    handoff_data = handoff_res.json()
    assert "job_status" in handoff_data or "new_job_status" in handoff_data

def test_api_costing_estimate_and_simulate(client, db):
    org_id = "org_tech4bharat_induspilot_demo"
    prod = db.query(Product).filter(Product.organization_id == org_id).first()
    mat = db.query(Material).filter(Material.organization_id == org_id).first()

    # 1. Calculate & Persist Estimate
    est_res = client.post("/api/v1/costing/estimate", json={
        "product_id": prod.id,
        "production_quantity": 500.0,
        "material_costs_breakdown": [
            {"material_name": mat.name, "unit_cost": 315.0, "gross_quantity": 1050.0}
        ],
        "direct_labor_hours": 120.0,
        "labor_rate_per_hour": 180.0,
        "machine_hours": 45.0,
        "machine_rate_per_hour": 350.0,
        "overhead_method": "PERCENTAGE_PRIME_COST",
        "target_gross_margin_pct": 25.0,
        "save_estimate": True
    })
    assert est_res.status_code == 200
    est_data = est_res.json()
    assert "saved_estimate_id" in est_data
    estimate_id = est_data["saved_estimate_id"]

    # 2. What-If Simulation
    sim_res = client.post("/api/v1/costing/simulate", json={
        "baseline_estimate_id": estimate_id,
        "simulation_overrides": {
            "labor_rate_per_hour": 160.0 # 20 INR/hr cheaper labor
        }
    })
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["variance"]["is_cost_reduced"] is True
