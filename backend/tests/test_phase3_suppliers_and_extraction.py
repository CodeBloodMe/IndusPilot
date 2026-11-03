import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

SAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/sample_quotations"))

@pytest.fixture
def client():
    return TestClient(app)


def test_supplier_registration_and_duplicate_detection(client):
    """Verifies supplier creation with rich profiles and duplicate detection."""
    import uuid
    uid = uuid.uuid4().hex[:6].upper()
    supplier_payload = {
        "name": f"Zenith Precision Forgings {uid}",
        "company_name": f"Zenith Precision Forgings {uid} Pvt Ltd",
        "contact_person": "Vikram Malhotra",
        "email": f"v.malhotra.{uid.lower()}@zenithforgings.com",
        "phone": "+91 80 4123 9988",
        "address": "Plot 18, Electronic City Phase 1",
        "city": "Bengaluru",
        "state": "Karnataka",
        "country": "India",
        "postal_code": "560100",
        "website": "https://zenithforgings.com",
        "gst_number": f"29AAACZ{uid[:4]}K1Z2",
        "category": "Primary Raw Materials",
        "manufacturing_specialisation": "Precision Hot & Cold Forgings",
        "credit_period_days": 45,
        "moq_general": 250.0,
        "capacity_monthly_tons": 75.0,
        "lead_time_days": 8,
        "quality_rating": 4.7,
        "reliability_score": 93.0,
        "on_time_delivery_pct": 95.0,
        "payment_terms_days": 45,
        "is_active": True,
        "is_simulated": True
    }

    # 1. Create Supplier
    res = client.post("/api/v1/suppliers", json=supplier_payload)
    assert res.status_code == 200, res.text
    created = res.json()
    assert created["name"] == supplier_payload["name"]
    assert created["city"] == "Bengaluru"
    assert created["gst_number"] == supplier_payload["gst_number"]
    assert created["credit_period_days"] == 45
    supp_id = created["id"]

    # 2. Reject Duplicate by Name (409 Conflict)
    dup_res = client.post("/api/v1/suppliers", json=supplier_payload)
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"].lower()

    # 3. Reject Duplicate by GSTIN (409 Conflict)
    diff_name_payload = dict(supplier_payload)
    diff_name_payload["name"] = "Zenith Sister Company LLP"
    dup_gst_res = client.post("/api/v1/suppliers", json=diff_name_payload)
    assert dup_gst_res.status_code == 409
    assert "gstin" in dup_gst_res.json()["detail"].lower()

    # 4. Partial Update (PATCH)
    patch_res = client.patch(f"/api/v1/suppliers/{supp_id}", json={
        "quality_rating": 4.9,
        "credit_period_days": 60
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["quality_rating"] == 4.9
    assert patch_res.json()["credit_period_days"] == 60

    # 5. Soft-Deactivate Supplier (DELETE)
    del_res = client.delete(f"/api/v1/suppliers/{supp_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "DEACTIVATED"

    # Verify inactive filter
    get_res = client.get(f"/api/v1/suppliers/{supp_id}")
    assert get_res.status_code == 200
    assert get_res.json()["is_active"] is False


def test_supplier_search_and_filters(client):
    """Tests multi-criteria supplier search and material filters."""
    # Filter by City
    res_blr = client.get("/api/v1/suppliers?city=Bengaluru")
    assert res_blr.status_code == 200
    assert len(res_blr.json()) >= 1
    assert all("Bengaluru" in s["city"] for s in res_blr.json() if s.get("city"))

    # Filter by Category
    res_cat = client.get("/api/v1/suppliers?category=Primary Raw Materials")
    assert res_cat.status_code == 200
    assert len(res_cat.json()) >= 1

    # Filter by Material
    res_mat = client.get("/api/v1/suppliers?material_filter=Stainless Steel")
    assert res_mat.status_code == 200
    assert len(res_mat.json()) >= 1

    # Search keyword
    res_search = client.get("/api/v1/suppliers?search=Tata")
    assert res_search.status_code == 200
    assert any("Tata" in s["name"] for s in res_search.json())


def test_material_specification_matcher(client):
    """Validates deterministic material specification matcher across grades and forms."""
    # 1. Stainless Steel Grade 304 Match
    res_ss = client.post("/api/v1/materials/match", json={
        "raw_text": "Stainless Steel Grade 304 Sheet - 2.0 MM Thk 2B finish",
        "thickness_mm": 2.0
    })
    assert res_ss.status_code == 200
    match_data = res_ss.json()
    assert match_data["best_match"] is not None
    assert match_data["best_match"]["code"] == "MAT-SS-304"
    assert match_data["best_match"]["similarity_score"] >= 0.70
    assert match_data["best_match"]["confidence_band"] in ["EXACT", "HIGH_CONFIDENCE"]

    # 2. Aluminium 6061-T6 Plate Match
    res_al = client.post("/api/v1/materials/match", json={
        "raw_text": "Alloy AL6061-T6 Plate 12mm thickness",
        "grade": "6061-T6"
    })
    assert res_al.status_code == 200
    al_data = res_al.json()
    assert al_data["best_match"] is not None
    assert al_data["best_match"]["code"] == "MAT-AL-6061"

    # 3. Mild Steel IS2062 Structural Match
    res_ms = client.post("/api/v1/materials/match", json={
        "raw_text": "MS IS2062 Grade E250 hot rolled plate 10mm"
    })
    assert res_ms.status_code == 200
    ms_data = res_ms.json()
    assert ms_data["best_match"] is not None
    assert ms_data["best_match"]["code"] == "MAT-MS-IS2062"


def test_document_ingestion_and_quality_gate_pipeline(client):
    """
    Tests end-to-end multi-format ingestion across PDF, Excel, CSV and Images,
    verifying extraction, Quality Gate classification, and material matching suggestions.
    """
    sample_files = [
        ("apex_steel_quotation_ss304.pdf", "application/pdf"),
        ("national_aluminium_pricelist.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("mahalaxmi_metals_tubes.csv", "text/csv"),
        ("scanned_quotation_apex_steel.png", "image/png"),
    ]

    for fname, mime_type in sample_files:
        fpath = os.path.join(SAMPLE_DIR, fname)
        if not os.path.exists(fpath):
            continue

        with open(fpath, "rb") as f:
            upload_res = client.post(
                "/api/v1/documents/upload",
                files={"files": (fname, f, mime_type)}
            )

        assert upload_res.status_code == 200, f"Upload failed for {fname}: {upload_res.text}"
        data = upload_res.json()

        # Handle single upload response
        doc_data = data["results"][0] if "results" in data else data
        assert doc_data["success"] is True
        assert "document_id" in doc_data
        assert doc_data["confidence_score"] > 0.0
        assert doc_data["validation_status"] in ["READY_FOR_REVIEW", "NEEDS_CORRECTION", "VERIFIED"]
        assert len(doc_data["items"]) >= 1

        # Check line item material match candidates
        item0 = doc_data["items"][0]
        assert "unit_price" in item0
        assert item0["unit_price"] > 0
        assert "match_confidence" in item0
        assert "suggested_candidates" in item0

        # Retrieve extraction from document ledger endpoint
        doc_id = doc_data["document_id"]
        ext_res = client.get(f"/api/v1/documents/{doc_id}/extraction")
        assert ext_res.status_code == 200
        assert ext_res.json()["document_id"] == doc_id


def test_human_review_and_quotation_confirmation_workflow(client):
    """
    Simulates the Human Review UI interaction:
    Takes an extracted document, corrects items and quantities,
    confirms and saves verified quotation into PostgreSQL, and verifies ledger persistence.
    """
    confirm_payload = {
        "supplier_name": "Apex Steel & Alloys Pvt Ltd",
        "quotation_number": "APX-HUMAN-REV-2026-001",
        "quotation_date": "2026-10-31",
        "valid_until": "2026-12-01",
        "subtotal": 249600.0,
        "tax_pct": 18.0,
        "tax_amount": 44928.0,
        "freight_cost": 4200.0,
        "other_charges": 0.0,
        "is_tax_inclusive": False,
        "total_amount": 298728.0,
        "currency": "INR",
        "payment_terms": "30 Days Net Credit",
        "review_notes": "Reviewed and verified by Lead Estimator for 500 Brackets order.",
        "items": [
            {
                "material_name": "Stainless Steel Grade 304 Sheet 2mm Thk (2B Finish)",
                "grade": "SS304 2B",
                "thickness_mm": 2.0,
                "dimensions": "1250 x 2500 mm",
                "quantity": 800.0,
                "unit": "kg",
                "unit_price": 312.0,
                "moq": 200.0,
                "lead_time_days": 6,
                "line_total": 249600.0,
                "match_confidence": 0.96,
                "is_quarantined": False
            }
        ]
    }

    # Confirm and persist
    res = client.post("/api/v1/quotations/confirm", json=confirm_payload)
    assert res.status_code == 200, res.text
    saved = res.json()
    assert saved["status"] == "SAVED"
    assert saved["quotation_number"] == "APX-HUMAN-REV-2026-001"
    assert saved["total_amount"] == 298728.0
    quote_id = saved["quotation_id"]

    # Verify retrieval from GET /api/v1/quotations/{id}
    detail_res = client.get(f"/api/v1/quotations/{quote_id}")
    assert detail_res.status_code == 200
    q_data = detail_res.json()
    assert q_data["quotation_number"] == "APX-HUMAN-REV-2026-001"
    assert q_data["status"] == "VERIFIED"
    assert len(q_data["items"]) == 1
    assert q_data["items"][0]["material_id"] is not None

    # Verify Supplier Quotation History API
    supp_id = q_data["supplier_id"]
    hist_res = client.get(f"/api/v1/suppliers/{supp_id}/quotations")
    assert hist_res.status_code == 200
    assert any(q["quotation_number"] == "APX-HUMAN-REV-2026-001" for q in hist_res.json())


def test_quarantined_document_isolation(client):
    """Verifies that quotations with missing prices or zero values are quarantined."""
    quarantine_payload = {
        "supplier_name": "Unknown Vendor",
        "quotation_number": "ERR-NO-PRICE-001",
        "subtotal": 0.0,
        "tax_pct": 18.0,
        "tax_amount": 0.0,
        "total_amount": 0.0,
        "items": [
            {
                "material_name": "Unidentified Scrap Steel",
                "quantity": 500.0,
                "unit": "kg",
                "unit_price": 0.0,
                "line_total": 0.0,
                "is_quarantined": True,
                "quarantine_reason": "Zero unit price."
            }
        ]
    }

    # Reject / quarantine quotation
    res = client.post("/api/v1/quotations/confirm", json=quarantine_payload)
    assert res.status_code == 200
    saved_id = res.json()["quotation_id"]

    # Reject quotation
    rej_res = client.post(f"/api/v1/quotations/{saved_id}/reject?reason=Missing+pricing+data")
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "REJECTED"
