import os
import re
from typing import Dict, Any, List, Optional
from app.calculations.landed_cost import calculate_landed_cost
from app.calculations.scoring import evaluate_supplier_quotation
from app.calculations.inventory_netting import calculate_net_procurement_requirement
from app.calculations.bom_engine import explode_bom
from app.calculations.cost_engine import calculate_manufacturing_cost
from app.optimizers.procurement_optimizer import optimize_procurement_split
from app.services.negotiation_service import generate_counteroffer_draft, simulate_supplier_response

class IndusPilotAgentOrchestrator:
    """
    Coordinates IndusPilot's 9 specialized agents:
    1. Manufacturing Requirement Agent
    2. Document Intelligence Agent
    3. Supplier Intelligence Agent
    4. Procurement Planning Agent
    5. Negotiation Agent
    6. Cost Intelligence Agent
    7. Optimization Agent
    8. Customer Quotation Agent
    9. Supervisor Agent

    Supports English, Hindi, and Hinglish inputs with zero-key deterministic fallback.
    """

    def __init__(self, db_session=None):
        self.db = db_session

    def process_conversational_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Supervisor Agent: Analyzes query intent, selects the appropriate specialized agent,
        invokes deterministic backend tools, and explains the results.
        """
        q_lower = query.lower().strip()
        ctx = context or {}

        # 1. Detect language / intent
        # Support Hindi/Hinglish keywords: "karo", "batao", "kitna", "kharcha", "kam", "chahiye", "daam"
        
        # Intent A: Compare / Supplier Scoring
        if any(w in q_lower for w in ["compare", "tulna", "supplier b", "best supplier", "ranking", "kaunsa supplier"]):
            return self._handle_supplier_comparison(ctx)

        # Intent B: Inventory Shortage / Material Requirement
        elif any(w in q_lower for w in ["shortage", "inventory", "stock", "chahiye", "kitna material", "requirement"]):
            qty = self._extract_number_from_text(query, default=500.0)
            return self._handle_inventory_requirement(qty, ctx)

        # Intent C: Production Costing / Profitability
        elif any(w in q_lower for w in ["cost", "kharcha", "production cost", "profit", "margin", "calculate cost"]):
            qty = self._extract_number_from_text(query, default=500.0)
            return self._handle_cost_intelligence(qty, ctx)

        # Intent D: Negotiation / Counteroffer
        elif any(w in q_lower for w in ["negotiate", "counteroffer", "draft email", "bargain", "discount", "kam karao"]):
            return self._handle_negotiation_agent(ctx)

        # Intent E: OR-Tools Procurement Optimization
        elif any(w in q_lower for w in ["optimize", "allocation", "split", "budget", "or-tools"]):
            qty = self._extract_number_from_text(query, default=800.0)
            return self._handle_optimization_agent(qty, ctx)

        # Intent F: Customer Quotation
        elif any(w in q_lower for w in ["customer quote", "quotation banao", "quote for", "selling price", "bracket"]):
            qty = self._extract_number_from_text(query, default=500.0)
            return self._handle_customer_quotation(qty, ctx)

        # Default: General Manufacturing Copilot Assistance
        else:
            return {
                "agent_name": "Supervisor Agent",
                "intent_detected": "GENERAL_INQUIRY",
                "response_text": (
                    f"Hello! I am IndusPilot, your AI Manufacturing & Procurement Copilot. "
                    f"I can assist you with:\n"
                    f"1. **BOM & Inventory**: Check material shortages for production batches.\n"
                    f"2. **Quotation Intelligence**: Ingest and compare supplier quotes (landed costs & quality).\n"
                    f"3. **Autonomous Negotiation**: Prepare evidence-backed counteroffers with email drafts.\n"
                    f"4. **OR-Tools Optimization**: Allocate purchasing quantities across vendors under capacity & budget constraints.\n"
                    f"5. **14-Factor Costing**: Calculate exact shop-floor manufacturing costs and customer quotations.\n\n"
                    f"*Tip:* You can ask me in English, Hindi, or Hinglish, e.g., '500 brackets ka material shortage check karo' or 'Compare supplier quotations'."
                ),
                "data": None,
                "requires_human_approval": False
            }

    def _extract_number_from_text(self, text: str, default: float = 500.0) -> float:
        matches = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        if matches:
            for m in matches:
                val = float(m)
                if val >= 5: # reasonable batch size
                    return val
        return default

    def _handle_supplier_comparison(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Supplier Intelligence Agent"""
        # Benchmark quotation comparison pool
        candidates = ctx.get("candidates") or [
            {
                "supplier_name": "Apex Steel & Alloys Pvt Ltd",
                "unit_price": 315.0,
                "quantity": 800.0,
                "freight": 4500.0,
                "quality_rating": 4.6,
                "reliability_score": 92.0,
                "lead_time_days": 6,
                "payment_terms_days": 30
            },
            {
                "supplier_name": "Bharat Forgings & Metals",
                "unit_price": 298.0,
                "quantity": 800.0,
                "freight": 6000.0,
                "quality_rating": 4.0,
                "reliability_score": 78.0,
                "lead_time_days": 12,
                "payment_terms_days": 15
            },
            {
                "supplier_name": "Deccan Precision Alloys",
                "unit_price": 330.0,
                "quantity": 800.0,
                "freight": 3000.0,
                "quality_rating": 4.8,
                "reliability_score": 96.0,
                "lead_time_days": 4,
                "payment_terms_days": 45
            }
        ]

        evaluated = []
        all_landed = []
        all_leads = [c["lead_time_days"] for c in candidates]

        for c in candidates:
            landed = calculate_landed_cost(
                unit_price=c["unit_price"],
                quantity=c["quantity"],
                tax_pct=18.0,
                freight_total=c["freight"]
            )
            c["effective_landed"] = landed["effective_unit_landed_cost"]
            c["total_landed"] = landed["total_landed_cost"]
            all_landed.append(c["effective_landed"])

        for c in candidates:
            score_data = evaluate_supplier_quotation(
                unit_landed_cost=c["effective_landed"],
                all_landed_costs=all_landed,
                quality_rating=c["quality_rating"],
                reliability_score=c["reliability_score"],
                lead_time_days=c["lead_time_days"],
                all_lead_times=all_leads,
                payment_terms_days=c["payment_terms_days"]
            )
            c["scorecard"] = score_data
            evaluated.append(c)

        # Sort by composite score descending
        evaluated.sort(key=lambda x: x["scorecard"]["composite_score"], reverse=True)
        top_supplier = evaluated[0]

        return {
            "agent_name": "Supplier Intelligence Agent",
            "intent_detected": "SUPPLIER_COMPARISON",
            "response_text": (
                f"**Supplier Comparison Analysis Complete:**\n\n"
                f"Top Recommended Supplier: **{top_supplier['supplier_name']}** "
                f"(Composite Score: **{top_supplier['scorecard']['composite_score']}/100**, "
                f"Effective Landed: **₹{top_supplier['effective_landed']:.2f}/kg**).\n\n"
                f"**Why recommended?**\n"
                f"- High reliability ({top_supplier['reliability_score']}%)\n"
                f"- Fast delivery ({top_supplier['lead_time_days']} days vs average 7.3 days)\n"
                f"- Balanced cost-to-quality ratio.\n\n"
                f"*Comparison Summary:* {len(evaluated)} active quotations evaluated."
            ),
            "data": {
                "rankings": evaluated,
                "top_supplier": top_supplier
            },
            "requires_human_approval": False
        }

    def _handle_inventory_requirement(self, production_qty: float, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Procurement Planning Agent"""
        # BOM: 500 brackets requires 2.0 kg SS304 per bracket with 5% scrap
        bom_items = [
            {"material_id": "mat-ss304", "material_name": "Stainless Steel 304 Plate", "quantity_per_unit": 2.0, "wastage_pct": 5.0, "unit": "kg"}
        ]
        exploded = explode_bom(production_qty, bom_items)
        comp = exploded["components"][0]
        gross_req = comp["total_gross_required"]

        # Inventory check: current stock 250 kg, reserved 50 kg, incoming 0 kg, safety stock 50 kg
        net_calc = calculate_net_procurement_requirement(
            gross_requirement=gross_req,
            current_stock=250.0,
            reserved_stock=50.0,
            incoming_stock=0.0,
            safety_stock=50.0
        )

        return {
            "agent_name": "Procurement Planning Agent",
            "intent_detected": "INVENTORY_SHORTAGE_CHECK",
            "response_text": (
                f"**Material Requirement & Inventory Audit for {production_qty:,.0f} Finished Brackets:**\n\n"
                f"- **Gross Material Needed:** {gross_req:,.1f} kg Stainless Steel 304 (includes 5% scrap allowance)\n"
                f"- **Current Warehouse Stock:** {net_calc['current_stock']} kg (Available: {net_calc['available_stock']} kg after reservations)\n"
                f"- **Safety Stock Required:** {net_calc['safety_stock']} kg\n"
                f"- **Net Shortage to Purchase:** **{net_calc['net_shortage']:,.1f} kg**\n\n"
                f"**Action Recommended:** Purchase requisition of **{net_calc['net_shortage']:,.1f} kg** must be issued immediately."
            ),
            "data": {
                "bom_explosion": exploded,
                "inventory_netting": net_calc
            },
            "requires_human_approval": False
        }

    def _handle_cost_intelligence(self, production_qty: float, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Cost Intelligence Agent"""
        # 1000 kg SS304 @ ₹315/kg
        material_breakdown = [
            {"material_name": "SS304 Plate", "gross_quantity": production_qty * 2.1, "net_quantity": production_qty * 2.0, "unit_cost": 315.0}
        ]
        cost_res = calculate_manufacturing_cost(
            production_quantity=production_qty,
            material_costs_breakdown=material_breakdown,
            direct_labor_hours=120.0,
            labor_rate_per_hour=180.0,
            machine_hours=45.0,
            machine_rate_per_hour=350.0,
            electricity_kwh=650.0,
            electricity_tariff_per_kwh=8.50,
            secondary_processes_total=18000.0, # passivation & finishing
            transportation_total=6500.0,
            packaging_total=4500.0,
            overhead_pct=12.0,
            target_gross_margin_pct=25.0
        )

        ue = cost_res["unit_economics"]
        cb = cost_res["cost_breakdown"]

        return {
            "agent_name": "Cost Intelligence Agent",
            "intent_detected": "MANUFACTURING_COSTING",
            "response_text": (
                f"**Deterministic Manufacturing Cost Breakdown ({production_qty:,.0f} Units):**\n\n"
                f"- **Raw Material + Scrap:** ₹{cb['total_raw_material_cost']:,.2f}\n"
                f"- **Direct Labor ({cost_res['operational_rates']['labor_hours']} hrs):** ₹{cb['direct_labor_cost']:,.2f}\n"
                f"- **Machine Center ({cost_res['operational_rates']['machine_hours']} hrs):** ₹{cb['machine_operating_cost']:,.2f}\n"
                f"- **Electricity ({cost_res['operational_rates']['electricity_kwh']} kWh):** ₹{cb['electricity_cost']:,.2f}\n"
                f"- **Finishing & Overheads:** ₹{cb['secondary_processes_cost'] + cb['allocated_overhead_cost']:,.2f}\n\n"
                f"**Total Production Cost:** **₹{cb['total_production_cost']:,.2f}**\n"
                f"- **Cost per Unit (Break-even):** **₹{ue['break_even_price']:.2f}**\n"
                f"- **Suggested Selling Price (25% Gross Margin):** **₹{ue['suggested_unit_price']:.2f}**\n"
                f"- **Projected Gross Profit:** **₹{ue['projected_gross_profit']:,.2f}**"
            ),
            "data": cost_res,
            "requires_human_approval": False
        }

    def _handle_negotiation_agent(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Negotiation Agent"""
        draft = generate_counteroffer_draft(
            supplier_name="Apex Steel & Alloys Pvt Ltd",
            material_name="Stainless Steel 304 Sheet Plate",
            quantity=800.0,
            unit="kg",
            current_offered_price=315.0,
            target_price=295.0,
            benchmark_market_price=300.0,
            competitor_lowest_price=298.0,
            current_payment_terms="30 Days Net",
            improved_payment_terms="15 Days Immediate Credit"
        )

        return {
            "agent_name": "Negotiation Agent",
            "intent_detected": "COUNTEROFFER_GENERATION",
            "response_text": (
                f"**Negotiation Strategy & Counteroffer Prepared:**\n\n"
                f"- **Supplier:** Apex Steel & Alloys Pvt Ltd\n"
                f"- **Original Quoted Price:** ₹315.00/kg\n"
                f"- **Target Counter Price:** **₹295.00/kg** (Discount: 6.3%, Potential Savings: **₹16,000.00**)\n"
                f"- **Leverage Used:** Order volume (800 kg), competitor pricing (₹298.00/kg), and improved 15-day payment terms.\n\n"
                f"**Generated Email Draft:**\n"
                f"```\n{draft['email_body']}\n```\n\n"
                f"⚠️ *Human Approval Safeguard:* This counteroffer is in `READY_FOR_APPROVAL` state. "
                f"Click 'Approve & Send' in the Negotiation Centre to transmit."
            ),
            "data": draft,
            "requires_human_approval": True
        }

    def _handle_optimization_agent(self, required_qty: float, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Optimization Agent"""
        candidates = [
            {"supplier_id": "sup-apex", "supplier_name": "Apex Steel & Alloys Pvt Ltd", "unit_landed_cost": 320.6, "fixed_freight": 4500.0, "capacity": 1000.0, "moq": 200.0, "lead_time_days": 6},
            {"supplier_id": "sup-bharat", "supplier_name": "Bharat Forgings & Metals", "unit_landed_cost": 305.5, "fixed_freight": 6000.0, "capacity": 500.0, "moq": 500.0, "lead_time_days": 12},
            {"supplier_id": "sup-deccan", "supplier_name": "Deccan Precision Alloys", "unit_landed_cost": 333.7, "fixed_freight": 3000.0, "capacity": 1200.0, "moq": 100.0, "lead_time_days": 4}
        ]

        opt_res = optimize_procurement_split(
            required_quantity=required_qty,
            supplier_candidates=candidates,
            budget_limit=ctx.get("budget_limit", 300000.0)
        )

        return {
            "agent_name": "Optimization Agent",
            "intent_detected": "OR_TOOLS_OPTIMIZATION",
            "response_text": (
                f"**Google OR-Tools Mathematical Optimization Result:**\n\n"
                f"- **Solver Status:** {opt_res['status']}\n"
                f"- **Total Optimal Landed Cost:** **₹{opt_res['total_cost']:,.2f}**\n"
                f"- **Budget Utilized:** {opt_res['budget_utilized_pct']}%\n\n"
                f"**Allocations:**\n" +
                "\n".join([f"- **{a['supplier_name']}**: {a['allocated_quantity']:.1f} kg @ ₹{a['unit_landed_cost']:.2f}/kg" for a in opt_res['allocations']]) +
                f"\n\n**Mathematical Rationale:**\n{opt_res['explanation']}"
            ),
            "data": opt_res,
            "requires_human_approval": False
        }

    def _handle_customer_quotation(self, production_qty: float, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Customer Quotation Agent"""
        quote_data = {
            "quote_number": f"IP-CQ-2026-{int(production_qty)}",
            "customer_name": "Larsen Heavy Machinery Corp",
            "customer_company": "L&H Industrial Equipment Division",
            "product_name": "Stainless Steel Industrial Bracket",
            "product_code": "SS304-BRK-500",
            "quantity": production_qty,
            "unit_cost": 637.0,
            "unit_selling_price": 850.0,
            "subtotal": production_qty * 850.0,
            "tax_amount": (production_qty * 850.0) * 0.18,
            "total_amount": (production_qty * 850.0) * 1.18,
            "margin_pct": 25.1,
            "payment_terms": "50% Advance, 50% Against Delivery",
            "delivery_weeks": 3,
            "is_loss_making": False
        }

        return {
            "agent_name": "Customer Quotation Agent",
            "intent_detected": "CUSTOMER_QUOTATION_GENERATION",
            "response_text": (
                f"**Customer Commercial Quotation Drafted:**\n\n"
                f"- **Customer:** {quote_data['customer_name']} ({quote_data['customer_company']})\n"
                f"- **Product:** {quote_data['product_name']} ({quote_data['quantity']:,.0f} units)\n"
                f"- **Factory Cost per Unit:** ₹{quote_data['unit_cost']:.2f}\n"
                f"- **Proposed Selling Price:** **₹{quote_data['unit_selling_price']:.2f} / unit**\n"
                f"- **Projected Gross Margin:** **{quote_data['margin_pct']}%** (Healthy, above 20% floor)\n"
                f"- **Total Order Value:** **₹{quote_data['total_amount']:,.2f}** (incl. 18% GST)\n\n"
                f"Commercial PDF is generated and ready for human approval."
            ),
            "data": quote_data,
            "requires_human_approval": True
        }

