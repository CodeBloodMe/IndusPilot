# IndusPilot — Mathematical Optimization Model Formulation

## 1. Overview & Problem Definition

The IndusPilot Mathematical Procurement Optimizer models multi-material, multi-supplier procurement allocation as a Mixed-Integer Linear Program (MILP).

The model determines the optimal order allocation across qualified vendors to satisfy manufacturing production demand, respecting physical vendor capacity limits, Minimum Order Quantities (MOQ), packaging lot batch sizes, delivery deadlines, and corporate budget caps.

---

## 2. Sets and Indices

- $m \in M$: Set of required raw materials ($|M| \ge 1$).
- $s \in S$: Set of qualified, eligible suppliers ($|S| \ge 1$).
- $(s, m) \in \mathcal{E} \subseteq S \times M$: Set of eligible supplier-material candidate pairs offering valid, non-quarantined, non-expired quotations.

---

## 3. Parameters

### Demand and Requirements
- $d_m \in \mathbb{R}_{>0}$: Net required demand quantity of material $m$ after BOM explosion and inventory netting.
- $\theta_m \in [0, 1]$: Maximum allowable overbuy tolerance percentage for material $m$ (default 10%, $\theta_m = 0.10$).
- $T_m^{\max} \in \mathbb{Z}_{\ge 1}$: Maximum allowable delivery lead time in days for material $m$.
- $B \in \mathbb{R}_{>0} \cup \{\infty\}$: Global procurement budget ceiling for the purchase order.

### Supplier & Material Parameters
- $c_{s,m} \in \mathbb{R}_{>0}$: Effective unit landed cost of material $m$ from supplier $s$ (including base quoted price, applicable GST, and variable handling).
- $F_s \in \mathbb{R}_{\ge 0}$: Order-level fixed freight fee charged by supplier $s$ if activated for any material.
- $C_{s,m} \in \mathbb{R}_{>0}$: Maximum monthly supply capacity of supplier $s$ for material $m$.
- $M_{s,m} \in \mathbb{R}_{>0}$: Minimum Order Quantity (MOQ) enforced by supplier $s$ for material $m$.
- $P_{s,m} \in \mathbb{R}_{\ge 1}$: Packaging lot multiple (e.g. 100 fasteners per box, 1.0 for bulk sheet metal).
- $L_{s,m} \in \mathbb{Z}_{\ge 1}$: Quoted delivery lead time in days from supplier $s$ for material $m$.
- $Q_{s,m} \in [1.0, 5.0]$: Verified supplier quality rating on a 5-point scale.
- $R_{s,m} \in [0, 100]$: Historical on-time delivery reliability score percentage.
- $K^{\max} \in \mathbb{Z}_{\ge 1}$: Maximum number of distinct suppliers permitted per material (default 3).

---

## 4. Decision Variables

- $x_{s,m} \ge 0$: Continuous variable representing the quantity of material $m$ purchased from supplier $s$.
- $y_{s,m} \in \{0, 1\}$: Binary indicator variable; $y_{s,m} = 1$ if supplier $s$ is selected to supply material $m$, and $0$ otherwise.
- $z_s \in \{0, 1\}$: Binary activation variable; $z_s = 1$ if supplier $s$ is awarded an order for at least one material, and $0$ otherwise.
- $k_{s,m} \in \mathbb{Z}_{\ge 0}$: Integer variable representing the number of discrete packaging lots purchased when $P_{s,m} > 1.0$.

---

## 5. Mathematical Constraints

### 5.1 Demand Satisfaction and Controlled Overbuy
Each material demand $d_m$ must be fully satisfied. Overbuy is restricted to vendor lot sizing or a user-defined ceiling:
$$d_m \le \sum_{s \in S : (s,m) \in \mathcal{E}} x_{s,m} \le U_m, \quad \forall m \in M$$

Where the upper quantity bound $U_m$ is determined by:
$$U_m = \max \left( d_m \cdot (1 + \theta_m), \, \max_{(s,m) \in \mathcal{E}} M_{s,m} \cdot (1 + \theta_m), \, \max_{(s,m) \in \mathcal{E}} \left( \left\lceil \frac{d_m}{P_{s,m}} \right\rceil \cdot P_{s,m} \cdot (1 + \theta_m) \right) \right)$$

This formulation prevents artificial infeasibility when demand $d_m$ is smaller than vendor lot packaging.

### 5.2 Supplier Monthly Capacity Bounds
No supplier may be allocated a quantity exceeding their declared factory capacity:
$$x_{s,m} \le C_{s,m} \cdot y_{s,m}, \quad \forall (s, m) \in \mathcal{E}$$

### 5.3 Minimum Order Quantity (MOQ) Semi-Continuous Bound
If supplier $s$ is selected for material $m$ ($y_{s,m} = 1$), the purchased quantity must be at least the supplier's MOQ:
$$x_{s,m} \ge M_{s,m} \cdot y_{s,m}, \quad \forall (s, m) \in \mathcal{E}$$

If $y_{s,m} = 0$, then $x_{s,m} = 0$.

### 5.4 Order-Level Supplier Activation (Fixed Freight Linking)
If supplier $s$ supplies any material, activation variable $z_s$ must equal 1:
$$y_{s,m} \le z_s, \quad \forall (s, m) \in \mathcal{E}$$
$$z_s \le \sum_{m : (s,m) \in \mathcal{E}} y_{s,m}, \quad \forall s \in S$$

### 5.5 Discrete Packaging Lot Multiple Constraint
When a material has a packaging unit $P_{s,m} > 1.0$ (e.g. box of 100 units):
$$x_{s,m} = P_{s,m} \cdot k_{s,m}, \quad \forall (s,m) \in \mathcal{E} \text{ where } P_{s,m} > 1.0$$
$$k_{s,m} \in \mathbb{Z}_{\ge 0}$$

### 5.6 Maximum Suppliers per Material (Quota Concentration)
To prevent operational fragmentation across too many vendors:
$$\sum_{s : (s,m) \in \mathcal{E}} y_{s,m} \le K^{\max}, \quad \forall m \in M$$

When split purchasing is disabled (`allow_split_purchasing = False`), $K^{\max} = 1$.

### 5.7 Global Procurement Budget Ceiling
Total procurement landed expenditure, including fixed freight fees, cannot exceed corporate budget $B$:
$$\sum_{(s,m) \in \mathcal{E}} c_{s,m} \cdot x_{s,m} + \sum_{s \in S} F_s \cdot z_s \le B$$

### 5.8 Delivery Deadline Compliance
Quotations with lead times exceeding deadlines are eliminated during eligibility pre-filtering:
$$\mathcal{E} \cap \{(s,m) : L_{s,m} > T_m^{\max}\} = \emptyset$$

---

## 6. Objective Functions Across Strategies

Let the total landed cost objective be:
$$\mathcal{Z}_{\text{cost}} = \sum_{(s,m) \in \mathcal{E}} c_{s,m} \cdot x_{s,m} + \sum_{s \in S} F_s \cdot z_s$$

IndusPilot optimizes one of five objective formulations based on user selection:

### Strategy 1: `LOWEST_LANDED_COST` (Pure Cost Minimisation)
$$\min \mathcal{Z} = \mathcal{Z}_{\text{cost}}$$

### Strategy 2: `BALANCED` (Multi-Criteria Pareto Compromise)
Balances unit landed cost against delivery speed, certified quality, and historical reliability:
$$\min \mathcal{Z} = \sum_{(s,m) \in \mathcal{E}} \left[ c_{s,m} + \alpha_1 \cdot L_{s,m} + \alpha_2 \cdot (5.0 - Q_{s,m}) + \alpha_3 \cdot (100.0 - R_{s,m}) \right] \cdot x_{s,m} + \sum_{s \in S} F_s \cdot z_s$$
*Default Weights:* $\alpha_1 = 3.0$ (₹/day penalty), $\alpha_2 = 12.0$ (₹/quality-star deficit), $\alpha_3 = 0.5$ (₹/reliability-point deficit).

### Strategy 3: `FASTEST_DELIVERY` (Expedited Sourcing)
Prioritises rapid order delivery to prevent manufacturing assembly idle time:
$$\min \mathcal{Z} = \sum_{(s,m) \in \mathcal{E}} \left[ c_{s,m} + 15.0 \cdot L_{s,m} \right] \cdot x_{s,m} + \sum_{s \in S} F_s \cdot z_s$$

### Strategy 4: `QUALITY_FIRST` (Zero-Defect Premium Sourcing)
Heavily favors ISO/AS9100 qualified vendors with near-zero historical scrap rates:
$$\min \mathcal{Z} = \sum_{(s,m) \in \mathcal{E}} \left[ c_{s,m} + 40.0 \cdot \max(0, 5.0 - Q_{s,m}) \right] \cdot x_{s,m} + \sum_{s \in S} F_s \cdot z_s$$

### Strategy 5: `BUDGET_CONSTRAINED`
Minimises landed cost subject to a hard budget cap constraint ($B$), guaranteeing multi-sourcing quota fulfillment within available cash flow.

---

## 7. Solver Implementation & Numerical Stability

- **Solver Engine**: Google OR-Tools `pywraplp.Solver.CreateSolver("SCIP")` (Solving Constraint Integer Programs).
- **Time Limit**: Enforces a strict 30-second execution ceiling (`solver.SetTimeLimit(30000)`).
- **Tolerance**: Integrality tolerance set to $10^{-6}$. Continuous variables rounded to 2 decimal places (`ROUND_HALF_UP`) for ERP consistency.
- **Graceful Diagnostics**: If no feasible solution exists, the solver analyses constraint violations and returns structured diagnostic reasons (e.g. MOQ lockouts, capacity deficits, budget limits, or delivery date conflicts).

