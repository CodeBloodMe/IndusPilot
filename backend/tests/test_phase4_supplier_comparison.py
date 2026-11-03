import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app

from app.calculations.landed_cost import (
    calculate_landed_cost, allocate_charges_across_items, convert_units, TaxTreatment
)
from app.calculations.scoring import evaluate_supplier_quotation
from app.services.eligibility_engine import evaluate_supplier_eligibility, EligibilityStatus
from app.services.decision_explainer import generate_procurement_decision_explanation
from app.services.ocr_engine import get_ocr_engine_status

@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. TOTAL LANDED COST CALCULATION ENGINE TESTS (DETERMINISTIC DECIMAL)
# ==============================================================================

def test_landed_cost_tax_exclusive():
    """Verify GST-exclusive pricing calculation: Base = Net, GST = Base * 18%"""
    res = calculate_landed_cost(
        unit_price=300.0,
        quantity=500.0,
        tax_pct=18.0,
        tax_treatment=TaxTreatment.TAX_EXCLUDED,
        freight_total=4000.0,
        packaging_total=1500.0,
        other_charges_total=500.0
    )
    # Gross = 300 * 500 = 150,000
    assert res["gross_material_cost"] == 150000.0
    assert res["material_base_cost"] == 150000.0
    # Tax = 150,000 * 0.18 = 27,000
    assert res["tax_amount"] == 27000.0
    # Freight + Packaging + Other = 4000 + 1500 + 500 = 6000
    # Total = 150,000 + 27,000 + 6,000 = 183,000
    assert res["total_landed_cost"] == 183000.0
    # Effective Unit = 183,000 / 500 = 366.0
    assert res["effective_unit_landed_cost"] == 366.0
    assert res["is_tax_inclusive"] is False


def test_landed_cost_tax_inclusive_no_double_counting():
    """Verify GST-inclusive pricing: Base = Net / 1.18, Tax = Net - Base. Prevents double-counting tax."""
    res = calculate_landed_cost(
        unit_price=354.0, # 300 base + 54 GST
        quantity=100.0,
        tax_pct=18.0,
        tax_treatment=TaxTreatment.TAX_INCLUDED,
        freight_total=2000.0
    )
    # Net material = 35,400 (inclusive of 18% tax)
    # Base = 35,400 / 1.18 = 30,000.00
    assert res["material_base_cost"] == 30000.0
    # Tax = 35,400 - 30,000 = 5,400.00
    assert res["tax_amount"] == 5400.0
    # Total = 30,000 + 5,400 + 2,000 = 37,400.00
    assert res["total_landed_cost"] == 37400.0
    assert res["effective_unit_landed_cost"] == 374.0
    assert res["is_tax_inclusive"] is True


def test_landed_cost_zero_tax_and_discounts():
    """Verify zero-tax treatment and commercial percentage discounts."""
    res = calculate_landed_cost(
        unit_price=200.0,
        quantity=100.0,
        tax_pct=0.0,
        tax_treatment=TaxTreatment.NO_TAX,
        discount_pct=5.0, # 5% volume discount
        freight_total=1000.0
    )
    # Gross = 20,000. Discount = 1,000. Base = 19,000. Tax = 0.
    assert res["gross_material_cost"] == 20000.0
    assert res["discount_amount"] == 1000.0
    assert res["material_base_cost"] == 19000.0
    assert res["tax_amount"] == 0.0
    assert res["total_landed_cost"] == 20000.0 # 19,000 + 1,000 freight
    assert res["effective_unit_landed_cost"] == 200.0


def test_landed_cost_unknown_tax_blocked():
    """Ensure UNKNOWN tax treatment strictly raises ValueError instead of silent assumptions."""
    with pytest.raises(ValueError, match="Tax treatment is unstated or UNKNOWN"):
        calculate_landed_cost(
            unit_price=300.0,
            quantity=100.0,
            tax_treatment=TaxTreatment.UNKNOWN
        )


def test_landed_cost_multi_item_freight_allocation():
    """Verify multi-item freight allocation using pro-rata value and weight methods."""
    items = [
        {"material_name": "Heavy Steel Plate", "unit_price": 70.0, "quantity": 1000.0}, # Val: 70,000
        {"material_name": "Precision Bolt Pack", "unit_price": 300.0, "quantity": 100.0} # Val: 30,000
    ]
    # Total value = 100,000 (Item 1 = 70%, Item 2 = 30%)
    allocated = allocate_charges_across_items(items, total_freight=10000.0, method="PRO_RATA_VALUE")
    assert len(allocated) == 2
    assert allocated[0]["allocated_freight"] == 7000.0
    assert allocated[1]["allocated_freight"] == 3000.0


def test_landed_cost_currency_conversion():
    """Verify currency conversion with foreign exchange rate."""
    res = calculate_landed_cost(
        unit_price=10.0, # in USD
        quantity=50.0,
        currency="USD",
        base_currency="INR",
        fx_rate_to_base=83.50,
        freight_total=50.0 # 50 USD
    )
    # Landed USD = 500 (mat) + 90 (18% tax) + 50 (freight) = 640 USD
    # In INR = 640 * 83.50 = 53,440 INR
    assert res["total_landed_cost"] == 53440.0
    assert res["currency"] == "INR"
    assert res["original_currency"] == "USD"


def test_unit_conversions():
    """Verify mass unit conversions."""
    assert convert_units(2.5, "ton", "kg") == 2500.0
    assert convert_units(500.0, "kg", "ton") == 0.5
    assert convert_units(100.0, "kg", "kg") == 100.0
    with pytest.raises(ValueError, match="Incompatible or unsupported"):
        convert_units(10.0, "kg", "meter")


# ==============================================================================
# 2. SUPPLIER ELIGIBILITY ENGINE TESTS
# ==============================================================================

def test_eligibility_exact_grade_and_dimensions():
    """Validates that matching grade and thickness yields ELIGIBLE status."""
    req = {
        "material_name": "Stainless Steel 304 Sheet",
        "grade": "SS304",
        "thickness_mm": 2.0,
        "quantity": 800.0,
        "unit": "kg",
        "delivery_deadline": (datetime.utcnow() + timedelta(days=15)).isoformat()
    }
    quote = {
        "quotation_number": "Q-001",
        "valid_until": (datetime.utcnow() + timedelta(days=20)).isoformat(),
        "is_quarantined": False,
        "items": [{
            "material_name_raw": "Stainless Steel 304 Sheet 2mm",
            "grade": "SS304 2B",
            "thickness_mm": 2.0,
            "unit": "kg",
            "unit_price": 315.0,
            "moq": 200.0,
            "lead_time_days": 6
        }]
    }
    sup = {"capacity_monthly_tons": 50.0}

    eval_res = evaluate_supplier_eligibility(req, quote, sup)
    assert eval_res["status"] == EligibilityStatus.ELIGIBLE
    assert eval_res["is_eligible"] is True
    assert len(eval_res["ineligibility_reasons"]) == 0


def test_eligibility_grade_mismatch_fatal():
    """Verify that SS316 cannot be substituted for SS304 without failing compatibility."""
    req = {
        "material_name": "Stainless Steel 304 Sheet Plate",
        "grade": "SS304",
        "quantity": 500.0
    }
    quote = {
        "quotation_number": "Q-316",
        "is_quarantined": False,
        "items": [{
            "material_name_raw": "Stainless Steel 316 Marine Plate",
            "grade": "SS316 Acid Resistant",
            "unit_price": 430.0,
            "unit": "kg"
        }]
    }
    eval_res = evaluate_supplier_eligibility(req, quote)
    assert eval_res["status"] == EligibilityStatus.INELIGIBLE
    assert eval_res["is_eligible"] is False
    assert any("Fatal Grade Mismatch" in r for r in eval_res["ineligibility_reasons"])


def test_eligibility_thickness_mismatch():
    """Verify that a 5mm plate is marked INELIGIBLE when specification demands 2mm."""
    req = {
        "material_name": "Stainless Steel 304 Sheet",
        "grade": "SS304",
        "thickness_mm": 2.0,
        "quantity": 500.0
    }
    quote = {
        "quotation_number": "Q-5MM",
        "is_quarantined": False,
        "items": [{
            "material_name_raw": "SS 304 Heavy Plate 5mm",
            "grade": "SS304",
            "thickness_mm": 5.0, # 5mm vs 2mm
            "unit_price": 310.0,
            "unit": "kg"
        }]
    }
    eval_res = evaluate_supplier_eligibility(req, quote)
    assert eval_res["status"] == EligibilityStatus.INELIGIBLE
    assert any("Thickness Mismatch" in r for r in eval_res["ineligibility_reasons"])


def test_eligibility_expired_quotation():
    """Verify that quotations past valid_until date are rejected as INELIGIBLE."""
    req = {"material_name": "SS 304 Sheet", "grade": "SS304", "quantity": 100.0}
    quote = {
        "quotation_number": "Q-EXPIRED",
        "valid_until": (datetime.utcnow() - timedelta(days=5)).isoformat(), # Expired 5 days ago
        "is_quarantined": False,
        "items": [{"material_name_raw": "SS304 Sheet", "grade": "SS304", "unit_price": 300.0, "unit": "kg"}]
    }
    eval_res = evaluate_supplier_eligibility(req, quote)
    assert eval_res["status"] == EligibilityStatus.INELIGIBLE
    assert any("Expired" in r for r in eval_res["ineligibility_reasons"])


def test_eligibility_quarantined_exclusion():
    """Verify that quarantined quotations are blocked immediately."""
    req = {"material_name": "SS 304 Sheet", "quantity": 100.0}
    quote = {
        "quotation_number": "Q-QUARANTINED",
        "is_quarantined": True,
        "quarantine_reasons": ["Unverified supplier", "Zero item price detected"],
        "items": []
    }
    eval_res = evaluate_supplier_eligibility(req, quote)
    assert eval_res["status"] == EligibilityStatus.INELIGIBLE
    assert eval_res["is_eligible"] is False


def test_eligibility_delivery_deadline_exceeded():
    """Verify lead time exceeding deadline threshold causes ineligibility."""
    req = {
        "material_name": "SS 304 Sheet",
        "grade": "SS304",
        "quantity": 100.0,
        "max_lead_time_days": 5 # Must deliver in 5 days
    }
    quote = {
        "quotation_number": "Q-SLOW",
        "is_quarantined": False,
        "items": [{
            "material_name_raw": "SS 304 Sheet",
            "grade": "SS304",
            "unit_price": 290.0,
            "unit": "kg",
            "lead_time_days": 14 # 14 days exceeds 5 days
        }]
    }
    eval_res = evaluate_supplier_eligibility(req, quote)
    assert eval_res["status"] == EligibilityStatus.INELIGIBLE
    assert any("Lead Time Exceeded" in r for r in eval_res["ineligibility_reasons"])


# ==============================================================================
# 3. EXPLAINABLE 5-FACTOR SUPPLIER SCORING TESTS
# ==============================================================================

def test_scoring_cheapest_supplier_gets_top_cost_score():
    """Verify that lowest landed cost gets 100 in cost competitiveness."""
    all_costs = [350.0, 380.0, 420.0]
    score_res = evaluate_supplier_quotation(
        unit_landed_cost=350.0,
        all_landed_costs=all_costs,
        quality_rating=4.5,
        reliability_score=90.0,
        lead_time_days=6,
        all_lead_times=[6, 8, 12],
        payment_terms_days=30
    )
    assert score_res["sub_scores"]["cost_competitiveness"] == 100.0
    assert score_res["data_completeness_pct"] == 100.0
    assert score_res["decision_band"] == "STRONGLY_RECOMMENDED"


def test_scoring_missing_data_weight_renormalization():
    """Verify missing vendor history transparently renormalizes active weights and reports gaps."""
    all_costs = [350.0, 400.0]
    score_res = evaluate_supplier_quotation(
        unit_landed_cost=350.0,
        all_landed_costs=all_costs,
        quality_rating=None, # Missing quality records!
        reliability_score=None, # Missing reliability history!
        lead_time_days=7,
        all_lead_times=[7, 10],
        payment_terms_days=30
    )
    # 2 of 5 metrics missing: completeness is 60%
    assert score_res["data_completeness_pct"] == 60.0
    assert "quality" in score_res["missing_factors"]
    assert "delivery_reliability" in score_res["missing_factors"]
    # Total active weight was 0.35 (cost) + 0.15 (lead) + 0.10 (payment) = 0.60
    # Renormalized cost weight = 0.35 / 0.60 = 0.5833
    assert pytest.approx(score_res["renormalized_weights"]["cost_competitiveness"], 0.01) == 0.5833
    assert sum(score_res["renormalized_weights"].values()) == pytest.approx(1.0, 0.01)


def test_scoring_low_evidence_provisional_tag():
    """Verify that when evidence completeness < 60%, decision band is LOW_EVIDENCE_PROVISIONAL."""
    score_res = evaluate_supplier_quotation(
        unit_landed_cost=320.0,
        all_landed_costs=[320.0],
        quality_rating=None,
        reliability_score=None,
        lead_time_days=None,
        payment_terms_days=None
    )
    # Only 1 of 5 factors available (20% completeness)
    assert score_res["data_completeness_pct"] == 20.0
    assert score_res["decision_band"] == "LOW_EVIDENCE_PROVISIONAL"


def test_decision_explanation_generation():
    """Verify structured decision explanation generation."""
    cand_apex = {
        "supplier_id": "sup-apex",
        "supplier_name": "Apex Steel & Alloys Pvt Ltd",
        "composite_score": 88.5,
        "effective_unit_landed_cost": 377.33,
        "total_landed_cost": 301860.0,
        "lead_time_days": 6,
        "quality_rating": 4.6,
        "reliability_score": 92.0,
        "scorecard": {"data_completeness_pct": 100.0, "missing_factors": []},
        "eligibility": {"conditions": [], "warnings": []}
    }
    cand_bharat = {
        "supplier_id": "sup-bharat",
        "supplier_name": "Bharat Forgings & Metals",
        "composite_score": 80.2,
        "effective_unit_landed_cost": 359.14,
        "total_landed_cost": 287312.0,
        "lead_time_days": 12,
        "quality_rating": 4.0,
        "reliability_score": 78.0
    }

    explanation = generate_procurement_decision_explanation(
        recommended_candidate=cand_apex,
        all_candidates=[cand_apex, cand_bharat],
        cheapest_candidate=cand_bharat,
        fastest_candidate=cand_apex,
        target_quantity=800.0,
        material_name="Stainless Steel 304 Sheet"
    )

    assert "Apex Steel" in explanation["summary_headline"]
    assert "88.5/100" in explanation["summary_headline"]
    assert "Bharat Forgings" in explanation["concise_recommendation"]
    assert len(explanation["detailed_explanation"]) > 200
    assert len(explanation["key_tradeoffs"]) == 3


# ==============================================================================
# 4. FULL API ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_api_comparison_analyze(client):
    """Integration test for POST /api/v1/comparisons/analyze with material filter."""
    res = client.post("/api/v1/comparisons/analyze", json={
        "material_name": "Stainless Steel 304 Sheet Plate",
        "grade": "SS304",
        "quantity": 800.0,
        "unit": "kg",
        "save_comparison": True
    })
    assert res.status_code == 200
    data = res.json()

    assert data["compared_quotations_count"] >= 3
    assert data["eligible_candidates_count"] >= 1
    assert "recommended_candidate" in data
    assert "highlights" in data
    assert "explanation" in data

    rec = data["recommended_candidate"]
    assert rec["composite_score"] > 70.0
    assert rec["effective_unit_landed_cost"] > 0
    assert data["comparison_id"] is not None

    # Retrieve saved comparison by ID
    comp_id = data["comparison_id"]
    get_res = client.get(f"/api/v1/comparisons/{comp_id}")
    assert get_res.status_code == 200
    saved_data = get_res.json()
    assert saved_data["comparison_id"] == comp_id
    assert len(saved_data["candidates"]) >= 1


def test_api_quotation_eligibility_endpoint(client):
    """Integration test for POST /api/v1/comparisons/eligibility."""
    # Fetch a quotation
    quotes = client.get("/api/v1/quotations?status=VERIFIED").json()
    first_q = quotes[0]

    res = client.post("/api/v1/comparisons/eligibility", json={
        "quotation_id": first_q["id"],
        "material_name": first_q["items"][0]["material_name"],
        "grade": first_q["items"][0].get("grade"),
        "quantity": 500.0
    })
    assert res.status_code == 200
    eval_res = res.json()
    assert "status" in eval_res
    assert "constraint_checks" in eval_res


def test_api_landed_cost_endpoint(client):
    """Integration test for POST /api/v1/comparisons/landed-cost."""
    res = client.post("/api/v1/comparisons/landed-cost", json={
        "unit_price": 315.0,
        "quantity": 800.0,
        "tax_pct": 18.0,
        "tax_treatment": "TAX_EXCLUDED",
        "freight_total": 4500.0,
        "packaging_total": 1200.0
    })
    assert res.status_code == 200
    data = res.json()
    # Gross = 252,000, Tax = 45,360, Freight = 4,500, Packaging = 1,200. Total = 303,060
    assert data["gross_material_cost"] == 252000.0
    assert data["tax_amount"] == 45360.0
    assert data["total_landed_cost"] == 303060.0
    assert pytest.approx(data["effective_unit_landed_cost"], 0.01) == 378.83


def test_api_material_price_history(client):
    """Integration test for GET /api/v1/materials/{material_id}/price-history."""
    materials = client.get("/api/v1/materials").json()
    ss304 = next(m for m in materials if "SS-304" in m["code"])

    hist_res = client.get(f"/api/v1/materials/{ss304['id']}/price-history")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["material_id"] == ss304["id"]
    assert hist_data["price_history_records_count"] >= 3
    assert len(hist_data["history"]) >= 3

    # Check tags
    tags = [h["data_type"] for h in hist_data["history"]]
    assert any(t in ["CURRENT_OFFER", "HISTORICAL_QUOTATION", "SIMULATED_DEMO"] for t in tags)


def test_api_supplier_performance(client):
    """Integration test for GET /api/v1/suppliers/{supplier_id}/performance."""
    suppliers = client.get("/api/v1/suppliers").json()
    apex = next(s for s in suppliers if "Apex Steel" in s["name"])

    perf_res = client.get(f"/api/v1/suppliers/{apex['id']}/performance")
    assert perf_res.status_code == 200
    perf_data = perf_res.json()
    assert perf_data["supplier_id"] == apex["id"]
    assert "scorecard" in perf_data
    assert perf_data["scorecard"]["quality_rating"] >= 4.0
    assert "financial_summary" in perf_data
    assert "materials_supplied" in perf_data
    assert "simulation_disclaimer" in perf_data


def test_api_procurement_requisition_flow(client):
    """Integration test for creating and listing formal Purchase Requisitions."""
    materials = client.get("/api/v1/materials").json()
    ss304 = next(m for m in materials if "SS-304" in m["code"])
    suppliers = client.get("/api/v1/suppliers").json()
    apex = next(s for s in suppliers if "Apex Steel" in s["name"])

    # Create Requisition
    create_res = client.post("/api/v1/procurement/requisitions", json={
        "material_id": ss304["id"],
        "required_quantity": 800.0,
        "unit": "kg",
        "reason": "Production Shortage: 500 Mounting Brackets",
        "selected_supplier_id": apex["id"],
        "estimated_total_cost": 301860.0
    })
    assert create_res.status_code == 200
    req_data = create_res.json()
    assert req_data["status"] == "CREATED"
    assert "REQ-2026-" in req_data["requisition_number"]
    assert req_data["quantity"] == 800.0

    # List Requisitions
    list_res = client.get("/api/v1/procurement/requisitions")
    assert list_res.status_code == 200
    all_reqs = list_res.json()
    assert len(all_reqs) >= 1
    created_req = next(r for r in all_reqs if r["id"] == req_data["requisition_id"])
    assert created_req["selected_supplier_id"] == apex["id"]
    assert created_req["status"] == "PENDING"


def test_ocr_subsystem_status(client):
    """Verify that OCR subsystem reports its status and fallback transparently."""
    status = get_ocr_engine_status()
    assert "is_real_ocr_available" in status
    assert "engine_name" in status
    assert "limitation_statement" in status

    # Verify health endpoint exposes OCR status
    health_res = client.get("/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert "ocr_subsystem" in health_data
    assert health_data["ocr_subsystem"]["active_fallback"] is True

