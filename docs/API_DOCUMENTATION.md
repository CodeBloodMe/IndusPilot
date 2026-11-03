# IndusPilot — API Documentation & Integration Specification

**System Name:** IndusPilot API Gateway  
**Base URL:** `http://localhost:8000/api/v1`  
**Specification Standard:** OpenAPI 3.1 / JSON REST  
**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI) & `/redoc` (ReDoc)  

---

## 1. Authentication & Multi-Tenant Scoping

All API endpoints enforce multi-tenant isolation. Requests should include the enterprise tenant header:
```http
X-Organization-ID: org_tech4bharat_induspilot_demo
```
If omitted, the API defaults to the demonstration tenant (`org_tech4bharat_induspilot_demo`).

---

## 2. Core Endpoints Specification

### 2.1 Dashboard & Intelligence Overview
#### `GET /api/v1/dashboard/metrics`
Computes live KPIs across procurement spend, active vendor base, inventory shortages, and negotiation cost savings.

**Response (200 OK):**
```json
{
  "procurement_spend_total": 903692.00,
  "active_suppliers_count": 10,
  "verified_quotations_count": 3,
  "pending_quotations_count": 0,
  "pending_approvals_count": 1,
  "material_shortages_count": 0,
  "total_savings_generated": 16000.00,
  "critical_shortages": [],
  "recent_quotations": [
    {
      "id": "qtn_8821",
      "quotation_number": "APX-2026-QTN-8821",
      "supplier_name": "Apex Steel & Alloys Pvt Ltd",
      "total_amount": 301860.00,
      "date": "12 Oct 2026"
    }
  ],
  "currency_symbol": "₹"
}
```

---

### 2.2 Supplier Directory
#### `GET /api/v1/suppliers`
Retrieves suppliers with filtering by material grade and quality ratings.

**Query Parameters:**
- `material_filter` (optional string): e.g. `ss304`
- `min_rating` (optional float): e.g. `4.0`

**Response (200 OK):**
```json
[
  {
    "id": "sup-apex-uuid",
    "organization_id": "org_tech4bharat_induspilot_demo",
    "name": "Apex Steel & Alloys Pvt Ltd",
    "contact_person": "Suresh Hegde",
    "city": "Bengaluru",
    "state": "Karnataka",
    "quality_rating": 4.6,
    "reliability_score": 92.0,
    "on_time_delivery_pct": 94.0,
    "payment_terms_days": 30,
    "is_simulated": true
  }
]
```

---

### 2.3 Quotation Ingestion & Quality Gate
#### `POST /api/v1/quotations/upload`
Uploads raw quotation files (PDF, XLSX, CSV, JPG, PNG). Executes PyMuPDF / regex extraction and checks the automated Quality Gate.

**Request:** `multipart/form-data` with `file=@apex_steel_quotation_ss304.pdf`

**Response (200 OK):**
```json
{
  "success": true,
  "filename": "apex_steel_quotation_ss304.pdf",
  "confidence_score": 0.96,
  "status": "VERIFIED",
  "supplier_name": "Apex Steel & Alloys Pvt Ltd",
  "quotation_number": "APX-2026-QTN-8821",
  "subtotal": 252000.00,
  "tax_pct": 18.0,
  "tax_amount": 45360.00,
  "is_tax_inclusive": false,
  "freight_cost": 4500.00,
  "total_amount": 301860.00,
  "items": [
    {
      "material_name": "Stainless Steel 304 Sheet Plate (2B Finish)",
      "grade": "AISI 304 / DIN 1.4301",
      "quantity": 800.0,
      "unit": "kg",
      "unit_price": 315.00,
      "moq": 200.0,
      "lead_time_days": 6,
      "line_total": 252000.00,
      "is_quarantined": false
    }
  ]
}
```

---

### 2.4 Smart Supplier Comparison & Decision Engine

#### `POST /api/v1/comparisons/analyze` (aliased at `POST /api/v1/compare/evaluate`)
Performs deterministic multi-criteria eligibility assessment, landed cost calculation, dynamic weight-renormalized 5-factor scoring, and explainable decision narrative generation.

**Request Body:**
```json
{
  "material_id": "mat-ss304-sheet",
  "product_id": "prod-enclosure-01",
  "required_quantity": 800.0,
  "required_date": "2026-11-20T00:00:00Z",
  "target_unit_price": 310.0,
  "delivery_location": "Peenya Industrial Area, Bengaluru",
  "quality_standard": "IS 6911 / ASTM A240",
  "weights": {
    "cost": 35.0,
    "quality": 25.0,
    "reliability": 15.0,
    "lead_time": 15.0,
    "payment_terms": 10.0
  },
  "quotation_ids": ["qtn_1", "qtn_2"]
}
```

**Response (200 OK):**
```json
{
  "comparison_id": "cmp_8d92f1b0a8",
  "organization_id": "org_tech4bharat_induspilot_demo",
  "target_quantity": 800.0,
  "evaluated_at": "2026-11-03T12:00:00Z",
  "recommended_candidate": {
    "supplier_id": "sup-titan-alloy",
    "supplier_name": "Titan Alloy & Plate Distribution Ltd",
    "quotation_id": "qtn_titan_304",
    "quotation_number": "TAP-2026-QTN-8821",
    "eligibility_status": "ELIGIBLE",
    "composite_score": 88.5,
    "decision_band": "STRONGLY_RECOMMENDED",
    "effective_unit_landed_cost": 377.33,
    "total_landed_cost": 301860.0,
    "rationale": "Strongly recommended as primary supplier with leading composite score of 88.5/100.",
    "cost_breakdown": {
      "base_material_cost": 252000.0,
      "tax_amount": 45360.0,
      "freight_cost": 4500.0,
      "packaging_cost": 0.0,
      "insurance_cost": 0.0,
      "effective_unit_cost": 377.33,
      "tax_treatment": "TAX_EXCLUDED",
      "currency": "INR"
    },
    "score_breakdown": {
      "cost_score": 94.2,
      "quality_score": 92.0,
      "reliability_score": 94.0,
      "lead_time_score": 85.0,
      "payment_terms_score": 33.3,
      "composite_score": 88.5,
      "evidence_completeness_score": 1.0,
      "is_provisional": false
    }
  },
  "category_leaders": {
    "overall_best": {...},
    "lowest_cost": {...},
    "fastest_delivery": {...},
    "highest_quality": {...}
  },
  "candidates": [...]
}
```

#### `POST /api/v1/comparisons/eligibility`
Performs standalone eligibility constraint checks on an individual quotation without running full multi-supplier scoring.

**Request Body:**
```json
{
  "quotation_id": "qtn_titan_304",
  "required_quantity": 800.0,
  "required_grade": "SS304",
  "required_thickness_mm": 2.0,
  "required_delivery_date": "2026-11-20T00:00:00Z",
  "required_unit": "kg"
}
```

**Response (200 OK):**
```json
{
  "quotation_id": "qtn_titan_304",
  "status": "ELIGIBLE",
  "is_eligible": true,
  "reasons": ["Passed all technical and operational constraints."],
  "warnings": [],
  "details": {
    "grade_match": true,
    "thickness_match": true,
    "moq_satisfied": true,
    "deadline_satisfied": true,
    "is_valid": true,
    "is_quarantined": false
  }
}
```

#### `POST /api/v1/comparisons/landed-cost`
Computes deterministic landed cost breakdown for given commercial terms.

**Request Body:**
```json
{
  "unit_price": 315.0,
  "quantity": 800.0,
  "tax_rate_percent": 18.0,
  "tax_treatment": "TAX_EXCLUDED",
  "freight_charges": 4500.0,
  "payment_terms_days": 30
}
```

#### `GET /api/v1/comparisons/{comparison_id}`
Retrieves a previously computed and persisted comparison analysis result.

---

### 2.5 Materials Benchmark & Price History

#### `GET /api/v1/materials/{material_id}/price-history`
Returns 12-month historical price trend data, 30-day/90-day moving averages, and minimum/maximum ranges.

**Response (200 OK):**
```json
{
  "material_id": "mat-ss304-sheet",
  "material_name": "Stainless Steel 304 Sheet 2mm",
  "unit": "kg",
  "history": [
    { "date": "2026-08-15", "avg_price": 320.0, "low_price": 310.0, "high_price": 330.0 },
    { "date": "2026-09-15", "avg_price": 315.0, "low_price": 305.0, "high_price": 322.0 }
  ],
  "current_benchmark": 315.0,
  "moving_average_90d": 318.5
}
```

---

### 2.6 Supplier Performance Analytics

#### `GET /api/v1/suppliers/{supplier_id}/performance`
Returns comprehensive quality rating, on-time delivery percentage, rejection rate, defect history, and total fulfilled spend.

---

### 2.7 Procurement Requisitions Handoff

#### `POST /api/v1/procurement/requisitions`
Creates an official internal Purchase Requisition linked to an approved quotation and supplier.

**Request Body:**
```json
{
  "supplier_id": "sup-titan-alloy",
  "material_id": "mat-ss304-sheet",
  "quotation_id": "qtn_titan_304",
  "quantity": 800.0,
  "target_price": 315.0,
  "notes": "Fast-track order for Batch #042 assembly",
  "delivery_deadline": "2026-11-20"
}
```

**Response (201 Created):**
```json
{
  "id": "req-9c81a2",
  "requisition_number": "PR-2026-0042",
  "supplier_id": "sup-titan-alloy",
  "quantity": 800.0,
  "status": "PENDING_APPROVAL",
  "created_at": "2026-11-03T12:00:00Z"
}
```

#### `GET /api/v1/procurement/requisitions`
Lists all active and historical procurement requisitions.

---

### 2.5 Bill of Materials & Inventory Netting
#### `POST /api/v1/bom/explode`
Calculates gross material requirements incorporating scrap/wastage percentages and nets against warehouse stock.

**Request Body:**
```json
{
  "product_id": "prod-bracket-500",
  "production_quantity": 500.0
}
```

**Response (200 OK):**
```json
{
  "product": { "name": "Stainless Steel Industrial Bracket (500mm)", "code": "SS304-BRK-500" },
  "production_quantity": 500.0,
  "components_count": 4,
  "shortages_count": 1,
  "total_shortage_mass_kg": 900.0,
  "components": [
    {
      "material_name": "Stainless Steel 304 Sheet Plate",
      "net_quantity_per_unit": 2.0,
      "wastage_pct": 5.0,
      "total_gross_required": 1050.0,
      "inventory_status": {
        "current_stock": 250.0,
        "available_stock": 200.0,
        "safety_stock": 50.0,
        "net_shortage": 900.0,
        "has_shortage": true
      }
    }
  ]
}
```

---

### 2.6 Manufacturing Cost Intelligence Engine
#### `POST /api/v1/costing/calculate`
Executes deterministic 14-factor manufacturing cost calculation with Python Decimal arithmetic.

**Request Body:**
```json
{
  "production_quantity": 500.0,
  "material_costs_breakdown": [
    { "material_name": "SS304 Plate", "unit_cost": 315.0, "gross_quantity": 1050.0, "net_quantity": 1000.0 }
  ],
  "direct_labor_hours": 120.0,
  "labor_rate_per_hour": 180.0,
  "machine_hours": 45.0,
  "machine_rate_per_hour": 350.0,
  "electricity_kwh": 650.0,
  "electricity_tariff_per_kwh": 8.50,
  "secondary_processes_total": 18000.0,
  "transportation_total": 6500.0,
  "packaging_total": 4500.0,
  "overhead_pct": 12.0,
  "target_gross_margin_pct": 25.0
}
```

**Response (200 OK):**
```json
{
  "production_quantity": 500.0,
  "cost_breakdown": {
    "total_raw_material_cost": 330750.00,
    "direct_labor_cost": 21600.00,
    "machine_operating_cost": 15750.00,
    "electricity_cost": 5525.00,
    "secondary_processes_cost": 18000.00,
    "transportation_cost": 6500.00,
    "packaging_cost": 4500.00,
    "allocated_overhead_cost": 48315.00,
    "total_production_cost": 450940.00
  },
  "unit_economics": {
    "unit_cost": 901.88,
    "break_even_price": 901.88,
    "suggested_unit_price": 1202.51,
    "total_revenue": 601255.00,
    "projected_gross_profit": 150315.00,
    "effective_margin_pct": 25.0,
    "is_loss_making": false
  }
}
```

---

### 2.7 Google OR-Tools Procurement Optimization
#### `POST /api/v1/optimizer/solve`
Solves multi-supplier allocation using Mixed-Integer Linear Programming.

**Request Body:**
```json
{
  "required_quantity": 800.0,
  "budget_limit": 300000.0
}
```

**Response (200 OK):**
```json
{
  "status": "OPTIMAL",
  "required_quantity": 800.0,
  "total_cost": 260500.00,
  "budget_utilized_pct": 86.8,
  "allocated_suppliers_count": 2,
  "allocations": [
    {
      "supplier_name": "Bharat Forgings & Metals",
      "allocated_quantity": 500.0,
      "unit_landed_cost": 305.50
    },
    {
      "supplier_name": "Apex Steel & Alloys Pvt Ltd",
      "allocated_quantity": 300.0,
      "unit_landed_cost": 320.60
    }
  ],
  "explanation": "Volume is split across 2 suppliers to satisfy capacity limits and minimize overall landed cost."
}
```

---

### 2.8 Autonomous Negotiation State Machine
#### `POST /api/v1/negotiation/start`
Initializes a negotiation session and drafts an evidence-backed counteroffer (`READY_FOR_APPROVAL`).

#### `POST /api/v1/negotiation/send-and-simulate?session_id={id}`
Simulates transmission of the approved counteroffer and computes the vendor's concession curve.

---

### 2.9 Customer Quotation Generator & PDF
#### `POST /api/v1/customer-quotes/generate`
Builds a customer commercial quotation, verifies margin thresholds, and renders a PDF quotation.

#### `GET /api/v1/customer-quotes/{id}/download-pdf`
Streams the generated commercial PDF document.

---

### 2.10 Multilingual AI Copilot
#### `POST /api/v1/copilot/chat`
Conversational assistant supporting English, Hindi, and Hinglish with real tool invocation.

**Sample Hinglish Request:**
```json
{
  "query": "Apex Steel ka quotation compare karo aur batao kitna kharcha aayega 500 units ke liye"
}
```

---

## 3. Phase 5 Manufacturing Intelligence API Endpoints

### 3.1 Products Catalogue
- `GET /api/v1/products`: List all manufactured products in the tenant.
- `POST /api/v1/products`: Create a new manufactured product with process, base unit, and default batch size.
- `GET /api/v1/products/{product_id}`: Retrieve detailed product metadata and associated BOM revisions.
- `PATCH /api/v1/products/{product_id}`: Update manufacturing parameters or active status.

### 3.2 Bill of Materials (BOM) & Revision Control
- `GET /api/v1/boms`: List BOMs with optional filtering by `product_id` and `is_active`.
- `POST /api/v1/boms`: Create an engineering BOM with items, scrap allowances (`ADDITIVE_SCRAP` or `YIELD_BASED`), and routing stages.
- `GET /api/v1/boms/{bom_id}`: Retrieve BOM details and itemized specifications.
- `POST /api/v1/boms/{bom_id}/revisions`: Create a new immutable revision (e.g. `v2.0`), optionally setting it as active.
- `POST /api/v1/boms/{bom_id}/validate`: Run automated engineering checks (orphaned materials, duplicates, negative quantities, scrap > 100%).
- `GET /api/v1/boms/compare?bom_id_1={id1}&bom_id_2={id2}`: Side-by-side diff comparing two BOM revisions (added/removed items, quantity & scrap variances).
- `POST /api/v1/boms/explode`: Explode a BOM for a planned batch size, applying scrap models and netting against live warehouse stock.

### 3.3 Perpetual Inventory Ledger & Movements
- `GET /api/v1/inventory/ledger`: Real-time stock ledger returning physical stock, reserved stock, available stock, moving average cost, and status.
- `POST /api/v1/inventory/receive`: Post inbound raw material stock with quantity, unit cost, and idempotency key protection.
- `POST /api/v1/inventory/issue`: Issue stock to machines or production bays (enforces negative stock prevention).
- `POST /api/v1/inventory/reserve`: Lock material to a production job (`StockReservation`).
- `POST /api/v1/inventory/release`: Release a stock reservation if a job is cancelled or modified.
- `POST /api/v1/inventory/adjust`: Physical cycle count reconciliation with recorded adjustment delta and audit notes.
- `GET /api/v1/inventory/alerts`: List critical shortages, reorder point triggers, and overstock warnings.
- `GET /api/v1/inventory/movements`: Immutable perpetual movement transaction history.
- `POST /api/v1/inventory/check-availability`: Batch stock availability check for multiple materials.

### 3.4 Production Jobs & MRP
- `GET /api/v1/production/jobs`: List manufacturing jobs with filtering by status.
- `POST /api/v1/production/jobs`: Create a production job order linked to a product and active BOM.
- `GET /api/v1/production/jobs/{job_id}`: Retrieve job order status, timeline, and material allocations.
- `POST /api/v1/production/jobs/{job_id}/material-check`: Execute MRP explosion, net against warehouse stock, and compute shortages.
- `POST /api/v1/production/jobs/{job_id}/procurement-handoff`: Automatically generate purchase requisitions and handoff shortages to the procurement comparison engine.

### 3.5 Deterministic 14-Factor Costing & What-If Simulations
- `POST /api/v1/costing/estimate`: Calculate and persist a complete 14-factor manufacturing cost estimate, break-even price, and target selling price.
- `GET /api/v1/costing/estimates`: List historical cost estimates.
- `GET /api/v1/costing/estimates/{estimate_id}`: Retrieve detailed estimate breakdown, assumptions snapshot, and data quality status.
- `POST /api/v1/costing/simulate`: Run What-If sensitivity simulations (material price variations, batch size economies of scale, scrap reductions, labor rate deltas) against a baseline estimate.
- `POST /api/v1/costing/scenarios`: Save a simulation scenario snapshot for management review.

---

## 4. Phase 6 Advanced Procurement Optimisation API Endpoints

### 4.1 Strategies & Metadata
- `GET /api/v1/procurement/strategies`: Lists the 5 available mathematical optimization strategies (`LOWEST_LANDED_COST`, `BALANCED`, `FASTEST_DELIVERY`, `QUALITY_FIRST`, `BUDGET_CONSTRAINED`) with descriptions and weightings.

### 4.2 Mathematical Procurement Planning & Optimization
- `GET /api/v1/procurement/plans`: Lists all created procurement plans in the tenant, filterable by `job_id` and `status`.
- `POST /api/v1/procurement/plans`: Generates and solves a multi-material procurement plan using Google OR-Tools MILP.
  - **Payload:** `requirements` array (with `material_id`, `required_quantity`, `unit`, `max_lead_time_days`), `strategy`, optional `budget_limit`, `allow_split_purchasing`, `max_suppliers_per_material`, `min_quality_rating`, `max_overbuy_pct`.
  - **Returns:** Plan ID, plan number, solver status, total landed cost, budget utilization, excess units, allocations breakdown, baseline comparison benchmarks, and natural language explanation.
- `POST /api/v1/procurement/plans/from-job`: Automatically extracts raw material shortages from a production job's active BOM explosion and warehouse inventory netting, and optimizes a multi-material procurement plan in a single API call.
- `GET /api/v1/procurement/plans/{plan_id}`: Retrieves complete plan details including requirement items, supplier quota allocations, and comparative baseline savings.
- `POST /api/v1/procurement/plans/{plan_id}/reoptimize`: Re-executes mathematical optimization on an existing plan with updated strategy or constraint parameters.

### 4.3 Governance, Managerial Approval & ERP Integration
- `POST /api/v1/procurement/plans/{plan_id}/request-approval`: Submits an optimized plan for formal managerial authorization (`PENDING_APPROVAL`).
- `POST /api/v1/procurement/plans/{plan_id}/approve`: Approves the plan (`APPROVED`) by an authorized managerial role (Operations Director / Plant Head) and logs audit metadata (`approved_by`, `approved_at`).
- `POST /api/v1/procurement/plans/{plan_id}/reject`: Rejects the plan (`REJECTED`) with a required text audit rationale (`rejection_reason`).
- `POST /api/v1/procurement/plans/{plan_id}/generate-requisitions`: Automatically converts all awarded allocations in an approved plan into formal `PurchaseRequisition` records in the procurement ledger, sets plan status to `CONVERTED_TO_PO`, and locks the plan from modification.

---

## 5. Phase 7 Agentic Negotiation & Customer Quotation API Endpoints

### 5.1 Autonomous AI Supplier Negotiation Endpoints
- `GET /api/v1/negotiation/opportunities/{quotation_id}`: Evaluates a verified supplier quotation against internal and market benchmarks, computing target discount, benchmark price, and potential landed savings.
- `GET /api/v1/negotiation/sessions`: Lists active and historical negotiation sessions filterable by `status`.
- `POST /api/v1/negotiation/sessions`: Initiates a new autonomous negotiation session linked to a quotation or supplier, setting target price, strategy, and walk-away ceiling.
- `GET /api/v1/negotiation/sessions/{session_id}`: Retrieves complete session state, 16-state lifecycle position, commercial impact analysis, and chronological message dialogue thread.
- `POST /api/v1/negotiation/sessions/{session_id}/generate-message`: Generates an agentic counteroffer message in English, Hindi, or Hinglish based on the chosen commercial strategy (`VOLUME_COMMITMENT`, `BENCHMARK_PARITY`, `PAYMENT_ACCELERATION`, `LONG_TERM_CONTRACT`, `SPOT_CLEARANCE`). Sets message to `is_approved=False` and session to `AWAITING_APPROVAL`.
- `POST /api/v1/negotiation/messages/{message_id}/approve`: Human commercial gate. Approves a drafted counteroffer for transmission to the supplier, recording approver name and timestamp.
- `POST /api/v1/negotiation/sessions/{session_id}/simulate-response`: Simulates realistic vendor concession curve behavior (`CONCESSION`, `FIRM`, `COUNTER`, `REJECT`), tagging messages as `is_simulated=True` and deterministically recalculating all 9 landed cost components.
- `POST /api/v1/negotiation/sessions/{session_id}/analyze-response`: Parses unstructured inbound supplier replies (email/WhatsApp), extracts offered rates, classifies sentiment, and recalculates landed costs.
- `POST /api/v1/negotiation/sessions/{session_id}/finalize-agreement`: Formally concludes agreement, transitions state to `AGREEMENT_REACHED`, and generates an immutable child quotation revision (`version=2`) without mutating the original.
- `POST /api/v1/negotiation/start`: Backwards-compatible legacy endpoint to start a session and generate the initial counteroffer.
- `POST /api/v1/negotiation/send-and-simulate`: Backwards-compatible legacy endpoint to simulate concession and return immediate round savings.

### 5.2 Customer Quotation Engine & Margin Protection Endpoints
- `GET /api/v1/customer-quotes`: Lists customer quotations filterable by `status` and `is_loss_making`.
- `POST /api/v1/customer-quotes`: Formulates an audited commercial customer quote, enforces Gross Margin % vs Markup % distinction in Python `Decimal`, evaluates loss-making status, and renders an official ReportLab PDF.
- `POST /api/v1/customer-quotes/generate`: Backwards-compatible alias for quotation generation.
- `GET /api/v1/customer-quotes/{quote_id}`: Retrieves full customer quotation record, breakdown items, margin spread, and PDF availability.
- `POST /api/v1/customer-quotes/{quote_id}/recalculate`: Recalculates an existing customer quote with revised prices or margin targets, increments revision version (`version=version+1`), and renders an updated PDF.
- `POST /api/v1/customer-quotes/{quote_id}/request-approval`: Submits a quote to the commercial director review queue.
- `POST /api/v1/customer-quotes/{quote_id}/approve`: Approves a customer quote for dispatch to the client.
- `GET /api/v1/customer-quotes/{quote_id}/pdf` & `GET /api/v1/customer-quotes/{quote_id}/download-pdf`: Streams the official customer quotation PDF with safe `Rs.` currency formatting.
- `POST /api/v1/customer-quotes/{quote_id}/record-response`: Records client response (`ACCEPTED`, `REJECTED`, `COUNTER_PROPOSED`) with text audit notes.
- `GET /api/v1/customer-quotes/customers`: Lists all registered customer directory enterprises.
- `POST /api/v1/customer-quotes/customers`: Registers a new customer entity with contact details, GSTIN, and credit terms.

---

## 6. Phase 8 AI Copilot & Multi-Agent Orchestration Endpoints

### 6.1 Conversational Session Management
- `GET /api/v1/copilot/conversations`: Lists persistent conversational sessions filterable by `include_archived`.
- `POST /api/v1/copilot/conversations`: Creates a new conversational thread with initial greetings and parameter state.
- `GET /api/v1/copilot/conversations/{conversation_id}`: Retrieves complete conversation details and chronological message history.
- `PATCH /api/v1/copilot/conversations/{conversation_id}`: Updates session title or toggles archive state (`is_archived`).
- `DELETE /api/v1/copilot/conversations/{conversation_id}`: Permanently deletes a conversation and cascade deletes child messages and runs.

### 6.2 Message Posting & LangGraph Execution
- `POST /api/v1/copilot/conversations/{conversation_id}/messages`: Submits a user instruction in English, Hindi, or Hinglish. Automatically executes the LangGraph multi-agent supervisor graph, updates persistent context state, persists message and telemetry traces, and returns synthesized response with structured UI card.
- `POST /api/v1/copilot/chat`: Backwards-compatible execution endpoint that manages or resumes the active conversation.

### 6.3 Agent Run Telemetry & Activity Panel
- `GET /api/v1/copilot/runs/{run_id}`: Retrieves deep telemetry for an execution run, including selected agents, step status, tool calls, and duration (ms).
- `GET /api/v1/copilot/runs/{run_id}/events`: Returns chronological step-by-step event stream for the live Agent Activity Panel.

### 6.4 Human-in-the-Loop Governance & Action Checkpoints
- `GET /api/v1/copilot/actions`: Lists pending or historical agent actions filterable by `status` (`PENDING`, `APPROVED`, `REJECTED`) and `conversation_id`.
- `POST /api/v1/copilot/actions/{action_id}/approve`: Authorizes a paused commercial action (e.g. customer quote dispatch, inventory adjustment) and resumes the paused agent run.
- `POST /api/v1/copilot/actions/{action_id}/reject`: Declines a paused commercial action with mandatory executive audit rationale.




