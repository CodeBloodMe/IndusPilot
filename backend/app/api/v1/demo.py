from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.seed_data import seed_induspilot_demonstration_data

router = APIRouter()

@router.post("/seed")
def seed_demo_environment(
    force_reset: bool = False,
    db: Session = Depends(get_db)
):
    """
    Seeds comprehensive synthetic demonstration data for the Tech4Bharat 2026 hackathon.
    """
    res = seed_induspilot_demonstration_data(db, force_reset=force_reset)
    return res

@router.get("/scenario")
def get_hackathon_demo_scenario():
    """
    Returns step-by-step guidance for the canonical 500 Stainless Steel Industrial Brackets demonstration.
    """
    return {
        "title": "Canonical Tech4Bharat 2026 Showcase: 500 SS304 Industrial Brackets",
        "description": (
            "Demonstrates the full closed-loop manufacturing procurement and quotation intelligence: "
            "from customer requirement, BOM explosion, inventory netting, OCR quotation extraction, "
            "explainable supplier scoring, OR-Tools optimization, negotiation counteroffers, "
            "to 14-factor manufacturing costing and customer quotation generation."
        ),
        "steps": [
            {
                "step": 1,
                "title": "Order & BOM Requirement",
                "action": "Customer requests 500 Stainless Steel 304 Industrial Brackets. BOM explosion calculates 1,050 kg gross requirement (including 5% scrap)."
            },
            {
                "step": 2,
                "title": "Inventory Audit & Shortage Detection",
                "action": "Existing warehouse inventory holds 250 kg (50 kg reserved). Net shortage calculated at exactly 800 kg. Purchase requisition PR-2026-OCT-001 created."
            },
            {
                "step": 3,
                "title": "Document Intelligence Ingestion",
                "action": "Upload 3 vendor quotation PDFs (Apex Steel, Bharat Forgings, Deccan Precision). PyMuPDF & Quality Gate automatically extract prices, MOQs, freight, and tax terms."
            },
            {
                "step": 4,
                "title": "Explainable Supplier Comparison",
                "action": "IndusPilot scores candidates across 5 weighted dimensions (Landed Cost, Quality, Reliability, Lead Time, Payment). Apex Steel recommended (Score: 84.8/100)."
            },
            {
                "step": 5,
                "title": "Autonomous Negotiation & Counteroffer",
                "action": "Negotiation Agent identifies ₹20/kg margin opportunity. Drafts evidence-backed counteroffer proposing ₹295/kg with 15-day payment terms. Requires human approval."
            },
            {
                "step": 6,
                "title": "Simulated Vendor Response",
                "action": "Apex Steel compromises to ₹305/kg (saving ₹8,000 on the batch). Deal closed with explicit user approval."
            },
            {
                "step": 7,
                "title": "OR-Tools Procurement Optimization",
                "action": "Google OR-Tools MILP solver evaluates capacity and budget constraints, generating mathematically optimal purchase allocations."
            },
            {
                "step": 8,
                "title": "14-Factor Manufacturing Costing",
                "action": "Deterministic Decimal engine computes raw material, scrap, operator labor, machine time, electricity kWh, and overheads. Cost per bracket: ₹637.00."
            },
            {
                "step": 9,
                "title": "Customer Quotation Generation & PDF Export",
                "action": "Builds commercial customer quotation at ₹850/bracket (25.1% margin). Exports industrial-grade PDF quote with zero risk of loss-making underpricing."
            }
        ]
    }

