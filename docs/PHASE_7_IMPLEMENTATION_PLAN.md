# IndusPilot — Phase 7 Implementation Plan
## Agentic Supplier Negotiation, Commercial Decision-Making & Customer Quotation Generation

**Theme:** Industrial Manufacturing  
**Problem Statement:** 4.1 — Raw Material Procurement and Manufacturing Quotation Optimisation  
**Target Repository:** CodeBloodMe/IndusPilot  

---

## 1. Existing Architecture Audit

### 1.1 Existing Negotiation Architecture
- **Database Models (`backend/app/models/entities.py`):**
  - `NegotiationSession`: Stores `organization_id`, `supplier_id`, `quotation_id`, `material_name`, `quantity`, `original_unit_price`, `target_unit_price`, `current_offered_price`, `status`, `simulation_mode`.
  - `NegotiationMessage`: Stores `session_id`, `round_number`, `sender_type` (`BUYER_AGENT`, `SUPPLIER`, `HUMAN_OPERATOR`), `message_text`, `proposed_unit_price`, `is_simulated`.
  - `ApprovalRequest`: Stores `request_type` (`NEGOTIATION_DISPATCH`), `status` (`PENDING`, `APPROVED`, `REJECTED`).
- **Services (`backend/app/services/negotiation_service.py`):**
  - `NegotiationStateMachine`: Basic transition map (`DRAFT` $\rightarrow$ `READY_FOR_APPROVAL` $\rightarrow$ `APPROVED_TO_SEND` $\rightarrow$ `SENT` $\rightarrow$ `RESPONSE_RECEIVED` $\rightarrow$ `COUNTEROFFER_PROPOSED` / `ACCEPTANCE_PROPOSED` $\rightarrow$ `CLOSED`).
  - `generate_counteroffer_draft`: Creates single-template counteroffer email draft citing volume and price gaps.
  - `simulate_supplier_response`: Simple 2-round synthetic concession split.
- **API Endpoints (`backend/app/api/v1/negotiation.py`):**
  - `GET /sessions`: Lists negotiation sessions and messages.
  - `POST /start`: Initiates session and creates draft with pending approval request.
  - `POST /send-and-simulate`: Simulates vendor response and increments round.
- **Frontend (`NegotiationView.tsx`):**
  - Displays sessions, chat bubble thread, status banner, and simulate button.

### 1.2 Existing Supplier Communication Functionality
- Currently uses synthetic simulation mode exclusively.
- Missing: Provider abstraction for optional real SMTP/Email dispatch with human approval gate and audit receipts.
- Missing: Multi-language message generation (English, Hindi, Hinglish).
- Missing: Multiple negotiation strategies (Price-focused, Volume-based, Competitive-offer, Delivery-focused, Balanced).

### 1.3 Procurement Integration
- Phase 6 introduced `ProcurementPlan`, `ProcurementPlanItem`, and `ProcurementPlanAllocation` solved by Google OR-Tools.
- Current gap: When a supplier accepts a negotiated counteroffer (e.g. ₹185 $\rightarrow$ ₹178/kg), the system needs to:
  1. Record a revised quotation record (without overwriting the original historical quotation).
  2. Deterministically recalculate unit landed cost via Phase 4 landed cost engine.
  3. Re-run procurement optimization or evaluate plan impact without overwriting historical plans.
  4. Display net negotiated savings delta.

### 1.4 Costing Integration
- Phase 5 introduced the 14-Factor deterministic costing engine (`calculate_manufacturing_cost`) and `ProductionCostEstimate`.
- Cost inputs include bill of materials, machine run rates, labor rates, scrap allowances, and overheads.
- Current gap: Linking customer quotation generation directly to saved cost estimates, calculating gross margins (distinguishing margin from markup), detecting loss-making orders, and enforcing minimum gross margin protection.

### 1.5 Customer Quotation Workflow
- Models: `CustomerQuotation` with customer info, product reference, quantity, unit production cost, unit selling price, subtotal, tax amount, total amount, margin %, payment terms, delivery weeks.
- Services: `generate_customer_quotation_pdf` using ReportLab.
- API: `GET /customer-quotes`, `POST /customer-quotes/generate`, `GET /customer-quotes/{id}/pdf`.
- Current gap:
  - Quotation state machine lacks full lifecycle (`DRAFT`, `NEEDS_REVIEW`, `READY_FOR_APPROVAL`, `APPROVED`, `SENT`, `ACCEPTED`, `REJECTED`, `EXPIRED`, `CANCELLED`).
  - Lacks multi-item product quotation line items and revision versioning.
  - No customer master entity; customer details are flat fields on the quote.

---

## 2. Critical Regression Audit & Remediation Plan (Part 2)

### Identified Bug
In `backend/app/services/procurement_baseline.py`:
When the OR-Tools solver returns `status = "INFEASIBLE"`, `total_landed_cost` is `0.0`.
The baseline computation calculates:
$$\text{savings\_abs} = \text{BaselineCost} - \text{opt\_cost} = \text{BaselineCost} - 0.0 = \text{BaselineCost}$$
$$\text{savings\_pct} = 100.0\%$$
And Baseline C was labelled `"Mathematically Optimal"` regardless of solver status!

### Strict Remediation Rules
1. If `opt_status == "INFEASIBLE"`:
   - `savings_vs_baseline_abs = 0.0`
   - `savings_vs_baseline_pct = 0.0`
   - Baseline C `is_feasible = False`
   - Baseline C `status_label = "Infeasible (No Feasible Solution Found)"`
   - `allocations = []`
2. If `b_a_cost < opt_cost` (negative savings in Quality/Delivery strategies):
   - Explicitly preserve negative savings ($-\Delta$ INR and $-\%$), never clamp silently to positive savings.
3. If a baseline is infeasible (`is_feasible = False`):
   - Savings against that baseline must be `0.0` and marked non-comparable.
4. Timed-out solutions:
   - Must be flagged `TIMED_OUT` / `FEASIBLE` if partial, never `OPTIMAL`.

---

## 3. Detailed Architecture for Phase 7

### 3.1 Specialized Negotiation Agent Architecture
- **Inputs**: Supplier master, original quote item, material specs, volume, quoted landed cost, genuine alternative quotes, target price, ceiling price, delivery deadline, payment terms, selected strategy.
- **Strategies**:
  - `PRICE_FOCUSED`: Unit rate concession without altering scope.
  - `VOLUME_BASED`: Aggregated purchasing volume leverage.
  - `COMPETITIVE_OFFER`: Cites genuine alternative quotation rates (no hallucinations).
  - `DELIVERY_FOCUSED`: Expedited delivery schedule trade-off.
  - `BALANCED_COMMERCIAL`: Simultaneous trade-off between price, payment terms, and freight.
- **Multilingual Communication**: Templates and generator supporting English, Hindi, and Hinglish.
- **State Machine**:
  `DRAFT` $\rightarrow$ `ANALYSING` $\rightarrow$ `PROPOSAL_GENERATED` $\rightarrow$ `AWAITING_APPROVAL` $\rightarrow$ `APPROVED_TO_SEND` $\rightarrow$ `SENT` $\rightarrow$ `RESPONSE_RECEIVED` $\rightarrow$ `RESPONSE_ANALYSED` $\rightarrow$ `COUNTEROFFER_GENERATED` $\rightarrow$ `AWAITING_COUNTEROFFER_APPROVAL` $\rightarrow$ `COUNTEROFFER_SENT` $\rightarrow$ `ACCEPTANCE_PROPOSED` / `REJECTION_PROPOSED` $\rightarrow$ `COMPLETED` / `CANCELLED` / `FAILED`.

### 3.2 Supplier Response Analysis Engine
- Analyzes incoming text / simulated response:
  - Extracts revised unit price, revised MOQ, revised freight, revised lead time, payment terms.
  - Recomputes exact landed cost deterministically via `calculate_landed_cost`.
  - Classifies: `ACCEPTED_TARGET`, `ACCEPTABLE_COUNTEROFFER`, `COUNTEROFFER_REQUIRES_REVIEW`, `REJECTED_TARGET`, `INCOMPLETE_RESPONSE`, `NEEDS_HUMAN_REVIEW`.
  - Computes net landed savings delta vs original quotation.

### 3.3 Communication Modes
- **Simulated Mode**: Reproducible synthetic generator simulating supplier acceptance, concessions, rejection, or volume conditions with clear UI disclaimer badge: `SIMULATED SUPPLIER RESPONSE — NOT A REAL COMMUNICATION`.
- **Real Mode**: Provider abstraction (`EmailProvider` / SMTP) with credentials check, pre-send confirmation modal, and explicit user approval gate.

### 3.4 Customer Quotation & Pricing Engine
- **Customer Directory**: Customer entity supporting name, company, email, phone, GSTIN, address.
- **Cost Estimate Integration**: Pulls unit production cost from Phase 5 14-factor estimate.
- **Margin Protection & Loss Detection**:
  - Gross Margin: $\text{Margin \%} = \frac{\text{Selling Price} - \text{Unit Cost}}{\text{Selling Price}} \times 100$.
  - Markup: $\text{Markup \%} = \frac{\text{Selling Price} - \text{Unit Cost}}{\text{Unit Cost}} \times 100$.
  - Classifies order profitability: `PROFITABLE`, `LOW_MARGIN` ($< 15\%$), `BREAK_EVEN` ($0\%$), `LOSS_MAKING` ($< 0\%$).
- **ReportLab PDF Generator**:
  - Industrial invoice layout with manufacturer header, customer details, scope of supply, tax breakdown, payment conditions, validity, and authorization block.
- **Quotation Lifecycle**:
  `DRAFT` $\rightarrow$ `NEEDS_REVIEW` $\rightarrow$ `READY_FOR_APPROVAL` $\rightarrow$ `APPROVED` $\rightarrow$ `SENT` $\rightarrow$ `ACCEPTED` / `REJECTED` / `EXPIRED`.

---

## 4. Security & Compliance Guardrails
1. **Never commit without human authorization**: AI agents generate proposals, humans click "Approve".
2. **Never exceed authorized limits**: Cannot submit counteroffers above user-defined maximum acceptable price.
3. **No financial hallucinations**: All financial deltas, landed costs, and margins computed with Python `Decimal` (`ROUND_HALF_UP`).
4. **Idempotency**: Prevent duplicate outbound messages or double PO allocations.
5. **Multi-tenant scoping**: Organization ID header enforced across all queries.

---

## 5. Testing & Verification Strategy
1. **Regression Suite (`test_optimization_regression.py`)**: 10 tests verifying infeasible solvers never claim optimal status or savings.
2. **Phase 7 Test Suite (`test_phase7_negotiation_and_customer_quotes.py`)**:
   - Negotiation session lifecycle & round transitions.
   - 5 negotiation strategies & counteroffer generation.
   - Deterministic landed cost recalculation on revised offers.
   - Multi-language communication templates.
   - Simulation mode labeling and reproducible responses.
   - Customer quotation creation, margin protection, loss-making detection.
   - Professional ReportLab PDF generation.
   - Integration: negotiated quote $\rightarrow$ revised procurement plan $\rightarrow$ cost estimate $\rightarrow$ customer quotation.
3. **Full Suite Execution**: All 76 existing + new regression + Phase 7 tests.
4. **Frontend Production Build**: `npm --prefix frontend run build` clean compilation.

