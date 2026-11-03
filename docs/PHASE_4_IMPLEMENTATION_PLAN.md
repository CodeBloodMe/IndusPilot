# Phase 4 Implementation Plan: Intelligent Supplier Comparison & Procurement Decision Engine

## 1. Existing Comparison Architecture Audit
- **Current State**: `backend/app/api/v1/compare.py` provides an `/api/v1/compare/evaluate` route that evaluates a list of quotations or all `VERIFIED` quotations for an organization.
- **Current Flow**:
  - Iterates through quotations, extracts `items[0]`.
  - Calculates landed cost via `calculate_landed_cost()`.
  - Computes a 5-factor score via `evaluate_supplier_quotation()`.
  - Sorts candidates descending by composite score.
- **Architectural Gaps Identified**:
  1. **No Eligibility Gate**: Quotes with incompatible grades (e.g., SS316 vs SS304), wrong thicknesses (e.g., 5mm vs 2mm), insufficient capacity, or expired validity are evaluated and can inadvertently be recommended solely due to low face value.
  2. **Single-Item Blindness**: Assumes each quotation has a single item (`items[0]`) rather than locating the specific line item matching the requested material and allocating freight across multi-item bills.
  3. **Missing Data Imputation**: Silently imputes neutral baseline values (e.g. 70.0 for quality, 75.0 for reliability) when vendor history is absent, rather than calculating evidence completeness and renormalizing available weights transparently.
  4. **No Persistence / Audit Trail**: Comparisons are purely ephemeral and not saved to the database. Past purchasing decisions cannot be reproduced if quotations change.
  5. **Missing Procurement Requisition Handoff**: No API to turn the chosen comparison candidate into a formal purchase requisition.
  6. **No Price History / Trend Analytics**: No dedicated endpoint for historical price movements and vendor pricing fluctuations.

---

## 2. Existing Scoring Implementation & Gaps
- **Existing Weights**:
  - Landed price competitiveness: 35%
  - Material quality: 25%
  - Delivery reliability: 15%
  - Delivery lead time: 15%
  - Payment terms flexibility: 10%
- **Issues with Current Scoring**:
  - Normalization is linear relative to the lowest price without bounding steep outliers.
  - Lead time penalization is static (-7 pts/day past best) without factoring the buyer's explicit required delivery deadline.
  - Imputation masks the absence of real vendor track records.
- **Phase 4 Upgrade**:
  - Transparent missing-data policy: dynamically renormalize active weights when metrics are missing (`is_imputed = False`).
  - Compute a `data_completeness_pct` (e.g., 80% if 4 of 5 factors have verified evidence).
  - Explicit threshold: Flag "Low Evidence Recommendation" if completeness < 60%.
  - Include full factor breakdown with original values, normalized scores, and mathematical justification.

---

## 3. Data Required for Comparison
| Data Field | Source | Required For |
|---|---|---|
| Material Code, Grade, Thickness, Form | Requirement input & Material catalog | Specification Compatibility |
| Required Quantity & Unit | Requirement input | Quantity Eligibility & Landed Cost |
| Required Delivery Deadline | Requirement input | Delivery Feasibility & Lead Time Scoring |
| Quoted Unit Price & Currency | Quotation line item | Base Financials |
| Tax Rate & Tax Inclusivity Status | Quotation header & line item | GST Base & Tax Calculations |
| Freight & Ancillary Charges | Quotation header & line item | Landed Cost Allocation |
| Payment Terms Days | Supplier profile & quote terms | Payment Flexibility Scoring |
| Historical Quality Rating & Rejections | Supplier profile & inspection ledger | Quality Scoring |
| Historical On-Time Delivery Rate | Supplier profile & delivery logs | Reliability Scoring |
| Quotation Validity Date | Quotation header | Commercial Eligibility Check |
| Document Quarantine Status | UploadedDocument & Quality Gate | Quarantine Exclusion |

---

## 4. Financial Calculation Requirements (Deterministic Decimal)
1. **Gross Material Cost**: $\text{Gross} = \text{Unit Price} \times \text{Quantity}$
2. **Discount Amount**: $\text{Discount} = \text{Gross} \times (\text{Discount \%} / 100)$
3. **Taxable Base**:
   - If `TAX_EXCLUDED`: $\text{Base} = \text{Gross} - \text{Discount}$
   - If `TAX_INCLUDED`: $\text{Base} = (\text{Gross} - \text{Discount}) / (1 + \text{Tax Rate} / 100)$
   - If `NO_TAX`: $\text{Base} = \text{Gross} - \text{Discount}$
   - If `UNKNOWN`: Block calculation, mark quotation as `NEEDS_REVIEW`.
4. **GST Amount**:
   - If `TAX_EXCLUDED`: $\text{Tax} = \text{Base} \times (\text{Tax Rate} / 100)$
   - If `TAX_INCLUDED`: $\text{Tax} = (\text{Gross} - \text{Discount}) - \text{Base}$
   - If `NO_TAX`: $\text{Tax} = 0$
5. **Freight Allocation (Multi-Item Quotes)**:
   - Pro-rata by item value: $\text{Allocated Freight}_i = \text{Total Freight} \times (\text{Base}_i / \sum \text{Base}_k)$
   - Packaging and insurance handled similarly.
6. **Total Landed Cost**:
   $$\text{Total Landed} = \text{Base} + \text{Tax} + \text{Allocated Freight} + \text{Allocated Ancillary}$$
7. **Effective Landed Cost Per Unit**:
   $$\text{Unit Landed} = \text{Total Landed} / \text{Target Quantity}$$

---

## 5. Supplier Eligibility Engine Design
- **Statuses**: `ELIGIBLE`, `CONDITIONALLY_ELIGIBLE`, `INELIGIBLE`, `NEEDS_REVIEW`.
- **Rules**:
  1. *Material Grade*: Exact match or permitted alias (e.g. AISI 304 matches SS304). Grade mismatch (e.g. SS316 for SS304) $\rightarrow$ `INELIGIBLE`.
  2. *Thickness / Dimensions*: Tolerance $\pm 0.1\text{ mm}$ for thickness. Beyond tolerance $\rightarrow$ `INELIGIBLE` or `CONDITIONALLY_ELIGIBLE`.
  3. *Quantity & Capacity*: Quoted qty + supplier capacity must be $\ge$ requested quantity unless split purchasing is permitted.
  4. *MOQ*: If supplier MOQ exceeds required quantity by $> 2\times$, flag as `CONDITIONALLY_ELIGIBLE` with warning.
  5. *Delivery Deadline*: Quoted delivery date or lead time must arrive on or before the deadline. Late arrival $\rightarrow$ `INELIGIBLE` (reason: "Cannot meet required production deadline").
  6. *Commercial Validity*: Quotations where `valid_until < today` $\rightarrow$ `INELIGIBLE` (reason: "Quotation validity expired").
  7. *Quarantine*: Any document or quotation flagged by the Quality Gate is strictly excluded from scoring and marked `INELIGIBLE` / `NEEDS_REVIEW`.

---

## 6. Proposed Implementation Steps
1. **Remediate Demonstration Data & Vendor Names**:
   - Replace any real corporate names (Tata, Jindal, Kalyani) with fictional identities (`Titan Alloy & Plate`, `Janata Inox Direct`, `Konkan Special Steels`).
   - Add explicit synthetic disclaimers to all mock quotations.
   - Expand dataset to 10+ synthetic files (PDFs, Excel, CSV, Images) including multi-item, incomplete, and ambiguous quotes.
2. **Build OCR Engine with Graceful Fallback**:
   - Integrate `pytesseract` with environment detection and clear limitation reporting.
   - Implement deterministic metadata/text zone fallback parser.
3. **Build Core Calculation & Scoring Services**:
   - `backend/app/calculations/landed_cost.py`: Support multi-item freight allocation, tax modes (`TAX_INCLUDED`, `TAX_EXCLUDED`, `NO_TAX`, `UNKNOWN`), Decimal precision.
   - `backend/app/services/eligibility_engine.py`: Material, quantity, lead time, commercial eligibility checks.
   - `backend/app/calculations/scoring.py`: Explainable 5-factor scoring with weight renormalization, evidence completeness tracking, and natural language rationale.
4. **Database Models & Alembic Migration**:
   - Add `SupplierComparisonRequest`, `SupplierComparisonResult`, `SupplierComparisonCandidate` models.
   - Ensure `PurchaseRequisition` integration.
   - Create and apply Alembic migration `0003_supplier_comparison_and_requisitions`.
5. **API Endpoints**:
   - `POST /api/v1/comparisons/analyze`: Comprehensive multi-supplier comparison.
   - `POST /api/v1/comparisons/eligibility`: Evaluate vendor eligibility for a requirement.
   - `POST /api/v1/comparisons/landed-cost`: Standalone landed cost computation.
   - `GET /api/v1/comparisons/{comparison_id}`: Retrieve saved comparison record.
   - `GET /api/v1/materials/{material_id}/price-history`: Historical quotation trend.
   - `GET /api/v1/suppliers/{supplier_id}/performance`: Vendor scorecard & audit logs.
   - `POST /api/v1/procurement/requisitions`: Create purchase requisition from chosen comparison.
   - `GET /api/v1/procurement/requisitions`: List requisitions.
6. **Frontend Enhancements (`SupplierCompareView.tsx`)**:
   - Step 1: Purchasing requirement inputs.
   - Step 2: Quotation retrieval and eligibility filtering.
   - Step 3: Detailed comparison table with landed cost breakdowns.
   - Step 4: Decision highlights (Best Overall, Cheapest, Fastest, Highest Quality).
   - Step 5: Supplier inspection drawer/modal with formula details.
   - Step 6: Procurement handoff button ("Create Procurement Requisition").
   - Price history chart using Recharts.
7. **Comprehensive Automated Test Suite**:
   - `backend/tests/test_phase4_supplier_comparison.py`: 20+ tests covering all eligibility, landed cost, scoring, API, and multi-tenant security requirements.

---

## 7. Testing Strategy
- Unit tests for tax inclusivity, exclusivity, zero-tax, freight allocation, unit conversion, and Decimal rounding.
- Matrix tests for eligibility rules (material grade, thickness, lead time, MOQ, expired validity, quarantine).
- Scoring verification for weight renormalization and missing data handling.
- Full end-to-end API integration tests.
- Frontend production build verification (`npm run build`).

