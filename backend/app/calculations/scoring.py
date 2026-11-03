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
    reliability_score: Optional[float] = None, # 0 to 100%
    lead_time_days: Optional[int] = None,
    all_lead_times: Optional[List[int]] = None,
    payment_terms_days: Optional[int] = None,
    rejection_rate_pct: Optional[float] = None,
    target_deadline_days: Optional[int] = None,
    weights: Optional[Dict[str, float]] = None,
    is_simulated: bool = False
) -> Dict[str, Any]:
    """
    Explainable, mathematically deterministic 5-factor supplier scoring engine.
    
    Missing Data Policy:
    When empirical vendor data is missing, IndusPilot dynamically renormalizes
    the weights of verified active factors, explicitly tags missing indicators,
    and calculates an overall Evidence Completeness Index.
    """
    base_weights = dict(weights or DEFAULT_WEIGHTS)
    explanations: List[str] = []
    missing_factors: List[str] = []
    raw_values: Dict[str, Any] = {}
    sub_scores: Dict[str, float] = {}
    active_weights: Dict[str, float] = {}

    # --- Factor 1: Landed Price Competitiveness (Weight: 35%) ---
    raw_values["unit_landed_cost"] = unit_landed_cost
    eligible_costs = [c for c in all_landed_costs if c > 0]
    min_cost = min(eligible_costs) if eligible_costs else unit_landed_cost

    if unit_landed_cost > 0:
        # Bounded hyper-curve: min_cost / current_cost * 100
        cost_score = min(100.0, max(10.0, (min_cost / unit_landed_cost) * 100.0))
        sub_scores["cost_competitiveness"] = round(cost_score, 2)
        active_weights["cost_competitiveness"] = base_weights["cost_competitiveness"]
        diff_pct = ((unit_landed_cost - min_cost) / min_cost) * 100.0 if min_cost > 0 else 0.0
        if diff_pct == 0:
            explanations.append(f"Cost Competitiveness: 100.0/100 (Lowest landed cost in comparison pool at ₹{unit_landed_cost:,.2f}/unit)")
        else:
            explanations.append(f"Cost Competitiveness: {cost_score:.1f}/100 (₹{unit_landed_cost:,.2f}/unit is +{diff_pct:.1f}% above pool minimum ₹{min_cost:,.2f})")
    else:
        sub_scores["cost_competitiveness"] = 0.0
        missing_factors.append("cost_competitiveness")
        explanations.append("Cost Competitiveness: 0.0/100 (Invalid or zero landed cost)")

    # --- Factor 2: Material Quality & Certifications (Weight: 25%) ---
    raw_values["quality_rating"] = quality_rating
    raw_values["rejection_rate_pct"] = rejection_rate_pct
    if quality_rating is not None and quality_rating > 0:
        base_quality_score = min(100.0, max(0.0, (quality_rating / 5.0) * 100.0))
        # Deduct for rejection rate if recorded
        rej_penalty = min(20.0, (rejection_rate_pct or 0.0) * 5.0)
        quality_score = max(10.0, base_quality_score - rej_penalty)
        sub_scores["quality"] = round(quality_score, 2)
        active_weights["quality"] = base_weights["quality"]
        sim_tag = " [Simulated Demo]" if is_simulated else ""
        explanations.append(
            f"Quality Score: {quality_score:.1f}/100 (Rating {quality_rating:.1f}/5.0 with {rejection_rate_pct or 0.0:.1f}% scrap/rejection rate{sim_tag})"
        )
    else:
        missing_factors.append("quality")
        explanations.append("Quality Score: UNKNOWN (No historical factory quality inspection records found. Factor weight redistributed.)")

    # --- Factor 3: Delivery Reliability & On-Time Performance (Weight: 15%) ---
    raw_values["reliability_score"] = reliability_score
    if reliability_score is not None and reliability_score > 0:
        rel_score = min(100.0, max(0.0, float(reliability_score)))
        sub_scores["delivery_reliability"] = round(rel_score, 2)
        active_weights["delivery_reliability"] = base_weights["delivery_reliability"]
        sim_tag = " [Simulated Track Record]" if is_simulated else ""
        explanations.append(f"Reliability Score: {rel_score:.1f}/100 (Historical fulfillment consistency{sim_tag})")
    else:
        missing_factors.append("delivery_reliability")
        explanations.append("Reliability Score: UNKNOWN (Vendor has zero prior order delivery logs in the factory ledger. Factor weight redistributed.)")

    # --- Factor 4: Delivery Lead Time (Weight: 15%) ---
    raw_values["lead_time_days"] = lead_time_days
    raw_values["target_deadline_days"] = target_deadline_days
    if lead_time_days is not None and lead_time_days > 0:
        best_lead = min(all_lead_times) if all_lead_times else lead_time_days
        if target_deadline_days and target_deadline_days > 0:
            # Score relative to required manufacturing deadline
            if lead_time_days <= best_lead:
                lead_score = 100.0
            elif lead_time_days <= target_deadline_days:
                ratio = (target_deadline_days - lead_time_days) / max(1, target_deadline_days - best_lead)
                lead_score = 60.0 + (ratio * 40.0)
            else:
                lead_score = max(10.0, 50.0 - (lead_time_days - target_deadline_days) * 5.0)
        else:
            # Score relative to pool best
            if lead_time_days <= best_lead:
                lead_score = 100.0
            else:
                lead_score = max(20.0, 100.0 - (lead_time_days - best_lead) * 7.0)

        sub_scores["delivery_time"] = round(lead_score, 2)
        active_weights["delivery_time"] = base_weights["delivery_time"]
        explanations.append(f"Lead Time Score: {lead_score:.1f}/100 ({lead_time_days} calendar days quoted transit)")
    else:
        missing_factors.append("delivery_time")
        explanations.append("Lead Time Score: UNKNOWN (Unstated delivery timeline in quotation. Factor weight redistributed.)")

    # --- Factor 5: Commercial Payment Flexibility (Weight: 10%) ---
    raw_values["payment_terms_days"] = payment_terms_days
    if payment_terms_days is not None:
        if payment_terms_days >= 60:
            payment_score = 100.0
        elif payment_terms_days >= 45:
            payment_score = 90.0
        elif payment_terms_days >= 30:
            payment_score = 75.0
        elif payment_terms_days >= 15:
            payment_score = 60.0
        elif payment_terms_days > 0:
            payment_score = 50.0
        else: # 0 days = 100% advance payment required
            payment_score = 35.0

        sub_scores["payment_flexibility"] = round(payment_score, 2)
        active_weights["payment_flexibility"] = base_weights["payment_flexibility"]
        explanations.append(f"Payment Terms Score: {payment_score:.1f}/100 ({payment_terms_days} days credit terms)")
    else:
        missing_factors.append("payment_flexibility")
        explanations.append("Payment Terms Score: UNKNOWN (Standard payment conditions not specified. Factor weight redistributed.)")

    # --- Renormalization & Composite Score Computation ---
    total_active_weight = sum(active_weights.values())
    renormalized_weights: Dict[str, float] = {}

    if total_active_weight > 0:
        composite_score = 0.0
        for factor_key, score_val in sub_scores.items():
            norm_w = active_weights[factor_key] / total_active_weight
            renormalized_weights[factor_key] = round(norm_w, 4)
            composite_score += score_val * norm_w
        composite_score = round(composite_score, 2)
    else:
        composite_score = 0.0

    # Data Completeness Index
    completeness_pct = round((len(sub_scores) / 5.0) * 100.0, 1)

    # Decision Band Classification
    if completeness_pct < 60.0:
        decision_band = "LOW_EVIDENCE_PROVISIONAL"
        verdict = f"Provisional evaluation: Only {completeness_pct}% of evaluation data is available. Additional supplier verification required before commitment."
    elif composite_score >= 82.0:
        decision_band = "STRONGLY_RECOMMENDED"
        verdict = "Top tier procurement choice offering superior landed economics, quality, and delivery stability."
    elif composite_score >= 68.0:
        decision_band = "VIABLE_ALTERNATIVE"
        verdict = "Solid alternative candidate; competitive overall terms with acceptable operational trade-offs."
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
        "data_completeness_pct": completeness_pct,
        "sub_scores": sub_scores,
        "original_factor_values": raw_values,
        "original_weights": base_weights,
        "renormalized_weights": renormalized_weights,
        "missing_factors": missing_factors,
        "explanations": explanations,
        "is_simulated": is_simulated
    }
