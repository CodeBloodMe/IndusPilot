# IndusPilot Phase 5 Implementation Plan
## BOM Management, Inventory Intelligence & Manufacturing Cost Optimisation

---

## 1. Executive Summary & Audit Findings

Following a complete audit of the IndusPilot codebase, this document sets forth the architectural blueprint and execution plan for Phase 5: **Manufacturing Intelligence Engine**.

### 1.1 Existing Architecture Audit

| Module / Component | Existing State | Gaps Identified | Required Phase 5 Enhancement |
|---|---|---|---|
| **Products Catalogue** | Minimal `Product` table (`id`, `code`, `name`, `category`, `description`). Only `GET /products` exists. | Missing process parameters, base unit, batch size, duration, active status. No CRUD APIs. | Extend `Product` model; add `POST /products`, `GET /products/{id}`, `PATCH /products/{id}`. |
| **BOM Management** | Basic `BillOfMaterials` and `BOMItem` tables. `GET /products`, `GET /{product_id}`, `POST /explode` in `bom.py`. | No BOM versioning/revisions, no duplication, no validation engine, no yield-based calculation option. | Add BOM lifecycle (`DRAFT`, `ACTIVE`, `ARCHIVED`), revisioning preserving history, additive vs yield scrap, circular reference detection. |
| **Material Requirement Engine** | `bom_engine.py` computes additive scrap `gross = net * (1 + scrap%)`. | Only additive scrap supported. No multi-product aggregation, no unit conversion service. | Add yield-based formula `gross = net / yield`, multi-product requirement aggregator, safe `unit_conversion.py` in Decimal. |
| **Inventory System** | Simple `Inventory` table (`current`, `reserved`, `incoming`, `safety`, `reorder`). `InventoryMovement` has minimal fields. | No transactional ledger. Stock can be edited arbitrarily. No atomic receive/issue/reserve/release/adjust workflows. | Implement atomic `inventory_ledger.py` service, strict idempotency, negative stock prevention, reservation tracking, alert engine. |
| **Production Planning / MRP** | None. Only `POST /bom/explode` for ad-hoc netting. | No production orders, no job tracking, no shortage reports, no formal handoff to procurement. | Create `ProductionJob` lifecycle (`DRAFT` to `COMPLETED`), MRP material checks, and one-click `PurchaseRequisition` handoffs. |
| **Costing Engine** | `cost_engine.py` has 14-factor arithmetic in Decimal, but is ephemeral/stateless. | No persistence of estimates, no assumption audit snapshots, fixed overhead allocation method only, no what-if baseline vs scenario comparison. | Refactor costing engine with configurable overhead methods (`PERCENTAGE_PRIME`, `PERCENTAGE_LABOR`, `MACHINE_HOURS`, `FIXED_BATCH`), assumption data quality scoring (`COMPLETE`, `ESTIMATED`, `NEEDS_INPUT`), what-if simulation, and persistent DB entities. |
| **Frontend Views** | `BOMManagerView.tsx`, `InventoryView.tsx`, `CostingEngineView.tsx` are functional but partially decoupled from backend CRUD. | `CostingEngineView` uses hardcoded transport/packaging and client-side scrap. `InventoryView` has no action buttons. `BOMManagerView` cannot create/edit BOMs. | Modernize all 3 views to be fully interactive and wired to new backend APIs. |

---

## 2. Mathematical Formulations & Calculation Specifications

### 2.1 Material Requirement Formulations
For each BOM component \(i\) of finished product quantity \(Q\):

1. **Additive Scrap Allowance:**
   $$\text{Gross Qty}_i = (Q \times \text{Net Qty per Unit}_i) \times \left(1 + \dfrac{\text{Scrap Pct}_i}{100}\right)$$
   $$\text{Scrap Qty}_i = \text{Gross Qty}_i - (Q \times \text{Net Qty per Unit}_i)$$

2. **Yield-Based Allowance:**
   $$\text{Gross Qty}_i = \dfrac{Q \times \text{Net Qty per Unit}_i}{\text{Yield Rate}_i} \quad \left(\text{where } \text{Yield Rate}_i = \dfrac{\text{Yield Pct}_i}{100}\right)$$
   $$\text{Scrap Qty}_i = \text{Gross Qty}_i - (Q \times \text{Net Qty per Unit}_i)$$

*Rule: Each component uses exactly one configured method; never both simultaneously.*

### 2.2 Inventory Netting & Availability
For component material \(M\):
$$\text{Available Stock} = \max(0, \text{Physical On-Hand} - \text{Reserved Stock})$$
$$\text{Effective Stock} = \text{Available Stock} + \text{Confirmed Incoming Stock}$$
$$\text{Net Shortage} = \max(0, \text{Gross Requirement} + \text{Safety Stock} - \text{Effective Stock})$$
$$\text{Purchasing Requirement} = \max(0, \text{Net Shortage})$$

*Rule: Confirmed incoming stock includes only approved/confirmed POs, excluding draft requisitions.*

### 2.3 14-Factor Manufacturing Cost Engine

1. **Raw Material Cost (\(C_{\text{mat}}\)):**
   $$C_{\text{mat}} = \sum_{i} (\text{Gross Qty}_i \times P_{\text{unit}, i}) - \text{Recoverable Scrap Value}$$
2. **Direct Labour Cost (\(C_{\text{lab}}\)):**
   $$C_{\text{lab}} = N_{\text{workers}} \times H_{\text{labour}} \times R_{\text{labour}}$$
3. **Machine Operating Cost (\(C_{\text{mach}}\)):**
   $$C_{\text{mach}} = (H_{\text{operating}} \times R_{\text{operating}}) + (H_{\text{setup}} \times R_{\text{setup}})$$
4. **Electricity Cost (\(C_{\text{elec}}\)):**
   $$\text{Consumption (kWh)} = P_{\text{machine}} (\text{kW}) \times H_{\text{operating}}$$
   $$C_{\text{elec}} = \text{Consumption} \times \text{Tariff}_{\text{kWh}}$$
5. **Secondary Processes (\(C_{\text{proc}}\)):** Coating, plating, heat treatment.
6. **Transportation & Logistics (\(C_{\text{trans}}\)):** Inbound/outbound freight.
7. **Packaging & Crating (\(C_{\text{pack}}\)):** Direct packaging expenses.
8. **Direct Prime Cost (\(C_{\text{prime}}\)):**
   $$C_{\text{prime}} = C_{\text{mat}} + C_{\text{lab}} + C_{\text{mach}} + C_{\text{elec}} + C_{\text{proc}} + C_{\text{trans}} + C_{\text{pack}}$$
9. **Manufacturing Overhead (\(C_{\text{ovh}}\)):** Configurable allocation:
   - Percentage of Prime Cost: \(C_{\text{ovh}} = C_{\text{prime}} \times (r_{\text{ovh}} / 100)\)
   - Percentage of Direct Labour: \(C_{\text{ovh}} = C_{\text{lab}} \times (r_{\text{ovh}} / 100)\)
   - Machine Hours Rate: \(C_{\text{ovh}} = H_{\text{mach}} \times R_{\text{ovh\_hr}}\)
   - Fixed per Batch: \(C_{\text{ovh}} = F_{\text{batch}}\)
10. **Other Production Expenses (\(C_{\text{other}}\)):** Tooling, consumables, inspection fees.
11. **Total Batch Manufacturing Cost (\(C_{\text{total}}\)):**
    $$C_{\text{total}} = C_{\text{prime}} + C_{\text{ovh}} + C_{\text{other}}$$
12. **Unit Cost / Break-Even Price (\(P_{\text{breakeven}}\)):**
    $$P_{\text{breakeven}} = \dfrac{C_{\text{total}}}{Q}$$
13. **Suggested Selling Price (\(P_{\text{sell}}\)) based on Target Gross Margin (\(m\)):**
    $$P_{\text{sell}} = \dfrac{P_{\text{breakeven}}}{1 - \frac{m}{100}}$$
14. **Commercial Profitability Metrics:**
    $$\text{Gross Profit} = (P_{\text{sell}} \times Q) - C_{\text{total}}$$
    $$\text{Gross Margin \%} = \dfrac{P_{\text{sell}} - P_{\text{breakeven}}}{P_{\text{sell}}} \times 100$$
    $$\text{Markup \%} = \dfrac{P_{\text{sell}} - P_{\text{breakeven}}}{P_{\text{breakeven}}} \times 100$$

---

## 3. Implementation Steps

1. **Service: Unit Conversion Engine (`backend/app/services/unit_conversion.py`)**
   - Safe conversions for Mass, Length, Area, Volume, Count using Decimal arithmetic.
   - Guard against invalid cross-dimensional conversions (e.g. mass to area without density).
2. **Database Models & Alembic Migration (`c19d45e7832b_0004_manufacturing_intelligence.py`)**
   - Extend `products`, `bills_of_materials`, `bom_items`, `inventory`.
   - Add `production_jobs`, `production_job_materials`, `cost_estimates`, `cost_estimate_items`, `costing_scenarios`.
3. **Service: BOM & Material Requirement Aggregator (`backend/app/services/bom_service.py`)**
   - Versioning, revisions, duplicate component validation, additive vs yield scrap, requirement aggregation across multiple jobs/BOMs.
4. **Service: Inventory Ledger Service (`backend/app/services/inventory_service.py`)**
   - Transactional stock receipts, issues, reservations, releases, adjustments, and alerts.
5. **Service: Manufacturing Cost & What-If Simulation Engine (`backend/app/services/costing_service.py`)**
   - 14-factor Decimal calculation, configurable overhead methods, assumption data quality tagging (`COMPLETE`, `ESTIMATED`, `NEEDS_INPUT`), and scenario diffs.
6. **API Endpoints (`backend/app/api/v1/`)**
   - `products.py` and `bom.py`: Product & BOM management.
   - `inventory.py`: Ledger transactions, movements, availability check.
   - `production.py`: Production jobs, material checks, procurement handoff.
   - `costing.py`: Cost estimates, what-if simulations, scenario saving.
7. **Frontend Views Update**
   - `BOMManagerView.tsx`: Product selector, BOM revision manager, explosion preview, validation.
   - `InventoryView.tsx`: Ledger table, action modals (Receive, Issue, Adjust, Reserve), alerts.
   - `CostingEngineView.tsx`: 14-factor inputs, supplier quote auto-population, what-if side-by-side simulator.
   - `frontend/src/lib/api.ts`: Add all new API methods.
8. **Demonstration Dataset Remediation**
   - Seed product: "Stainless Steel Industrial Bracket" (500 units) with 4 BOM components and verified pricing.
9. **Testing & Verification**
   - `backend/tests/test_phase5_manufacturing_intelligence.py` with 25+ comprehensive tests.
   - Build verification with `npm --prefix frontend run build`.

