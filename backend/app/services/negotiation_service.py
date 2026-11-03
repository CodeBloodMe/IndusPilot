from typing import Dict, Any, List, Optional
from datetime import datetime

class NegotiationStateMachine:
    VALID_TRANSITIONS = {
        "DRAFT": ["READY_FOR_APPROVAL", "CANCELLED"],
        "READY_FOR_APPROVAL": ["APPROVED_TO_SEND", "DRAFT", "CANCELLED"],
        "APPROVED_TO_SEND": ["SENT"],
        "SENT": ["RESPONSE_RECEIVED"],
        "RESPONSE_RECEIVED": ["COUNTEROFFER_PROPOSED", "ACCEPTANCE_PROPOSED", "REJECTED", "CLOSED"],
        "COUNTEROFFER_PROPOSED": ["READY_FOR_APPROVAL", "CLOSED"],
        "ACCEPTANCE_PROPOSED": ["READY_FOR_APPROVAL", "CLOSED"],
        "REJECTED": ["CLOSED"],
        "CLOSED": []
    }

    @classmethod
    def can_transition(cls, current_state: str, new_state: str) -> bool:
        return new_state in cls.VALID_TRANSITIONS.get(current_state, [])

def generate_counteroffer_draft(
    supplier_name: str,
    material_name: str,
    quantity: float,
    unit: str,
    current_offered_price: float,
    target_price: float,
    benchmark_market_price: Optional[float] = None,
    competitor_lowest_price: Optional[float] = None,
    current_payment_terms: str = "30 Days Net",
    improved_payment_terms: str = "15 Days Advance/Prompt Payment"
) -> Dict[str, Any]:
    """
    Constructs an evidence-backed counteroffer and email draft.
    Does not invent fake figures; uses supplied market benchmarks and volumes.
    """
    price_gap = current_offered_price - target_price
    discount_pct = (price_gap / current_offered_price) * 100.0 if current_offered_price > 0 else 0.0

    subject = f"Commercial Negotiation — Purchase Order for {quantity} {unit} of {material_name}"

    body_paragraphs = [
        f"Dear {supplier_name} Sales & Commercial Team,",
        (
            f"Thank you for submitting your quotation for {quantity:,.1f} {unit} of {material_name} "
            f"at ₹{current_offered_price:.2f}/{unit}."
        ),
        (
            f"We are actively planning our upcoming production batch and are prepared to issue an immediate "
            f"firm Purchase Order. However, our technical costing and current market allocations reflect a "
            f"target landed price of ₹{target_price:.2f}/{unit} "
            + (f"(supported by alternative vendor quotes at ₹{competitor_lowest_price:.2f}/{unit})." if competitor_lowest_price else ".")
        ),
        (
            f"In recognition of our intended repeat procurement partnership and to close this order immediately, "
            f"we propose a revised unit price of ₹{target_price:.2f}/{unit}. In exchange for this pricing concession, "
            f"we are prepared to support expedited payment terms: {improved_payment_terms}."
        ),
        "Kindly review this counteroffer and confirm if you can revise your commercial invoice accordingly.",
        "Warm regards,\nProcurement Lead\nIndusPilot Autonomous Procurement"
    ]

    email_body = "\n\n".join(body_paragraphs)

    return {
        "subject": subject,
        "email_body": email_body,
        "proposed_unit_price": target_price,
        "requested_discount_pct": round(discount_pct, 1),
        "improved_payment_terms": improved_payment_terms,
        "evidence_cited": {
            "requested_quantity": quantity,
            "unit": unit,
            "opening_quote": current_offered_price,
            "counter_target": target_price,
            "market_benchmark": benchmark_market_price,
            "competitor_price": competitor_lowest_price,
        },
        "requires_human_approval": True,
        "next_state": "READY_FOR_APPROVAL"
    }

def simulate_supplier_response(
    supplier_name: str,
    round_number: int,
    original_price: float,
    current_offered_price: float,
    buyer_counter_price: float,
    material_name: str,
    quantity: float
) -> Dict[str, Any]:
    """
    Simulates a realistic, vendor negotiation response for the hackathon demonstration.
    Models vendor concession behavior:
    - Round 1: Vendor partially compromises towards buyer target (splits difference ~50-65%).
    - Round 2: Vendor offers final best-and-final offer.
    """
    gap = current_offered_price - buyer_counter_price
    
    if round_number == 1:
        # Vendor concessions: concede roughly 60% of the difference
        concession = gap * 0.60
        revised_price = round(current_offered_price - concession, 2)
        response_text = (
            f"Dear Buyer Team,\n\n"
            f"Thank you for your counteroffer on the {quantity:,.1f} kg {material_name} requirement. "
            f"While ₹{buyer_counter_price:.2f}/kg is below our raw mill margin, we value your volume and "
            f"are pleased to propose a revised price of ₹{revised_price:.2f}/kg, provided payment terms "
            f"are 15 days as discussed. This represents our strongest possible commercial concession."
            f"\n\nBest regards,\nSales Commercials, {supplier_name} (Simulated)"
        )
        recommendation = "COUNTEROFFER_PROPOSED"
        explanation = (
            f"{supplier_name} compromised by ₹{concession:.2f}/kg (price dropped from ₹{current_offered_price:.2f} "
            f"to ₹{revised_price:.2f}/kg). Total potential batch savings: ₹{(original_price - revised_price) * quantity:,.2f}."
        )
    else:
        # Final round: Accept buyer price if within 3% or give rock-bottom price
        if gap / original_price <= 0.04:
            revised_price = buyer_counter_price
            response_text = (
                f"Dear Buyer Team,\n\n"
                f"Following internal management review, we have agreed to accept your proposed rate of "
                f"₹{revised_price:.2f}/kg for the entire {quantity:,.1f} kg order. Please release the Purchase Order."
                f"\n\nBest regards,\nCommercial Director, {supplier_name} (Simulated)"
            )
            recommendation = "ACCEPTANCE_PROPOSED"
            explanation = f"{supplier_name} agreed to final target price of ₹{revised_price:.2f}/kg. Deal ready for closing."
        else:
            revised_price = round(buyer_counter_price + (gap * 0.25), 2)
            response_text = (
                f"Dear Buyer Team,\n\n"
                f"We have reached our absolute floor at ₹{revised_price:.2f}/kg. This is our best and final offer."
                f"\n\nBest regards,\nSales Commercials, {supplier_name} (Simulated)"
            )
            recommendation = "ACCEPTANCE_PROPOSED"
            explanation = f"{supplier_name} presented best-and-final rate of ₹{revised_price:.2f}/kg."

    savings_vs_original = round((original_price - revised_price) * quantity, 2)

    return {
        "round_number": round_number,
        "sender_type": "SUPPLIER",
        "supplier_name": supplier_name,
        "response_message": response_text,
        "revised_unit_price": revised_price,
        "original_price": original_price,
        "savings_vs_original": savings_vs_original,
        "status": "RESPONSE_RECEIVED",
        "recommended_action": recommendation,
        "explanation": explanation,
        "is_simulated": True
    }

