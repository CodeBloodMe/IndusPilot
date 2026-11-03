"""
Phase 10 — Financial Consistency & Margin Reconciliation Test Suite
Verifies mathematical precision across Costing Engine, Customer Quotation Service,
LLM Intent Extraction, and LangGraph Supervisor Workflow.

Ensures:
1. Exact 20% Gross Margin ($637 / 0.8 = ₹796.25)
2. Exact 25% Gross Margin ($637 / 0.75 = ₹849.33)
3. Default 20% fallback when margin is omitted
4. Contextual follow-up margin update (20% -> 25%)
5. Exact reconciliation between Costing Engine and Customer Quotation
6. Realized margin adjustments under customer discounts
7. Strict rejection of invalid margins (>= 100% or negative)
"""

import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from app.calculations.cost_engine import calculate_manufacturing_cost
from app.services.customer_quotation_service import (
    calculate_quotation_pricing,
    create_customer_quotation_record
)
from app.agents.llm_provider import DemoNLUProvider
from app.agents.langgraph_supervisor import IndusPilotSupervisorGraph
from app.models.entities import CustomerQuotation, Product, Organization


def test_cost_engine_and_quotation_20_percent_margin():
    """
    Validates exact unit economics at 20.0% gross margin:
    1. Tests mathematical equivalence between Cost Engine and Customer Quotation Service.
    2. Validates exact values for the 500-unit bracket scenario (Unit Cost: Rs. 637.00):
       Selling Price: 637.00 / (1 - 0.20) = Rs. 796.25
       Total Revenue (500 units): Rs. 398,125.00
       Total Cost (500 units): Rs. 318,500.00
       Gross Profit: Rs. 79,625.00 (exact 20.0% of revenue)
    """
    # 1. Cost Engine calculation
    mat_breakdown = [
        {"material_name": "Stainless Steel 304 Plate", "gross_quantity": 1050.0, "net_quantity": 1000.0, "unit_cost": 315.0}
    ]
    cost_res = calculate_manufacturing_cost(
        production_quantity=500.0,
        material_costs_breakdown=mat_breakdown,
        direct_labor_hours=120.0,
        labor_rate_per_hour=180.0,
        machine_hours=45.0,
        machine_rate_per_hour=350.0,
        electricity_kwh=650.0,
        electricity_tariff_per_kwh=8.50,
        secondary_processes_total=18000.0,
        transportation_total=6500.0,
        packaging_total=4500.0,
        overhead_rate=12.0,
        target_gross_margin_pct=20.0
    )

    ue = cost_res["unit_economics"]
    cb = cost_res["cost_breakdown"]

    # Verify that Quotation Service produces identical results when given the Cost Engine's break-even price
    quote_pricing_reconciled = calculate_quotation_pricing(
        unit_cost=ue["break_even_price"],
        quantity=500.0,
        target_margin_pct=20.0
    )
    assert quote_pricing_reconciled["unit_selling_price"] == ue["suggested_unit_price"]
    assert quote_pricing_reconciled["total_production_cost"] == cb["total_production_cost"]
    assert quote_pricing_reconciled["total_gross_profit"] == ue["projected_gross_profit"]
    assert quote_pricing_reconciled["margin_pct"] == 20.0

    # 2. Quotation Pricing calculation for baseline Rs. 637.00 unit cost
    quote_pricing = calculate_quotation_pricing(
        unit_cost=637.00,
        quantity=500.0,
        target_margin_pct=20.0
    )
    assert quote_pricing["unit_selling_price"] == 796.25
    assert quote_pricing["total_production_cost"] == 318500.0
    assert quote_pricing["gross_subtotal"] == 398125.0
    assert quote_pricing["total_gross_profit"] == 79625.0
    assert quote_pricing["margin_pct"] == 20.0
    assert quote_pricing["markup_pct"] == 25.0


def test_cost_engine_and_quotation_25_percent_margin():
    """
    Validates exact unit economics at 25.0% gross margin:
    1. Tests mathematical equivalence between Cost Engine and Customer Quotation Service at 25%.
    2. Validates exact values for baseline Rs. 637.00 unit cost:
       Selling Price: 637.00 / (1 - 0.25) = Rs. 849.33
       Total Revenue (500 units): Rs. 424,665.00
       Total Cost (500 units): Rs. 318,500.00
       Gross Profit: Rs. 106,165.00 (~25.0% of revenue)
    """
    mat_breakdown = [
        {"material_name": "Stainless Steel 304 Plate", "gross_quantity": 1050.0, "net_quantity": 1000.0, "unit_cost": 315.0}
    ]
    cost_res = calculate_manufacturing_cost(
        production_quantity=500.0,
        material_costs_breakdown=mat_breakdown,
        direct_labor_hours=120.0,
        labor_rate_per_hour=180.0,
        machine_hours=45.0,
        machine_rate_per_hour=350.0,
        electricity_kwh=650.0,
        electricity_tariff_per_kwh=8.50,
        secondary_processes_total=18000.0,
        transportation_total=6500.0,
        packaging_total=4500.0,
        overhead_rate=12.0,
        target_gross_margin_pct=25.0
    )

    ue = cost_res["unit_economics"]
    cb = cost_res["cost_breakdown"]

    quote_pricing_reconciled = calculate_quotation_pricing(
        unit_cost=ue["break_even_price"],
        quantity=500.0,
        target_margin_pct=25.0
    )
    assert quote_pricing_reconciled["unit_selling_price"] == ue["suggested_unit_price"]
    assert quote_pricing_reconciled["total_production_cost"] == cb["total_production_cost"]
    assert quote_pricing_reconciled["total_gross_profit"] == ue["projected_gross_profit"]
    assert abs(quote_pricing_reconciled["margin_pct"] - 25.0) < 0.05

    quote_pricing = calculate_quotation_pricing(
        unit_cost=637.00,
        quantity=500.0,
        target_margin_pct=25.0
    )
    assert quote_pricing["unit_selling_price"] == 849.33
    assert quote_pricing["total_production_cost"] == 318500.0
    assert quote_pricing["gross_subtotal"] == 424665.0
    assert quote_pricing["total_gross_profit"] == 106165.0
    assert abs(quote_pricing["margin_pct"] - 25.0) < 0.05
    assert abs(quote_pricing["markup_pct"] - 33.33) < 0.05


def test_nlu_margin_extraction_and_defaults():
    """Validates that DemoNLUProvider correctly extracts 20%, 25%, and defaults when omitted."""
    nlu = DemoNLUProvider()

    # Query with explicit 20% gross margin
    q20 = "Check inventory, optimise procurement and calculate my expected manufacturing profit at a 20% gross margin."
    res20 = nlu.analyze_intent(q20)
    assert res20["intent"] == "END_TO_END_MANUFACTURING_WORKFLOW"
    assert res20["parameters"]["target_margin_pct"] == 20.0

    # Query with explicit 25% gross margin
    q25 = "Check inventory, optimise procurement and calculate my expected manufacturing profit at a 25% gross margin."
    res25 = nlu.analyze_intent(q25)
    assert res25["intent"] == "END_TO_END_MANUFACTURING_WORKFLOW"
    assert res25["parameters"]["target_margin_pct"] == 25.0

    # Query without explicit margin
    q_default = "Check inventory, identify missing materials, find suitable suppliers, optimise procurement within 5 lakh and calculate profit."
    res_default = nlu.analyze_intent(q_default)
    assert res_default["intent"] == "END_TO_END_MANUFACTURING_WORKFLOW"
    assert res_default["parameters"]["target_margin_pct"] == 20.0


def test_nlu_contextual_follow_up_margin_update():
    """Validates that a follow-up query updating margin retains product context and updates target_margin_pct."""
    nlu = DemoNLUProvider()
    context = {
        "product_code": "IND-BRK-SS304",
        "product_name": "Stainless Steel Industrial Bracket",
        "material_grade": "SS304",
        "production_quantity": 500.0,
        "target_margin_pct": 20.0,
        "previous_intent": "END_TO_END_MANUFACTURING_WORKFLOW"
    }

    follow_up_q = "What would my profit be at a 25% margin?"
    res = nlu.analyze_intent(follow_up_q, context=context)
    assert res["intent"] == "END_TO_END_MANUFACTURING_WORKFLOW"
    assert res["parameters"]["target_margin_pct"] == 25.0
    assert res["parameters"]["production_quantity"] == 500.0
    assert res["parameters"]["material_grade"] == "SS304"


def test_discount_adjusts_realized_margin():
    """
    Validates that applying a customer discount lowers the realized gross margin:
    List Price: Rs. 796.25 (20.0% list margin)
    Discount: 10% -> Net Price: Rs. 716.63 / unit
    Cost: Rs. 637.00
    Realized Gross Margin: (716.63 - 637.00) / 716.63 = 11.11%
    """
    pricing_nodisc = calculate_quotation_pricing(
        unit_cost=637.00,
        quantity=500.0,
        target_margin_pct=20.0,
        discount_pct=0.0
    )
    assert pricing_nodisc["margin_pct"] == 20.0

    pricing_disc = calculate_quotation_pricing(
        unit_cost=637.00,
        quantity=500.0,
        target_margin_pct=20.0,
        discount_pct=10.0
    )
    assert pricing_disc["discount_amount"] == 39812.50
    assert pricing_disc["discounted_subtotal"] == 358312.50
    assert pricing_disc["total_gross_profit"] == 39812.50
    assert pricing_disc["list_margin_pct"] == 20.0
    # Realized margin is strictly reduced by discount
    assert pricing_disc["realized_margin_pct"] == 11.11
    assert pricing_disc["realized_margin_pct"] < pricing_disc["list_margin_pct"]


def test_invalid_margin_rejection():
    """Validates that margins >= 100% or negative margins raise ValueError."""
    with pytest.raises(ValueError, match=r"strictly between|less than 100%"):
        calculate_manufacturing_cost(
            production_quantity=100.0,
            material_costs_breakdown=[{"unit_cost": 100.0, "gross_quantity": 10.0}],
            target_gross_margin_pct=100.0
        )

    with pytest.raises(ValueError, match=r"strictly between|less than 100%"):
        calculate_manufacturing_cost(
            production_quantity=100.0,
            material_costs_breakdown=[{"unit_cost": 100.0, "gross_quantity": 10.0}],
            target_gross_margin_pct=-15.0
        )

    with pytest.raises(ValueError, match=r"strictly less than 100% and non-negative"):
        calculate_quotation_pricing(
            unit_cost=500.0,
            quantity=10.0,
            target_margin_pct=105.0
        )

    with pytest.raises(ValueError, match=r"strictly less than 100% and non-negative"):
        calculate_quotation_pricing(
            unit_cost=500.0,
            quantity=10.0,
            target_margin_pct=-5.0
        )


from app.services.copilot_service import create_conversation, post_message_and_execute


def test_langgraph_end_to_end_margin_consistency(db_session: Session):
    """
    Validates that the multi-agent copilot produces exact matching figures in text and structured card
    for both 20% and 25% margins.
    """
    # 1. Test 20% margin
    conv20 = create_conversation(db=db_session, org_id="org-induspilot-demo", title="20% Margin Test")
    query_20 = "I have received an order for 500 stainless steel industrial brackets. Check my inventory, identify missing materials, find suitable suppliers, optimise procurement within 5 lakh and calculate my expected manufacturing profit at a 20% gross margin. Prepare a customer quotation for review."
    res_20 = post_message_and_execute(
        db=db_session,
        org_id="org-induspilot-demo",
        conversation_id=conv20["id"],
        content=query_20
    )

    msg_20 = res_20.get("message", {})
    card_20 = msg_20.get("structured_data", {})
    assert card_20.get("card_type") == "END_TO_END_SUMMARY"
    assert card_20.get("gross_margin_pct") == 20.0
    assert card_20.get("unit_cost") == 637.0
    assert card_20.get("selling_price") == 796.25
    assert card_20.get("projected_profit") == 79625.0
    assert "20.0% Gross Margin" in msg_20["content"]
    assert "796.25" in msg_20["content"]

    # 2. Test 25% margin
    conv25 = create_conversation(db=db_session, org_id="org-induspilot-demo", title="25% Margin Test")
    query_25 = "I have received an order for 500 stainless steel industrial brackets. Check my inventory, identify missing materials, find suitable suppliers, optimise procurement within 5 lakh and calculate my expected manufacturing profit at a 25% gross margin. Prepare a customer quotation for review."
    res_25 = post_message_and_execute(
        db=db_session,
        org_id="org-induspilot-demo",
        conversation_id=conv25["id"],
        content=query_25
    )

    msg_25 = res_25.get("message", {})
    card_25 = msg_25.get("structured_data", {})
    assert card_25.get("card_type") == "END_TO_END_SUMMARY"
    assert card_25.get("gross_margin_pct") == 25.0
    assert card_25.get("unit_cost") == 637.0
    assert card_25.get("selling_price") == 849.33
    assert abs(card_25.get("projected_profit", 0) - 106165.0) < 1.0
    assert "25.0% Gross Margin" in msg_25["content"]
    assert "849.33" in msg_25["content"]
