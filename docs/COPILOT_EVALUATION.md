# IndusPilot AI Copilot Evaluation Benchmark: 20 Deterministic Scenarios

## Benchmark Overview

This document specifies the **20 deterministic evaluation scenarios** used to validate the IndusPilot AI Copilot and Multi-Agent Supervisor System. Every scenario defines the input prompt, detected intent, primary agents invoked, backend tools executed, and verified deterministic outputs.

All 20 test cases pass deterministically in both real LLM mode and zero-credential offline `DEMO MODE`.

---

## Evaluation Scenarios Matrix

| Scenario # | Category | User Input Prompt | Detected Intent | Expected Primary Agent | Tools Invoked | Verified Deterministic Output |
|---|---|---|---|---|---|---|
| **01** | Multi-Step Master | "I have received an order for 500 stainless steel industrial brackets. Check inventory, find required materials, optimise procurement within 5 lakh and calculate profit at 20% margin." | `END_TO_END_MANUFACTURING_WORKFLOW` | `Supervisor Agent` | `calculate_bom_requirements`, `calculate_material_shortages`, `list_supplier_quotations`, `compare_supplier_quotations`, `create_procurement_plan`, `calculate_manufacturing_cost`, `create_customer_quotation_draft` | 1,050 kg gross, 750 kg shortage, Apex Steel awarded, profit > ₹75,000, `PendingAgentAction` created. |
| **02** | Sourcing Comparison | "Compare supplier quotations and identify the top candidate for SS304 plate." | `SUPPLIER_COMPARISON` | `Supplier Intelligence Agent` | `list_supplier_quotations`, `compare_supplier_quotations` | Top supplier: Apex Steel & Alloys Pvt Ltd, Composite Score: 84.5/100, Landed Cost: ₹315.00/kg. |
| **03** | MRP Shortage Check | "Check warehouse inventory shortages for 500 brackets." | `INVENTORY_SHORTAGE_CHECK` | `Procurement Planning Agent` | `calculate_bom_requirements`, `calculate_material_shortages` | Gross required: 1,050.0 kg, Available: 350.0 kg, Critical shortage: 750.0 kg. |
| **04** | BOM Explosion | "Show me the bill of materials components and gross formula for industrial bracket." | `BOM_REQUIREMENT_CALCULATION` | `Procurement Planning Agent` | `get_product_bom`, `calculate_bom_requirements` | 4 components exploded, scrap allowance applied (5% for SS304 plate). |
| **05** | Production Costing | "Calculate 14-factor manufacturing cost breakdown for 500 units." | `MANUFACTURING_COSTING` | `Manufacturing Cost Agent` | `calculate_manufacturing_cost`, `calculate_target_selling_price` | Direct raw material: ₹2,36,250.00, Labor: ₹21,600.00, Break-even price: ₹637.00/unit. |
| **06** | MILP Optimization | "Optimize procurement allocation for stainless steel using OR-Tools solver." | `PROCUREMENT_OPTIMIZATION` | `Procurement Optimisation Agent` | `create_procurement_plan`, `inspect_optimization_result` | Solver status: `OPTIMAL`, multi-supplier split satisfying MOQ and capacity limits. |
| **07** | Negotiation Strategy | "Analyze negotiation opportunity and formulate target discount for Apex Steel." | `SUPPLIER_NEGOTIATION` | `Negotiation Agent` | `analyse_negotiation_opportunity`, `generate_negotiation_message` | Target concession: 6.2%, Counter-offer message drafted with volume commitment terms. |
| **08** | Customer Quotation | "Draft customer quotation for 500 units at a 25% gross margin." | `CUSTOMER_QUOTATION` | `Customer Quotation Agent` | `create_customer_quotation_draft`, `evaluate_quotation_profitability` | Unit selling price: ₹849.33, Total quote value: ₹5,01,105.00 (incl. 18% GST), Status: `READY_FOR_APPROVAL`. |
| **09** | Hindi Inventory | "500 bracket ke liye stock check karo aur shortage batao kitna material chahiye." | `INVENTORY_SHORTAGE_CHECK` | `Procurement Planning Agent` | `calculate_material_shortages` | Correctly parses quantity (500), reports 750.0 kg critical shortage. |
| **10** | Hinglish Supplier | "Stainless steel 304 ke liye kaunsa supplier best hai compare karke batao." | `SUPPLIER_COMPARISON` | `Supplier Intelligence Agent` | `compare_supplier_quotations` | Identifies SS304 grade, ranks Apex Steel as top candidate. |
| **11** | Hinglish Negotiation | "Apex steel se 300 rs per kg pe negotiate karne ke liye email draft karo." | `SUPPLIER_NEGOTIATION` | `Negotiation Agent` | `generate_negotiation_message` | Generates Hinglish negotiation email with ₹300/kg target and payment terms. |
| **12** | Hindi Costing | "500 bracket banane mein factory ka total manufacturing cost kitna aayega?" | `MANUFACTURING_COSTING` | `Manufacturing Cost Agent` | `calculate_manufacturing_cost` | Computes audited production cost of ₹3,18,500.00. |
| **13** | Context Continuity (Turn 1) | "Check inventory shortage for 500 stainless steel industrial brackets." | `INVENTORY_SHORTAGE_CHECK` | `Procurement Planning Agent` | `calculate_material_shortages` | Establishes context: Product `IND-BRK-SS304`, Quantity: 500, Material: SS304. |
| **14** | Context Continuity (Turn 2) | "Calculate manufacturing costing breakdown for this batch." | `MANUFACTURING_COSTING` | `Manufacturing Cost Agent` | `calculate_manufacturing_cost` | Retains quantity 500 and product code from Turn 1 without re-prompting. |
| **15** | Context Quantity Update | "What if we increase order quantity to 1000 brackets?" | `INVENTORY_SHORTAGE_CHECK` | `Procurement Planning Agent` | `calculate_material_shortages` | Updates quantity in memory to 1,000; scales gross requirement to 2,100 kg. |
| **16** | Budget Constraint | "Optimize procurement allocation under a strict ₹3 Lakh budget limit." | `PROCUREMENT_OPTIMIZATION` | `Procurement Optimisation Agent` | `create_procurement_plan` | Extracts `budget_limit = 300000.0`, enforces constraint in OR-Tools solver. |
| **17** | Loss-Making Protection | "Draft customer quote at ₹500 per unit for 500 brackets." | `CUSTOMER_QUOTATION` | `Customer Quotation Agent` | `evaluate_quotation_profitability` | Identifies ₹500 < ₹637 break-even cost, triggers `LOSS_MAKING` contract alert. |
| **18** | Action Authorization | `POST /api/v1/copilot/actions/{id}/approve` | `HITL_APPROVAL` | `Supervisor Agent` | `approve_pending_action` | Action transitions from `PENDING` $\to$ `APPROVED`, run marked `COMPLETED`. |
| **19** | Action Rejection | `POST /api/v1/copilot/actions/{id}/reject` | `HITL_REJECTION` | `Supervisor Agent` | `reject_pending_action` | Action transitions to `REJECTED`, stores executive revision rationale. |
| **20** | Multi-Tenant Scoping | Query executed under `X-Organization-ID: org-tenant-beta`. | Multi-Tenant Enforcement | Multi-Agent Supervisor | `list_supplier_quotations`, `check_inventory_stock` | Queries strictly isolated to Org Beta records; zero data bleed from Org Alpha. |

