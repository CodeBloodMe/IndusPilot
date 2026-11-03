# IndusPilot — Comparative Procurement Baselines & Savings Analysis

## 1. Executive Overview

A common pitfall of procurement software is claiming unrealistic cost savings by comparing against arbitrary or physically impossible baselines.

The **IndusPilot Baseline Comparison Engine** benchmarks the OR-Tools optimized procurement plan against two realistic, industry-standard procurement practices:

1. **Baseline A**: Single Consolidated Supplier (Status Quo Convenience Sourcing).
2. **Baseline B**: Fragmented Lowest Price Per Material (Naive Unconstrained Sourcing).
3. **Baseline C**: IndusPilot Mixed-Integer Linear Optimal (Constrained Mathematical Optimum).

---

## 2. Baseline Definitions & Mechanics

### Baseline A — Single Consolidated Supplier
- **Industry Practice**: A procurement manager orders all required materials from a single preferred distributor to minimize PO generation, communication, and receiving paperwork.
- **Computation**:
  - The engine iterates over all eligible suppliers $s \in S$.
  - It identifies suppliers who can supply **all** requested materials ($|\{m : (s,m) \in \mathcal{E}\}| = |M|$) and whose capacity satisfies each material's demand ($C_{s,m} \ge d_m$).
  - If multiple candidate single-suppliers qualify, the engine selects the one with the lowest total landed cost:
    $$\text{Baseline A Cost} = \min_{s \in S_{\text{all}}} \left( \sum_{m \in M} c_{s,m} \cdot d_m + F_s \right)$$
  - **Feasibility Integrity**: If no single supplier can supply all materials within capacity, Baseline A is explicitly marked `is_feasible = False`, and savings claims are flagged as non-comparable.

### Baseline B — Cheapest Quoted Price Per Material
- **Industry Practice**: A buyer searches a spreadsheet and picks whichever vendor offered the lowest raw unit price for each material item independently.
- **Computation**:
  - For each material $m \in M$, select the cheapest compliant supplier $s^*(m) = \arg\min_s c_{s,m}$.
  - Compute total expenditure including the fixed freight fees of all activated vendors:
    $$\text{Baseline B Cost} = \sum_{m \in M} c_{s^*(m), m} \cdot d_m + \sum_{s \in \{s^*(m)\}} F_s$$
  - **Limitations**: Baseline B ignores multi-item freight consolidation, supplier capacity exhaustion, and delivery schedule conflicts.

### Baseline C — IndusPilot OR-Tools Optimal
- **IndusPilot Formulation**:
  Simultaneously solves continuous allocations, binary supplier activation, integer packaging units, and MOQs across all materials and suppliers.
  $$\text{Baseline C Cost} = \sum_{(s,m) \in \mathcal{E}} c_{s,m} \cdot x_{s,m}^* + \sum_{s \in S} F_s \cdot z_s^*$$

---

## 3. Savings Calculation Formulas

All savings are calculated in Python `Decimal` with `ROUND_HALF_UP` precision:

### Savings versus Baseline A:
$$\Delta_{\text{A}} (\text{INR}) = \max(0, \, \text{Cost}_{\text{Baseline A}} - \text{Cost}_{\text{IndusPilot}})$$
$$\Delta_{\text{A}} (\%) = \text{round} \left( \frac{\Delta_{\text{A}}}{\text{Cost}_{\text{Baseline A}}} \times 100, \, 2 \right)$$

### Savings versus Baseline B:
$$\Delta_{\text{B}} (\text{INR}) = \max(0, \, \text{Cost}_{\text{Baseline B}} - \text{Cost}_{\text{IndusPilot}})$$
$$\Delta_{\text{B}} (\%) = \text{round} \left( \frac{\Delta_{\text{B}}}{\text{Cost}_{\text{Baseline B}}} \times 100, \, 2 \right)$$

---

## 4. Demonstrator Case Study (Tech4Bharat 2026 Batch)

### Requirements:
- 500 units of Stainless Steel Industrial Mounting Brackets (`SS304-BRK-500`).
- Exploded Shortages:
  - 800.0 kg of SS304 Sheet 2mm
  - 40.0 nos of M8 Fasteners
  - 52.5 kg of SS308L Welding Wire

### Sourcing Comparison Results:

| Metric | Baseline A (Single Supplier) | Baseline B (Naive Cheapest) | Baseline C (IndusPilot MILP) |
| :--- | :--- | :--- | :--- |
| **Strategy** | Consolidate under Apex Steel | Pick lowest quote per SKU | Mathematical Multi-Objective |
| **Vendors Used** | 1 (Apex Steel & Alloys) | 3 distinct vendors | 2 optimal vendors |
| **Total Landed Cost** | ₹337,420.00 | ₹322,850.00 | **₹317,994.00** |
| **Fixed Freight Paid** | ₹4,500.00 (1 shipment) | ₹11,500.00 (3 shipments) | **₹6,000.00 (2 shipments)** |
| **Vendor Capacity Checked** | Yes | No (ignores bottlenecks) | **100% Verified** |
| **MOQ Enforced** | Yes | No (assumes partial lots) | **Strictly Respected** |
| **Net Savings (₹)** | **₹19,426.00** | **₹4,856.00** | **Optimal Baseline** |
| **Savings (%)** | **5.76% Savings** | **1.50% Savings** | **0.00% Deficit** |

---

## 5. Summary of Strategic Insights

1. **Freight Consolidation Eliminates Naive Sourcing Advantages**:
   While Baseline B selects lower raw material prices for certain items, paying separate fixed freight fees to 3 uncoordinated vendors cancels out the unit savings. IndusPilot's binary activation variables ($z_s$) identify when consolidating fasteners with sheet metal yields a lower total landed cost.
2. **Elimination of Phantom Savings**:
   When a single supplier does not have the capacity to supply all requirements, IndusPilot flags Baseline A as `is_feasible = False`, preventing the system from reporting false savings against an unexecutable baseline.

