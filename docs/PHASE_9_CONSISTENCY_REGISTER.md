# INDUSPILOT — PHASE 9 CROSS-MODULE CONSISTENCY REGISTER
**Tech4Bharat 2026 — Industrial Manufacturing (Problem Statement 4.1)**  
**Author:** Lead Engineering Team (`CodeBloodMe`)  
**Date:** March 2026  
**Status:** Canonical Reference Standard  

---

## 1. Purpose of the Consistency Register

As a complex, multi-module platform spanning quotation extraction, supplier ranking, inventory netting, linear optimization, agentic negotiation, manufacturing costing, and multi-agent copilot orchestration, **IndusPilot** enforces absolute mathematical and architectural consistency across all subsystems.

This register serves as the authoritative source of truth for all cross-module parameters, scoring weights, inventory formulas, and SKU mappings.

---

## 2. Section 4.1: Canonical 5-Factor Supplier Scoring Model

### 2.1 Authoritative Weight Distribution
The platform strictly mandates the following 5-factor model across all services (`app/calculations/scoring.py`), agent supervisors (`app/agents/langgraph_supervisor.py`), frontend scorecards (`SupplierCompareView.tsx`), and documentation:

| Factor Code | Factor Name | Canonical Weight | Primary Data Source | Mathematical Formula / Curve |
|---|---|---|---|---|
| `cost_competitiveness` | Landed Cost Competitiveness | **35%** (0.35) | Effective landed cost per unit | Bounded Hyper-Curve: $\min(100, \max(10, \frac{\text{Min Landed Cost in Pool}}{\text{Supplier Landed Cost}} \times 100))$ |
| `quality` | Material Quality & Certifications | **25%** (0.25) | Empirical audit rating & test certs | Linear Rating: $(\text{Rating} / 5.0) \times 100$ (with ISO/NABL certification boosts) |
| `delivery_reliability` | Historical Delivery Reliability | **15%** (0.15) | On-time delivery records & reject rate | Base reliability score penalized by material rejection rate % |
| `delivery_time` | Lead Time Compliance | **15%** (0.15) | Declared lead time vs deadline | Exponential decay relative to required project delivery window |
| `payment_flexibility` | Payment Terms Flexibility | **10%** (0.10) | Credit days (e.g. 60d vs 30d vs Advance) | Credit Term Curve: 60+ days = 100pts; 30-45 days = 80pts; Advance/PDC = 40pts |
| **TOTAL** | **Composite Supplier Score** | **100%** (1.00) | Weighted linear combination | **Sum of all 5 weighted factors** |

### 2.2 Missing Data Policy & Dynamic Renormalization
When vendor empirical data is incomplete (e.g. unrated new supplier, unquoted payment terms):
1. **Dynamic Weight Renormalization:** The engine recalculates weights over active, verified factors:
   $$w'_i = \frac{w_i}{\sum_{k \in \text{Available}} w_k}$$
2. **Data Completeness Index:** Tracks the percentage of verified factors available:
   $$\text{Evidence Completeness Index} = \frac{|\text{Verified Factors}|}{5} \times 100\%$$
3. **Explicit Labeling:** Any missing factor is explicitly tagged with `[ESTIMATED]` or `[DATA UNAVAILABLE]` in the UI scorecard.

---

## 3. Section 4.2: Inventory Netting Arithmetic Standard

### 3.1 Mathematical Definitions
To eliminate confusion between simple inventory subtraction and Material Requirements Planning (MRP) replenishment netting, IndusPilot defines:

$$\text{Gross Requirement} = \text{Batch Quantity} \times \text{BOM Quantity per Unit} \times (1 + \text{Scrap Allowance})$$

$$\text{Available Stock} = \max(0, \text{Physical On-Hand Stock} - \text{Reserved Stock})$$

$$\text{Effective Stock} = \text{Available Stock} + \text{Incoming Purchase Orders}$$

$$\text{Unbuffered Shortage} = \max(0, \text{Gross Requirement} - \text{Effective Stock})$$

$$\text{Net MRP Shortage} = \max(0, \text{Gross Requirement} + \text{Safety Stock Buffer} - \text{Effective Stock})$$

### 3.2 Canonical 500-Bracket Production Batch Verification
For the master hackathon order of 500 units of Stainless Steel Brackets:
- Component: `MAT-SS-304` (Grade SS304 Sheet Plate, 2.0 kg per unit, 5% scrap allowance).
- **Gross Required:** $500 \times 2.0 \times 1.05 = \mathbf{1,050.0\text{ kg}}$.
- **Physical On-Hand Stock:** $400.0\text{ kg}$.
- **Reserved Stock (Job Allocations):** $50.0\text{ kg}$.
- **Available Warehouse Stock:** $400.0 - 50.0 = \mathbf{350.0\text{ kg}}$.
- **Incoming Scheduled Orders:** $0.0\text{ kg}$.
- **Safety Stock Buffer Requirement:** $\mathbf{50.0\text{ kg}}$.
- **Unbuffered Raw Difference:** $1,050.0 - 350.0 = \mathbf{700.0\text{ kg}}$.
- **Net MRP Procurement Shortage:** $1,050.0 + 50.0 - 350.0 = \mathbf{750.0\text{ kg}}$.

Both values are returned by the netting service (`unbuffered_shortage: 700.0`, `net_shortage: 750.0`) and displayed with clear labels in frontend inventory views and copilot cards.

---

## 4. Section 4.3: Product SKU Code Consistency & Alias Resolution Map

### 4.1 Canonical SKU Hierarchy
- **Canonical Product Code:** `IND-BRK-SS304`
- **Canonical Product Name:** Stainless Steel Industrial Mounting Bracket
- **Canonical Unit of Measure:** `nos` (units)
- **Standard Batch Size:** 500 units
- **Associated BOM:** Active Revision 1.0 (BOM ID: `bom_ss304_bracket_v1`)

### 4.2 SKU Alias Resolution Map
To support varied conversational inputs, ERP import formats, and prompt variants, the platform provides automated alias mapping in `bom_service.py`, `bom.py`, and `registry.py`:

| Input Alias / Identifier | Canonical Resolution | Product Name | Match Target |
|---|---|---|---|
| `IND-BRK-SS304` | `IND-BRK-SS304` | Stainless Steel Industrial Bracket | Primary SKU |
| `SS304-BRK-500` | `IND-BRK-SS304` | Stainless Steel Industrial Bracket | Batch 500 Alias |
| `BRK-SS-304` | `IND-BRK-SS304` | Stainless Steel Industrial Bracket | Short Notation |
| `IND-PRD-BRK` | `IND-BRK-SS304` | Stainless Steel Industrial Bracket | Copilot Default |
| `a04a77e9-fa69-4040-86be-86c6df249eff` | `IND-BRK-SS304` | Stainless Steel Industrial Bracket | Database UUID |

Any REST API endpoint or copilot tool accepting `product_id` automatically resolves any of the above aliases to `IND-BRK-SS304`.

