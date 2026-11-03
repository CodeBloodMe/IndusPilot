from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_org_id
from app.models.entities import (
    SupplierQuotation, Supplier, Material, QuotationItem,
    SupplierComparisonRequest, SupplierComparisonResult, SupplierComparisonCandidate
)
from app.schemas.domain import (
    ComparisonAnalyzeRequest, EligibilityCheckRequest,
    LandedCostCalculateRequest, SupplierCompareRequest
)
from app.calculations.landed_cost import calculate_landed_cost, allocate_charges_across_items
from app.calculations.scoring import evaluate_supplier_quotation
from app.services.eligibility_engine import evaluate_supplier_eligibility, EligibilityStatus
from app.services.decision_explainer import generate_procurement_decision_explanation

router = APIRouter()


@router.post("/analyze")
@router.post("/evaluate")
def analyze_supplier_comparison(
    payload: ComparisonAnalyzeRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Intelligent Supplier Comparison & Procurement Decision Engine.
    Executes specification eligibility filtering, multi-item landed cost calculations,
    evidence-weighted 5-factor scoring, and deterministic decision explanations.
    """
    # 1. Resolve Material Requirements
    target_mat_name = payload.material_name or "Stainless Steel 304 Sheet"
    target_grade = payload.grade
    target_thickness = payload.thickness_mm
    target_unit = payload.unit or "kg"
    target_qty = payload.quantity or 800.0

    if payload.material_id:
        mat_entity = db.query(Material).filter(
            Material.id == payload.material_id,
            Material.organization_id == org_id
        ).first()
        if mat_entity:
            target_mat_name = mat_entity.name
            target_grade = target_grade or mat_entity.grade
            target_unit = mat_entity.unit or target_unit

    requirement_spec = {
        "material_id": payload.material_id,
        "material_name": target_mat_name,
        "grade": target_grade,
        "thickness_mm": target_thickness,
        "quantity": target_qty,
        "unit": target_unit,
        "delivery_deadline": payload.delivery_deadline,
        "budget_limit": payload.budget_limit
    }

    # 2. Query Candidate Quotations
    query = db.query(SupplierQuotation).filter(
        SupplierQuotation.organization_id == org_id,
        SupplierQuotation.status != "QUARANTINED"
    )

    if payload.quotation_ids:
        query = query.filter(SupplierQuotation.id.in_(payload.quotation_ids))
    else:
        # Default to verified and ready for review quotations
        query = query.filter(SupplierQuotation.status.in_(["VERIFIED", "READY_FOR_REVIEW"]))

    quotations = query.all()
    if not quotations:
        raise HTTPException(
            status_code=400,
            detail="No verified quotations available for comparison. Please upload or verify supplier quotes first."
        )

    # 3. Evaluate Eligibility for all Candidate Quotations
    eligible_candidates_raw = []
    ineligible_candidates = []

    for q in quotations:
        sup = q.supplier
        sup_dict = {
            "id": sup.id if sup else "N/A",
            "name": sup.name if sup else "Unknown",
            "capacity_monthly_tons": sup.capacity_monthly_tons if sup else 50.0,
            "credit_period_days": sup.credit_period_days if sup else 30
        } if sup else None

        q_dict = {
            "id": q.id,
            "quotation_number": q.quotation_number,
            "valid_until": q.valid_until.isoformat() if q.valid_until else None,
            "tax_treatment": "TAX_INCLUDED" if q.is_tax_inclusive else "TAX_EXCLUDED",
            "is_quarantined": q.status == "QUARANTINED",
            "items": [
                {
                    "material_name_raw": it.material_name_raw,
                    "grade": it.grade,
                    "thickness_mm": it.thickness_mm,
                    "unit": it.unit,
                    "unit_price": it.unit_price,
                    "quantity": it.quantity,
                    "moq": it.moq,
                    "lead_time_days": it.lead_time_days,
                    "material_id": it.material_id
                }
                for it in q.items
            ]
        }

        eligibility_res = evaluate_supplier_eligibility(
            requirement=requirement_spec,
            quotation=q_dict,
            supplier=sup_dict,
            allow_split_purchasing=payload.allow_split_purchasing
        )

        matched_line = eligibility_res.get("matched_item") or (q_dict["items"][0] if q_dict["items"] else {})

        if not eligibility_res["is_eligible"]:
            ineligible_candidates.append({
                "quotation_id": q.id,
                "quotation_number": q.quotation_number,
                "supplier_id": sup.id if sup else "N/A",
                "supplier_name": sup.name if sup else "Unknown Vendor",
                "status": eligibility_res["status"],
                "ineligibility_reasons": eligibility_res["ineligibility_reasons"],
                "warnings": eligibility_res["warnings"],
                "quoted_material": matched_line.get("material_name"),
                "quoted_grade": matched_line.get("grade"),
                "quoted_thickness_mm": matched_line.get("thickness_mm"),
                "quoted_unit_price": matched_line.get("quoted_unit_price", 0.0),
                "constraint_checks": eligibility_res["constraint_checks"]
            })
        else:
            eligible_candidates_raw.append({
                "quotation": q,
                "supplier": sup,
                "matched_line": matched_line,
                "eligibility": eligibility_res
            })

    if not eligible_candidates_raw:
        return {
            "compared_quotations_count": len(quotations),
            "eligible_candidates_count": 0,
            "target_quantity": target_qty,
            "target_material": target_mat_name,
            "error_message": "All available supplier quotations failed mandatory specification eligibility checks.",
            "ineligible_candidates": ineligible_candidates,
            "candidates": []
        }

    # 4. Landed Cost Calculation & Normalization Pools
    candidate_evaluations = []
    landed_costs_pool = []
    lead_times_pool = []

    for item in eligible_candidates_raw:
        q = item["quotation"]
        sup = item["supplier"]
        matched_line = item["matched_line"]
        elig = item["eligibility"]

        unit_price = matched_line.get("quoted_unit_price") or 300.0
        lead_time = matched_line.get("lead_time_days") or (sup.lead_time_days if sup else 7)

        # Multi-item freight allocation if quotation contains multiple lines
        freight_to_use = q.freight_cost
        other_to_use = q.other_charges
        if len(q.items) > 1:
            line_dicts = [{"quantity": it.quantity, "unit_price": it.unit_price} for it in q.items]
            alloc = allocate_charges_across_items(line_dicts, q.freight_cost, 0.0, q.other_charges)
            # Find index of matched item
            match_idx = 0
            for idx, it in enumerate(q.items):
                if it.material_name_raw == matched_line.get("material_name"):
                    match_idx = idx
                    break
            freight_to_use = alloc[match_idx]["allocated_freight"]
            other_to_use = alloc[match_idx]["allocated_other"]

        # Calculate landed economics
        landed_data = calculate_landed_cost(
            unit_price=unit_price,
            quantity=target_qty,
            tax_pct=q.tax_pct,
            is_tax_inclusive=q.is_tax_inclusive,
            freight_total=freight_to_use,
            other_charges_total=other_to_use,
            requested_quantity=target_qty
        )

        eff_unit_landed = landed_data["effective_unit_landed_cost"]
        landed_costs_pool.append(eff_unit_landed)
        lead_times_pool.append(lead_time)

        candidate_evaluations.append({
            "quotation_id": q.id,
            "quotation_number": q.quotation_number,
            "quotation_date": q.quotation_date.isoformat() if q.quotation_date else None,
            "valid_until": q.valid_until.isoformat() if q.valid_until else None,
            "supplier_id": sup.id if sup else "N/A",
            "supplier_name": sup.name if sup else "Unknown Vendor",
            "city": sup.city if sup else "",
            "material_name": matched_line.get("material_name") or target_mat_name,
            "material_grade": matched_line.get("grade") or target_grade,
            "thickness_mm": matched_line.get("thickness_mm") or target_thickness,
            "quantity": target_qty,
            "quoted_unit_price": unit_price,
            "moq": matched_line.get("quoted_moq", 1.0),
            "lead_time_days": lead_time,
            "payment_terms_days": sup.payment_terms_days if sup else 30,
            "quality_rating": sup.quality_rating if sup else None,
            "reliability_score": sup.reliability_score if sup else None,
            "rejection_rate_pct": sup.rejection_rate_pct if sup else None,
            "is_simulated": getattr(sup, "is_simulated", True),
            "landed_cost_breakdown": landed_data,
            "effective_unit_landed_cost": eff_unit_landed,
            "total_landed_cost": landed_data["total_landed_cost"],
            "eligibility": elig
        })

    # 5. Execute 5-Factor Scoring with Missing Data Weight Renormalization
    for cand in candidate_evaluations:
        score_res = evaluate_supplier_quotation(
            unit_landed_cost=cand["effective_unit_landed_cost"],
            all_landed_costs=landed_costs_pool,
            quality_rating=cand["quality_rating"],
            reliability_score=cand["reliability_score"],
            lead_time_days=cand["lead_time_days"],
            all_lead_times=lead_times_pool,
            payment_terms_days=cand["payment_terms_days"],
            rejection_rate_pct=cand["rejection_rate_pct"],
            weights=payload.weights,
            is_simulated=cand["is_simulated"]
        )
        cand["scorecard"] = score_res
        cand["composite_score"] = score_res["composite_score"]
        cand["decision_band"] = score_res["decision_band"]
        cand["data_completeness_pct"] = score_res["data_completeness_pct"]

    # 6. Rank Candidates & Identify Category Leaders
    candidate_evaluations.sort(key=lambda x: x["composite_score"], reverse=True)
    for idx, c in enumerate(candidate_evaluations, start=1):
        c["rank"] = idx

    best_candidate = candidate_evaluations[0]
    cheapest_candidate = min(candidate_evaluations, key=lambda x: x["effective_unit_landed_cost"])
    fastest_candidate = min(candidate_evaluations, key=lambda x: x["lead_time_days"])
    highest_quality_candidate = max(candidate_evaluations, key=lambda x: x.get("quality_rating") or 0.0)

    # 7. Generate Natural Language Explanation
    explanation_res = generate_procurement_decision_explanation(
        recommended_candidate=best_candidate,
        all_candidates=candidate_evaluations,
        cheapest_candidate=cheapest_candidate,
        fastest_candidate=fastest_candidate,
        highest_quality_candidate=highest_quality_candidate,
        target_quantity=target_qty,
        material_name=target_mat_name
    )

    # 8. Persist Comparison Records for Auditability & Reproducibility
    saved_comparison_id = None
    if payload.save_comparison:
        comp_req = SupplierComparisonRequest(
            organization_id=org_id,
            material_id=payload.material_id,
            material_name=target_mat_name,
            target_quantity=target_qty,
            unit=target_unit,
            delivery_deadline=datetime.fromisoformat(payload.delivery_deadline.replace("Z", "+00:00")) if payload.delivery_deadline else None,
            budget_limit=payload.budget_limit,
            weights_json=payload.weights
        )
        db.add(comp_req)
        db.flush()

        comp_res = SupplierComparisonResult(
            organization_id=org_id,
            request_id=comp_req.id,
            recommended_supplier_id=best_candidate["supplier_id"],
            recommended_quotation_id=best_candidate["quotation_id"],
            lowest_cost_supplier_id=cheapest_candidate["supplier_id"],
            fastest_supplier_id=fastest_candidate["supplier_id"],
            highest_quality_supplier_id=highest_quality_candidate["supplier_id"],
            summary_headline=explanation_res["summary_headline"],
            concise_recommendation=explanation_res["concise_recommendation"],
            detailed_explanation=explanation_res["detailed_explanation"],
            evaluated_count=len(quotations),
            eligible_count=len(candidate_evaluations)
        )
        db.add(comp_res)
        db.flush()

        for cand in candidate_evaluations:
            db.add(SupplierComparisonCandidate(
                comparison_result_id=comp_res.id,
                quotation_id=cand["quotation_id"],
                supplier_id=cand["supplier_id"],
                rank=cand["rank"],
                eligibility_status=cand["eligibility"]["status"],
                ineligibility_reasons_json=cand["eligibility"]["ineligibility_reasons"],
                effective_unit_landed_cost=cand["effective_unit_landed_cost"],
                total_landed_cost=cand["total_landed_cost"],
                composite_score=cand["composite_score"],
                decision_band=cand["decision_band"],
                data_completeness_pct=cand["data_completeness_pct"],
                scorecard_json=cand["scorecard"]
            ))

        db.commit()
        saved_comparison_id = comp_res.id

    return {
        "comparison_id": saved_comparison_id,
        "compared_quotations_count": len(quotations),
        "eligible_candidates_count": len(candidate_evaluations),
        "ineligible_candidates_count": len(ineligible_candidates),
        "target_quantity": target_qty,
        "target_material": target_mat_name,
        "target_grade": target_grade,
        "highlights": {
            "best_overall": {
                "supplier_name": best_candidate["supplier_name"],
                "composite_score": best_candidate["composite_score"],
                "decision_band": best_candidate["decision_band"],
                "effective_unit_landed_cost": best_candidate["effective_unit_landed_cost"],
                "total_landed_cost": best_candidate["total_landed_cost"],
                "lead_time_days": best_candidate["lead_time_days"]
            },
            "lowest_cost": {
                "supplier_name": cheapest_candidate["supplier_name"],
                "effective_unit_landed_cost": cheapest_candidate["effective_unit_landed_cost"],
                "total_landed_cost": cheapest_candidate["total_landed_cost"]
            },
            "fastest": {
                "supplier_name": fastest_candidate["supplier_name"],
                "lead_time_days": fastest_candidate["lead_time_days"]
            },
            "highest_quality": {
                "supplier_name": highest_quality_candidate["supplier_name"],
                "quality_rating": highest_quality_candidate.get("quality_rating")
            }
        },
        "recommended_candidate": best_candidate,
        "explanation": explanation_res,
        "candidates": candidate_evaluations,
        "ineligible_candidates": ineligible_candidates
    }


@router.post("/eligibility")
def check_single_quotation_eligibility(
    payload: EligibilityCheckRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Evaluates whether a specific quotation satisfies the material specification,
    volume, delivery, and commercial constraints.
    """
    quote = db.query(SupplierQuotation).filter(
        SupplierQuotation.id == payload.quotation_id,
        SupplierQuotation.organization_id == org_id
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quotation not found.")

    sup = quote.supplier
    sup_dict = {
        "id": sup.id if sup else "N/A",
        "name": sup.name if sup else "Unknown",
        "capacity_monthly_tons": sup.capacity_monthly_tons if sup else 50.0,
        "credit_period_days": sup.credit_period_days if sup else 30
    } if sup else None

    q_dict = {
        "id": quote.id,
        "quotation_number": quote.quotation_number,
        "valid_until": quote.valid_until.isoformat() if quote.valid_until else None,
        "tax_treatment": "TAX_INCLUDED" if quote.is_tax_inclusive else "TAX_EXCLUDED",
        "is_quarantined": quote.status == "QUARANTINED",
        "items": [
            {
                "material_name_raw": it.material_name_raw,
                "grade": it.grade,
                "thickness_mm": it.thickness_mm,
                "unit": it.unit,
                "unit_price": it.unit_price,
                "quantity": it.quantity,
                "moq": it.moq,
                "lead_time_days": it.lead_time_days
            }
            for it in quote.items
        ]
    }

    req_dict = {
        "material_name": payload.material_name,
        "grade": payload.grade,
        "thickness_mm": payload.thickness_mm,
        "quantity": payload.quantity,
        "unit": payload.unit,
        "delivery_deadline": payload.delivery_deadline,
        "max_lead_time_days": payload.max_lead_time_days
    }

    res = evaluate_supplier_eligibility(
        requirement=req_dict,
        quotation=q_dict,
        supplier=sup_dict,
        allow_split_purchasing=payload.allow_split_purchasing
    )
    return res


@router.post("/landed-cost")
def calculate_landed_cost_endpoint(payload: LandedCostCalculateRequest):
    """
    Standalone deterministic calculator for Total Landed Cost.
    Calculates taxable base, GST amounts, freight allocation, and effective unit prices
    using strict Python Decimal precision.
    """
    try:
        return calculate_landed_cost(
            unit_price=payload.unit_price,
            quantity=payload.quantity,
            tax_pct=payload.tax_pct,
            tax_treatment=payload.tax_treatment,
            is_tax_inclusive=payload.is_tax_inclusive,
            freight_total=payload.freight_total,
            packaging_total=payload.packaging_total,
            other_charges_total=payload.other_charges_total,
            discount_pct=payload.discount_pct,
            discount_amount=payload.discount_amount,
            currency=payload.currency,
            base_currency=payload.base_currency,
            fx_rate_to_base=payload.fx_rate_to_base,
            requested_quantity=payload.requested_quantity
        )
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))


@router.get("/{comparison_id}")
def get_saved_comparison(
    comparison_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Retrieves a historically saved comparison result with its complete candidate list,
    factor scorecards, and reproducible decision rationale.
    """
    res = db.query(SupplierComparisonResult).filter(
        SupplierComparisonResult.id == comparison_id,
        SupplierComparisonResult.organization_id == org_id
    ).first()
    if not res:
        raise HTTPException(status_code=404, detail="Comparison record not found.")

    candidates = [
        {
            "rank": c.rank,
            "quotation_id": c.quotation_id,
            "supplier_id": c.supplier_id,
            "supplier_name": c.supplier.name if c.supplier else "N/A",
            "effective_unit_landed_cost": c.effective_unit_landed_cost,
            "total_landed_cost": c.total_landed_cost,
            "composite_score": c.composite_score,
            "decision_band": c.decision_band,
            "eligibility_status": c.eligibility_status,
            "data_completeness_pct": c.data_completeness_pct,
            "scorecard": c.scorecard_json
        }
        for c in res.candidates
    ]
    candidates.sort(key=lambda x: x["rank"])

    return {
        "comparison_id": res.id,
        "request_id": res.request_id,
        "created_at": res.created_at.isoformat() if res.created_at else None,
        "evaluated_count": res.evaluated_count,
        "eligible_count": res.eligible_count,
        "recommended_supplier": {
            "id": res.recommended_supplier.id if res.recommended_supplier else None,
            "name": res.recommended_supplier.name if res.recommended_supplier else "N/A"
        },
        "summary_headline": res.summary_headline,
        "concise_recommendation": res.concise_recommendation,
        "detailed_explanation": res.detailed_explanation,
        "candidates": candidates
    }
