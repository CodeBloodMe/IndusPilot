# IndusPilot Central Typed Tool Registry & Governance Framework

## Overview

The IndusPilot **Central Typed Tool Registry** (`backend/app/agents/tools/registry.py`) provides an auditable, type-safe interface between autonomous AI agents and live manufacturing business services.

Every tool in the registry:
1. Is strictly typed using **Pydantic v2 schemas** for arguments and validation.
2. Is classified into one of **four explicit permission tiers**.
3. Executes against the live PostgreSQL/SQLite database within tenant-isolated scopes (`X-Organization-ID`).
4. Logs execution telemetry to `agent_tool_calls` including duration (ms), input/output payloads, and success status.

---

## Permission Tiers

| Tier | Code | Description | Example Tools |
|---|---|---|---|
| **Tier 1** | `READ_ONLY` | Read-only inspection; zero mutation risk. Autonomous execution allowed. | `search_suppliers`, `calculate_material_shortages`, `inspect_optimization_result`, `calculate_manufacturing_cost` |
| **Tier 2** | `DRAFT_CREATION` | Creates draft proposals; does not mutate live factory assets or commit funds. | `create_procurement_plan`, `generate_negotiation_message`, `create_customer_quotation_draft`, `generate_customer_quotation_pdf` |
| **Tier 3** | `SENSITIVE_MUTATION` | Modifies live physical stock, reservations, or negotiated vendor rates. | `adjust_inventory_level`, `apply_negotiated_rate`, `reserve_material_stock` |
| **Tier 4** | `EXTERNAL_ACTION` | Transmits external communications or contracts to third parties. | `dispatch_customer_quotation`, `send_negotiation_counteroffer_email` |

---

## 30+ Typed Tools Catalog

### Domain 1: Supplier Intelligence Tools
1. `search_suppliers`: Searches suppliers by location, quality rating, or material capability. (Tier: `READ_ONLY`)
2. `get_supplier_details`: Retrieves deep supplier profile, contacts, payment terms, and past delivery performance. (Tier: `READ_ONLY`)
3. `list_supplier_quotations`: Discovers quotations filtered by status (`VERIFIED`, `PENDING_REVIEW`). (Tier: `READ_ONLY`)
4. `get_supplier_performance`: Computes vendor OTIF delivery %, defect PPM, and historical compliance. (Tier: `READ_ONLY`)
5. `compare_supplier_quotations`: Executes 100-point composite scoring comparison across a cohort of quotations. (Tier: `READ_ONLY`)
6. `calculate_landed_cost`: Computes base cost, freight, insurance, and GST landing price. (Tier: `READ_ONLY`)
7. `match_material_specification`: Matches raw quotation text against material catalogue grades. (Tier: `READ_ONLY`)
8. `list_uploaded_documents`: Lists ingested quotation and invoice documents. (Tier: `READ_ONLY`)

### Domain 2: Inventory & BOM Tools
9. `get_product_bom`: Retrieves bill of materials hierarchy for a finished good. (Tier: `READ_ONLY`)
10. `calculate_bom_requirements`: Explodes BOM to calculate gross component requirements including scrap. (Tier: `READ_ONLY`)
11. `check_inventory_stock`: Inspects physical, reserved, available, and incoming stock levels. (Tier: `READ_ONLY`)
12. `calculate_material_shortages`: Computes MRP net shortages against active production requirements. (Tier: `READ_ONLY`)
13. `adjust_inventory_level`: Adjusts warehouse physical stock level with audit justification. (Tier: `SENSITIVE_MUTATION`)

### Domain 3: Procurement Optimization Tools
14. `create_procurement_plan`: Solves multi-supplier MILP allocation model via Google OR-Tools. (Tier: `DRAFT_CREATION`)
15. `inspect_optimization_result`: Inspects solver status (`OPTIMAL`, `FEASIBLE`), allocations, and savings. (Tier: `READ_ONLY`)
16. `benchmark_procurement_savings`: Benchmarks optimal landed cost against single-source median pricing. (Tier: `READ_ONLY`)

### Domain 4: Negotiation Tools
17. `analyse_negotiation_opportunity`: Identifies price improvement headroom and target discount ranges. (Tier: `READ_ONLY`)
18. `generate_negotiation_message`: Drafts structured counter-offer message (English, Hindi, Hinglish). (Tier: `DRAFT_CREATION`)
19. `simulate_supplier_response`: Simulates vendor counter-concession curves under exponential decay `[SIMULATED]`. (Tier: `DRAFT_CREATION`)
20. `apply_negotiated_rate`: Applies negotiated unit price to supplier quotation record. (Tier: `SENSITIVE_MUTATION`)

### Domain 5: Manufacturing Costing Tools
21. `calculate_manufacturing_cost`: Calculates audited 14-factor production cost breakdown. (Tier: `READ_ONLY`)
22. `calculate_target_selling_price`: Computes break-even price and suggested selling price at target margin. (Tier: `READ_ONLY`)

### Domain 6: Customer Quotation Tools
23. `create_customer_quotation_draft`: Creates draft customer quotation with loss-making contract protection. (Tier: `DRAFT_CREATION`)
24. `evaluate_quotation_profitability`: Verifies whether quote is `PROFITABLE`, `BELOW_TARGET_MARGIN`, or `LOSS_MAKING`. (Tier: `READ_ONLY`)
25. `generate_customer_quotation_pdf`: Renders commercial PDF quotation with Indian Rupee formatting. (Tier: `DRAFT_CREATION`)
26. `dispatch_customer_quotation`: Dispatches quotation to customer via email. (Tier: `EXTERNAL_ACTION`)

### Domain 7: Governance & Approval Tools
27. `list_pending_approvals`: Retrieves pending commercial action approval requests. (Tier: `READ_ONLY`)
28. `request_action_approval`: Creates human-in-the-loop approval checkpoint for high-risk operations. (Tier: `DRAFT_CREATION`)
29. `retrieve_approval_status`: Checks current decision status of an approval request. (Tier: `READ_ONLY`)

---

## Tool Execution Flow

```python
result = registry.execute_tool(
    name="calculate_material_shortages",
    arguments={"product_id": "IND-PRD-BRK", "production_quantity": 500.0},
    org_id=state["org_id"],
    db=db_session,
    run_id=state.get("run_id")
)
```
1. Validates `arguments` against `CalculateMaterialShortagesInput` Pydantic model.
2. Checks tool existence and permission requirements.
3. Executes real backend logic.
4. Logs execution time (ms) and status to `agent_tool_calls` table.
5. Returns typed dictionary payload `{"success": True, "data": ...}`.

