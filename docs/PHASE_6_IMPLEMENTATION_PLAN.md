# IndusPilot — Phase 6 Implementation Plan
## Advanced AI-Assisted Procurement Planning & Mathematical Optimisation Engine

**Project:** IndusPilot (Problem Statement 4.1 — Industrial Manufacturing Procurement)  
**Status:** Audit Completed | Ready for Implementation  

---

## 1. Existing Implementation Audit

### 1.1 OR-Tools & Solver Status
- **Installation:** Google OR-Tools is installed and operational in `backend/.venv` (`ortools.linear_solver.pywraplp`).
- **Solvers:** Uses SCIP (`pywraplp.Solver.CreateSolver("SCIP")`) with fallback to CBC (`"CBC"`). A deterministic greedy fallback exists if solver bindings fail.
- **Current Limitation:** The existing optimizer in `procurement_optimizer.py` is single-material only ($x_i$ continuous quantity for one item). It does not support multi-material BOM demand ($x_{s,m}$), packaging multiples ($x_{s,m} = P_{s,m} \cdot k_{s,m}$), multi-objective strategies, or database persistence.

### 1.2 Integration with Preceding Phases
- **Phase 3 (Supplier Quotations):** 36 verified quotations exist across 10 suppliers for metals (SS304, SS316, MS IS2062, Al 6061, Brass C36000), hardware fasteners (M8, M10), welding wire (308L, E7018), and coatings (Powder 7035).
- **Phase 4 (Landed Cost & Eligibility):** Full 7-factor landed cost engine exists (`calculate_landed_cost` in `landed_cost.py`) and quotation eligibility gate exists (`check_quotation_eligibility` in `eligibility_engine.py`).
- **Phase 5 (MRP & Inventory):** Production jobs (`ProductionJob`), MRP material check (`runJobMaterialCheck`), and perpetual inventory ledger (`Inventory`, `StockReservation`) can produce real net purchasing shortages.

---

## 2. Core Deficiencies & Target Improvements

| Capability | Current State | Phase 6 Target Architecture |
| :--- | :--- | :--- |
| **Material Scope** | Single material only | Multi-material vector $\mathbf{m} = [m_1, m_2, \dots, m_K]$ with cross-material budget |
| **Supplier Allocation** | Single material split across suppliers | Multi-material allocation matrix $X_{s,m}$ with packaging constraints |
| **Packaging Constraints** | Continuous quantities ($x_i \ge \text{MOQ}$) | Integer packaging multiples $x_{s,m} = P_{s,m} \cdot k_{s,m}$ with controlled overbuy |
| **Procurement Strategies** | Single objective: min cost | 5 strategies: Lowest Landed Cost, Balanced, Fastest Delivery, Quality-First, Budget-Constrained |
| **Baseline Benchmark** | No baseline benchmark | Baseline A (Single Cheapest), Baseline B (Cheapest Eligible per Material), Baseline C (OR-Tools) |
| **Persistence** | Transient in-memory API response | Immutable database persistence: `ProcurementPlan`, `ProcurementPlanItem`, `ProcurementPlanAllocation` |
| **Plan Lifecycle** | Stateless solve endpoint | `DRAFT` $\rightarrow$ `OPTIMIZED` $\rightarrow$ `AWAITING_APPROVAL` $\rightarrow$ `APPROVED` $\rightarrow$ `REQUISITION_DISPATCH` |
| **Infeasibility Diagnosis** | Generic text error | Structured diagnosis: capacity shortage, budget bottleneck, delivery lead time impossibility |

---

## 3. Mathematical Model Specification

### 3.1 Decision Variables
For each material $m \in M$ and supplier candidate $s \in S_m$:
- $x_{s,m} \ge 0$: Continuous quantity of material $m$ purchased from supplier $s$.
- $y_{s,m} \in \{0, 1\}$: Binary variable indicating whether supplier $s$ is selected for material $m$.
- $z_s \in \{0, 1\}$: Binary variable indicating whether supplier $s$ is used at all (for order-level fixed costs).
- $k_{s,m} \in \mathbb{Z}_{\ge 0}$: Integer variable for package count when packaging multiple $P_{s,m} > 1$.

### 3.2 Constraints
1. **Demand Satisfaction & Overbuy Bound:**
   $$D_m \le \sum_{s \in S_m} x_{s,m} \le D_m \cdot (1 + \alpha_{\text{overbuy}})$$
2. **Supplier Capacity:**
   $$x_{s,m} \le C_{s,m} \cdot y_{s,m}$$
3. **Minimum Order Quantity (MOQ):**
   $$x_{s,m} \ge \text{MOQ}_{s,m} \cdot y_{s,m}$$
4. **Supplier Activation Linking:**
   $$y_{s,m} \le z_s \quad \forall m \in M$$
5. **Maximum Suppliers Limit:**
   $$\sum_{s \in S_m} y_{s,m} \le K_{\text{max\_suppliers}}$$
6. **Delivery Deadline Feasibility:**
   $$L_{s,m} \cdot y_{s,m} \le L_{\text{max\_days}, m}$$
7. **Total Procurement Budget Ceiling:**
   $$\sum_{m \in M} \sum_{s \in S_m} \left(c_{s,m}^{\text{landed}} \cdot x_{s,m}\right) + \sum_{s \in S} \left(F_s^{\text{fixed}} \cdot z_s\right) \le B_{\text{total}}$$

### 3.3 Multi-Objective Function Formulations
- **Strategy 1: `LOWEST_LANDED_COST`**
  $$\min \sum_{m} \sum_{s} c_{s,m}^{\text{landed}} x_{s,m} + \sum_{s} F_s^{\text{fixed}} z_s$$
- **Strategy 2: `BALANCED` (Cost + Quality + Reliability)**
  $$\min \sum_{m} \sum_{s} \left(c_{s,m}^{\text{landed}} \cdot (1.0 + \lambda_r(1 - R_s) - \lambda_q(Q_s - 3.0))\right) x_{s,m} + \sum_{s} F_s z_s$$
- **Strategy 3: `FASTEST_DELIVERY`**
  $$\min \sum_{m} \sum_{s} \left(L_{s,m} \cdot w_{\text{time}} + c_{s,m} \cdot w_{\text{cost}}\right) x_{s,m}$$
- **Strategy 4: `QUALITY_FIRST`**
  $$\min \sum_{m} \sum_{s} \left(c_{s,m}^{\text{landed}} - w_{\text{qual}} \cdot Q_s\right) x_{s,m}$$
- **Strategy 5: `BUDGET_CONSTRAINED`**
  $$\min \text{Total Landed Cost} \quad \text{subject to strict } \text{Total Cost} \le B$$

---

## 4. Implementation Steps

1. **Database Entities & Alembic Migration:**
   - Define `ProcurementPlan`, `ProcurementPlanItem`, `ProcurementPlanAllocation`.
   - Create and apply Alembic migration `0005_procurement_optimization.py`.
2. **Advanced Multi-Material Optimizer Service (`backend/app/optimizers/multi_material_optimizer.py`):**
   - Implement multi-material MILP formulation using Google OR-Tools.
   - Support integer packaging multiples, split limits, and 5 procurement strategies.
   - Comprehensive infeasibility diagnosis and structured bottleneck analysis.
3. **Procurement Baseline Comparison Engine (`backend/app/services/procurement_baseline.py`):**
   - Implement Baseline A (Single Cheapest) and Baseline B (Cheapest Eligible per material).
   - Compute absolute and percentage savings against the OR-Tools optimized solution.
4. **Procurement Plan Orchestration Service (`backend/app/services/procurement_plan_service.py`):**
   - Aggregate requirements from production jobs or BOM shortages.
   - Candidate generation filtering out quarantined/expired/ineligible quotations.
   - Plan creation, solver execution, explanation generation, approval transitions, and requisition dispatch.
5. **REST API Routers (`backend/app/api/v1/procurement_plans.py` & updated `optimizer.py`):**
   - Pydantic domain schemas.
   - Mount routes in `main.py`.
6. **Frontend Workspace (`OptimizationView.tsx` & `api.ts`):**
   - Multi-material requirements console.
   - Strategy and constraint tuning.
   - Results dashboard with allocations, excess analysis, baseline comparison cards, and approval handoff.
7. **Comprehensive Pytest Suite (`test_phase6_procurement_optimization.py`):**
   - Multi-material optimization, MOQ/capacity constraints, strategies, baselines, and approval lifecycles.
   - Verify all 64+ existing tests continue to pass.
8. **Documentation:**
   - `docs/PROCUREMENT_OPTIMIZATION.md`
   - `docs/OPTIMIZATION_MATHEMATICAL_MODEL.md`
   - `docs/SUPPLIER_ALLOCATION.md`
   - `docs/PROCUREMENT_BASELINE_ANALYSIS.md`
   - `docs/PROCUREMENT_APPROVAL_WORKFLOW.md`
   - Update `docs/API_DOCUMENTATION.md`

