from typing import Dict, Any, List, Optional

DEFAULT_WEIGHTS = {
    "cost_competitiveness": 0.35,
    "quality": 0.25,
    "delivery_reliability": 0.15,
    "delivery_time": 0.15,
    "payment_flexibility": 0.10,
}

def evaluate_supplier_quotation(
    unit_landed_cost: float,
    all_landed_costs: List[float],
    quality_rating: Optional[float] = None, # 0.0 to 5.0
    reliability_score: Optional[float] = None, # 0 to 100
    lead_time_days: Optional[int] = None,
    all_lead_times: Optional[List[int]] = None,
    payment_terms_days: Optional[int] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Computes an explainable, multi-dimensional supplier score (0 to 100).
    Handles missing metrics cleanly without unfair penalties, annotating treatment.
    """
    w = weights or DEFAULT_WEIGHTS
    explanations: List[str] = []

    # 1. Cost Competitiveness (0 - 100)
    # Relative to min price in comparison pool: Score = (min_price / current_price) * 100
    min_cost = min(all_landed_costs) if all_landed_costs else unit_landed_cost
    if unit_landed_cost > 0:
        cost_score = min(100.0, (min_cost / unit_landed_cost) * 100.0)
    else:
        cost_score = 0.0
    explanations.append(f"Cost Score: {cost_score:.1f}/100 (unit landed ₹{unit_landed_cost:.2f} vs best pool ₹{min_cost:.2f})")

    # 2. Quality Score (0 - 100)
    if quality_rating is not None:
        quality_score = min(100.0, max(0.0, (quality_rating / 5.0) * 100.0))
        explanations.append(f"Quality Score: {quality_score:.1f}/100 based on verified inspection rating {quality_rating:.1f}/5.0")
    else:
        quality_score = 70.0 # Neutral benchmark
        explanations.append("Quality Score: 70.0/100 (Neutral benchmark imputed due to lack of historical inspection records)")

    # 3. Delivery Reliability (0 - 100)
    if reliability_score is not None:
        rel_score = min(100.0, max(0.0, float(reliability_score)))
        explanations.append(f"Reliability Score: {rel_score:.1f}/100 based on past on-time fulfillment track record")
    else:
        rel_score = 75.0 # Neutral benchmark
        explanations.append("Reliability Score: 75.0/100 (Default baseline imputed for first-time or unrated vendor)")

    # 4. Lead Time / Delivery Time (0 - 100)
    if lead_time_days is not None:
        best_lead = min(all_lead_times) if all_lead_times else lead_time_days
        # Faster is better
        if lead_time_days <= best_lead:
            lead_score = 100.0
        else:
            lead_score = max(20.0, 100.0 - (lead_time_days - best_lead) * 7.0)
        explanations.append(f"Lead Time Score: {lead_score:.1f}/100 ({lead_time_days} days delivery timeline)")
    else:
        lead_score = 70.0
        explanations.append("Lead Time Score: 70.0/100 (Standard industrial lead time assumption)")

    # 5. Payment Terms Flexibility (0 - 100)
    # Standard: 30 days is standard (75 pts), 60+ days is excellent (100 pts), 0/advance is 40 pts
    if payment_terms_days is not None:
        if payment_terms_days >= 60:
            payment_score = 100.0
        elif payment_terms_days >= 45:
            payment_score = 90.0
        elif payment_terms_days >= 30:
            payment_score = 75.0
        elif payment_terms_days >= 15:
            payment_score = 60.0
        else:
            payment_score = 40.0
        explanations.append(f"Payment Terms Score: {payment_score:.1f}/100 ({payment_terms_days} days credit)")
    else:
        payment_score = 65.0
        explanations.append("Payment Terms Score: 65.0/100 (Default 15-day commercial terms assumed)")

    # Weighted composite score
    composite_score = (
        cost_score * w["cost_competitiveness"] +
        quality_score * w["quality"] +
        rel_score * w["delivery_reliability"] +
        lead_score * w["delivery_time"] +
        payment_score * w["payment_flexibility"]
    )
    composite_score = round(composite_score, 2)

    # Decision Band
    if composite_score >= 80.0:
        decision_band = "STRONGLY_RECOMMENDED"
        verdict = "Top tier procurement choice offering superior landed economics, quality, and delivery stability."
    elif composite_score >= 65.0:
        decision_band = "VIABLE_ALTERNATIVE"
        verdict = "Solid alternative candidate; competitive overall terms with acceptable trade-offs."
    elif composite_score >= 50.0:
        decision_band = "HIGH_RISK_CONSIDERATION"
        verdict = "Sub-optimal terms or higher landed cost; requires mitigation or active negotiation before commitment."
    else:
        decision_band = "NOT_RECOMMENDED"
        verdict = "Excessive landed pricing or poor reliability rating. Recommended for rejection."

    return {
        "composite_score": composite_score,
        "decision_band": decision_band,
        "verdict": verdict,
        "sub_scores": {
            "cost_competitiveness": round(cost_score, 2),
            "quality": round(quality_score, 2),
            "delivery_reliability": round(rel_score, 2),
            "delivery_time": round(lead_score, 2),
            "payment_flexibility": round(payment_score, 2),
        },
        "weights": w,
        "explanations": explanations
    }

