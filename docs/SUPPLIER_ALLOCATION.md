# IndusPilot — Intelligent Supplier Allocation & Multi-Sourcing Mechanics

## 1. Overview

In industrial manufacturing, allocating purchasing quotas to suppliers involves complex trade-offs between price, capacity, supply continuity, and administrative overhead. 

The **IndusPilot Supplier Allocation Engine** eliminates manual guesswork by evaluating all available supplier quotations simultaneously using mathematical optimization.

---

## 2. Multi-Sourcing vs. Single Sourcing

### Single-Sourcing (`allow_split_purchasing = False` or $K^{\max} = 1$)
- **Operational Reality**: Allocates 100% of a material's demand to a single vendor.
- **Advantages**: Minimal purchase order administration, higher volume leverage with one vendor, streamlined shipment tracking.
- **Risks**: High vulnerability to supplier stockouts, factory fires, strikes, or transport bottlenecks.
- **Feasibility Constraint**: If the demand exceeds the single supplier's monthly available capacity, or if their MOQ exceeds the total demand, single-sourcing becomes mathematically infeasible.

### Multi-Sourcing (`allow_split_purchasing = True` and $K^{\max} \ge 2$)
- **Operational Reality**: Splits procurement quantities across 2 to $K^{\max}$ eligible suppliers.
- **Advantages**:
  1. Overcomes individual supplier monthly capacity bottlenecks.
  2. Reduces single-point supply chain risk.
  3. Enables blending a low-cost, high-lead-time supplier with a high-cost, fast-turnaround supplier.
- **Control Mechanisms**: To prevent excessive fragmentation (e.g., ordering 10 kg from 10 different vendors), the engine enforces:
  - Upper limit on distinct vendors per material ($K^{\max}$).
  - Strict compliance with each vendor's Minimum Order Quantity ($x_{s,m} \ge \text{MOQ}_{s,m}$).

---

## 3. Handling Packaging Multiples & Minimum Order Quantities (MOQ)

### Packaging Multiples ($P_{s,m} > 1.0$)
In discrete parts manufacturing (e.g. M8 stainless steel hex bolts), suppliers sell materials in discrete packaging multiples (boxes of 100, cartons of 500) rather than individual loose units.

- The solver formulates discrete integer variables $k_{s,m}$:
  $$x_{s,m} = P_{s,m} \cdot k_{s,m}, \quad k_{s,m} \in \mathbb{Z}_{\ge 0}$$
- If a production job requires 2,040 fasteners and vendor packaging is 100 units/box, the engine allocates 21 boxes (2,100 units), generating an intentional, documented surplus of 60 units.

### Surplus Handling & Overbuy Ceiling
To prevent rogue solvers from ordering massive excess stock just to capture volume price breaks, IndusPilot caps total overbuy:
$$\text{AllocatedQuantity} \le \text{RequiredQuantity} \cdot (1 + \theta)$$
Where $\theta$ is the user-defined overbuy tolerance (default 10%).

---

## 4. Fixed Freight Consolidation & Vendor Activation

Most industrial suppliers charge an order-level fixed freight and logistics fee ($F_s$, e.g. ₹4,500 per dispatch) regardless of the number of line items ordered.

### Binary Activation Variable $z_s \in \{0, 1\}$:
- The solver introduces binary variable $z_s$ for each supplier $s \in S$.
- When supplier $s$ is awarded an order for any material $m$, $y_{s,m} = 1$, forcing $z_s = 1$.
- The objective function adds $F_s \cdot z_s$.
- **Economic Effect**: If Supplier A can supply both Stainless Steel Sheet and M8 Fasteners, activating Supplier A incurs the fixed ₹4,500 fee only once, incentivizing order consolidation when economically advantageous over splitting.

---

## 5. Summary of Allocation Diagnostics

When a procurement requirement cannot be satisfied, IndusPilot isolates the exact root cause:

| Infeasibility Condition | Root Cause Identified | Recommended Action |
| :--- | :--- | :--- |
| **Capacity Deficit** | Total eligible vendor capacity < Demand | Increase candidate pool or enable split sourcing. |
| **MOQ Lockout** | Lowest vendor MOQ > Allowable overbuy | Adjust lot size tolerance or increase order volume. |
| **Budget Exceeded** | Lowest feasible landed cost > Budget cap | Increase budget ceiling or select cheaper material grades. |
| **Deadline Conflict** | All compliant vendor lead times > Deadline | Relax delivery deadline or approve express freight quotes. |

