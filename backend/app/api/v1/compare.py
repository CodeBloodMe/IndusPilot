from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_org_id
from app.models.entities import SupplierQuotation, Supplier
from app.schemas.domain import SupplierCompareRequest
from app.calculations.landed_cost import calculate_landed_cost
from app.calculations.scoring import evaluate_supplier_quotation

router = APIRouter()

@router.post("/evaluate")
def evaluate_quotations(
    payload: SupplierCompareRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Evaluates quotations, calculates true landed costs, executes 5-factor scoring,
    and returns ranked recommendations with decision bands.
    """
    query = db.query(SupplierQuotation).filter(
        SupplierQuotation.organization_id == org_id
    )
    if payload.quotation_ids:
        query = query.filter(SupplierQuotation.id.in_(payload.quotation_ids))
    else:
        query = query.filter(SupplierQuotation.status == "VERIFIED")

    quotations = query.all()
    if not quotations:
        raise HTTPException(status_code=400, detail="No quotations found for comparison.")

    target_qty = payload.quantity
    candidate_evaluations = []
    landed_costs_pool = []
    lead_times_pool = []

    # First pass: calculate landed costs & lead times
    for q in quotations:
        sup = q.supplier
        item = q.items[0] if q.items else None
        unit_price = item.unit_price if item else 300.0
        lead_time = item.lead_time_days if item else 7

        landed_data = calculate_landed_cost(
            unit_price=unit_price,
            quantity=target_qty,
            tax_pct=q.tax_pct,
            is_tax_inclusive=q.is_tax_inclusive,
            freight_total=q.freight_cost,
            other_charges_total=q.other_charges
        )

        eff_unit_landed = landed_data["effective_unit_landed_cost"]
        landed_costs_pool.append(eff_unit_landed)
        lead_times_pool.append(lead_time)

        candidate_evaluations.append({
            "quotation_id": q.id,
            "quotation_number": q.quotation_number,
            "supplier_id": sup.id if sup else "N/A",
            "supplier_name": sup.name if sup else "Unknown Vendor",
            "city": sup.city if sup else "",
            "material_name": item.material_name_raw if item else "Industrial Material",
            "material_grade": item.grade if item else "Standard",
            "quantity": target_qty,
            "quoted_unit_price": unit_price,
            "moq": item.moq if item else 1.0,
            "lead_time_days": lead_time,
            "payment_terms_days": sup.payment_terms_days if sup else 30,
            "quality_rating": sup.quality_rating if sup else 4.0,
            "reliability_score": sup.reliability_score if sup else 80.0,
            "landed_cost_breakdown": landed_data,
            "effective_unit_landed_cost": eff_unit_landed,
            "total_landed_cost": landed_data["total_landed_cost"]
        })

    # Second pass: calculate 5-factor scoring
    for cand in candidate_evaluations:
        score_res = evaluate_supplier_quotation(
            unit_landed_cost=cand["effective_unit_landed_cost"],
            all_landed_costs=landed_costs_pool,
            quality_rating=cand["quality_rating"],
            reliability_score=cand["reliability_score"],
            lead_time_days=cand["lead_time_days"],
            all_lead_times=lead_times_pool,
            payment_terms_days=cand["payment_terms_days"],
            weights=payload.weights
        )
        cand["scorecard"] = score_res
        cand["composite_score"] = score_res["composite_score"]
        cand["decision_band"] = score_res["decision_band"]

    # Rank by composite score descending
    candidate_evaluations.sort(key=lambda x: x["composite_score"], reverse=True)
    best_candidate = candidate_evaluations[0]

    return {
        "compared_quotations_count": len(candidate_evaluations),
        "target_quantity": target_qty,
        "recommended_candidate": {
            "supplier_name": best_candidate["supplier_name"],
            "composite_score": best_candidate["composite_score"],
            "decision_band": best_candidate["decision_band"],
            "effective_unit_landed_cost": best_candidate["effective_unit_landed_cost"],
            "total_landed_cost": best_candidate["total_landed_cost"],
            "rationale": best_candidate["scorecard"]["verdict"]
        },
        "candidates": candidate_evaluations
    }

