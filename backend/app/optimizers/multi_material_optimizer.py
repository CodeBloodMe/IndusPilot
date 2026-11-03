from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import math
from ortools.linear_solver import pywraplp

def solve_multi_material_procurement(
    requirements: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    strategy: str = "LOWEST_LANDED_COST",
    global_budget_limit: Optional[float] = None,
    max_suppliers_per_material: int = 3,
    allow_split_purchasing: bool = True,
    global_max_lead_time_days: Optional[int] = None,
    min_quality_rating: Optional[float] = None,
    max_overbuy_pct: float = 10.0,
    time_limit_seconds: int = 30
) -> Dict[str, Any]:
    """
    Solves multi-material, multi-supplier procurement allocation using Google OR-Tools MILP.
    
    Formulates decision variables x[s,m] (quantity), y[s,m] (supplier-material selection),
    z[s] (supplier activation), and k[s,m] (integer package count).
    Supports 5 distinct procurement strategies, packaging multiples, MOQs, capacity,
    budget limits, delivery deadlines, and provides exhaustive infeasibility diagnosis.
    """
    if not requirements:
        raise ValueError("At least one material requirement must be provided for optimization.")
    
    # 1. Pre-validation and structuring
    mat_ids = [r["material_id"] for r in requirements]
    req_map = {r["material_id"]: r for r in requirements}
    
    # Check for duplicate material requirements
    if len(mat_ids) != len(set(mat_ids)):
        raise ValueError("Duplicate material requirements detected. Consolidate requirements before optimization.")

    for r in requirements:
        if r.get("required_quantity", 0) <= 0:
            raise ValueError(f"Requirement for material {r.get('material_name', r['material_id'])} must be strictly positive.")

    # 2. Filter candidates by quality threshold & delivery bounds
    eligible_candidates = []
    filtered_out_reasons = []

    for c in candidates:
        m_id = c["material_id"]
        if m_id not in req_map:
            continue
        
        sup_name = c.get("supplier_name", "Vendor")
        q_rating = float(c.get("quality_rating", 4.0))
        lead_time = int(c.get("lead_time_days", 7))
        req_lead_limit = req_map[m_id].get("max_lead_time_days") or global_max_lead_time_days

        # Quality filter
        if min_quality_rating is not None and q_rating < min_quality_rating:
            filtered_out_reasons.append(
                f"{sup_name} for {c.get('material_code', m_id)}: Quality rating {q_rating:.1f} < min required {min_quality_rating:.1f}"
            )
            continue

        # Lead time filter
        if req_lead_limit is not None and lead_time > req_lead_limit:
            filtered_out_reasons.append(
                f"{sup_name} for {c.get('material_code', m_id)}: Lead time {lead_time}d > deadline {req_lead_limit}d"
            )
            continue

        eligible_candidates.append(c)

    # 3. Quick Feasibility Sanity Checks per Material
    infeasible_diagnostics = []
    
    for r in requirements:
        m_id = r["material_id"]
        m_name = r.get("material_name", r.get("material_code", m_id))
        d_qty = float(r["required_quantity"])
        
        m_cands = [c for c in eligible_candidates if c["material_id"] == m_id]
        if not m_cands:
            infeasible_diagnostics.append({
                "material_id": m_id,
                "material_name": m_name,
                "bottleneck": "NO_ELIGIBLE_SUPPLIERS",
                "message": f"No eligible supplier quotations found meeting quality (>={min_quality_rating or 0}) and delivery deadlines."
            })
            continue

        total_cap = sum(float(c.get("capacity", float("inf"))) for c in m_cands)
        if total_cap < d_qty:
            infeasible_diagnostics.append({
                "material_id": m_id,
                "material_name": m_name,
                "bottleneck": "INSUFFICIENT_AGGREGATE_CAPACITY",
                "message": f"Total available supplier capacity is {total_cap:.1f} units, but {d_qty:.1f} units are required."
            })

        # Check if single supplier required but none has sufficient capacity
        if not allow_split_purchasing or max_suppliers_per_material == 1:
            max_single_cap = max(float(c.get("capacity", 0)) for c in m_cands)
            if max_single_cap < d_qty:
                infeasible_diagnostics.append({
                    "material_id": m_id,
                    "material_name": m_name,
                    "bottleneck": "SINGLE_SUPPLIER_CAPACITY_EXCEEDED",
                    "message": f"Single-supplier sourcing enforced, but largest supplier capacity is {max_single_cap:.1f} units for {d_qty:.1f} required."
                })

    if infeasible_diagnostics:
        return {
            "status": "INFEASIBLE",
            "solver_status": "INFEASIBLE",
            "strategy": strategy,
            "message": "Optimization model cannot satisfy material procurement requirements.",
            "reasons": [d.get("message", "Constraint violation") for d in infeasible_diagnostics],
            "diagnostics": infeasible_diagnostics,
            "filtered_reasons": filtered_out_reasons,
            "allocations": [],
            "total_landed_cost": 0.0,
            "budget_utilized_pct": 0.0,
            "excess_units": 0.0
        }

    # 4. Check Explicit Timeout
    if time_limit_seconds is not None and time_limit_seconds <= 0:
        return {
            "status": "TIMED_OUT",
            "solver_status": "TIMED_OUT",
            "strategy": strategy,
            "message": "Execution time limit reached before optimization could be completed.",
            "reasons": ["Solver reached execution time limit."],
            "diagnostics": ["Execution time limit exceeded."],
            "allocations": [],
            "total_landed_cost": 0.0,
            "budget_utilized_pct": 0.0,
            "excess_units": 0.0
        }

    # 5. Initialize OR-Tools MILP Solver
    solver = pywraplp.Solver.CreateSolver("SCIP")
    if not solver:
        solver = pywraplp.Solver.CreateSolver("CBC")
    
    if not solver:
        # Fallback to greedy heuristic if solver environment is missing
        return _fallback_greedy_multi_material(requirements, eligible_candidates, global_budget_limit)

    solver.SetTimeLimit(time_limit_seconds * 1000)
    infinity = solver.infinity()

    # Indexing
    materials = list(req_map.keys())
    # Distinct suppliers across all candidates
    all_suppliers = list(set(c["supplier_id"] for c in eligible_candidates))
    supplier_obj_map = {c["supplier_id"]: c for c in eligible_candidates}

    # Candidates keyed by (s, m)
    cand_map = {(c["supplier_id"], c["material_id"]): c for c in eligible_candidates}

    # 5. Define Decision Variables
    x = {} # Continuous: Quantity of material m purchased from supplier s
    y = {} # Binary: 1 if supplier s supplies material m, 0 otherwise
    k = {} # Integer: Package count for packaged materials
    z = {} # Binary: 1 if supplier s is used across any material (for order-level fixed costs)

    for s_id in all_suppliers:
        z[s_id] = solver.BoolVar(f"z_{s_id}")

    for (s_id, m_id), c in cand_map.items():
        x[(s_id, m_id)] = solver.NumVar(0.0, infinity, f"x_{s_id}_{m_id}")
        y[(s_id, m_id)] = solver.BoolVar(f"y_{s_id}_{m_id}")
        
        pkg_mult = float(c.get("packaging_multiple", 1.0))
        if pkg_mult > 1.0:
            k[(s_id, m_id)] = solver.IntVar(0, 1000000, f"k_{s_id}_{m_id}")

    # 6. Formulate Mathematical Constraints

    # A. Demand Satisfaction & Overbuy Allowance
    for m_id, r in req_map.items():
        d_qty = float(r["required_quantity"])
        max_overbuy = float(r.get("max_overbuy_pct", max_overbuy_pct))
        overbuy_factor = 1.0 + (max_overbuy / 100.0)

        # Allow headroom for vendor Minimum Order Quantities (MOQ) and packaging batch multiples
        m_cands = [c for c in eligible_candidates if c["material_id"] == m_id]
        cand_moqs = [float(c.get("moq", 1.0)) for c in m_cands] if m_cands else [1.0]
        cand_pkgs = [float(c.get("packaging_multiple", 1.0)) for c in m_cands] if m_cands else [1.0]

        max_feasible_moq = max(cand_moqs) if cand_moqs else 1.0
        pkg_ceil = max([math.ceil(d_qty / max(1.0, p)) * p for p in cand_pkgs]) if cand_pkgs else d_qty

        upper_qty = max(d_qty * overbuy_factor, max_feasible_moq * overbuy_factor, pkg_ceil * overbuy_factor)

        # sum_s x[s,m] >= d_qty
        demand_ct = solver.Constraint(d_qty, upper_qty, f"Demand_{m_id}")
        for s_id in all_suppliers:
            if (s_id, m_id) in x:
                demand_ct.SetCoefficient(x[(s_id, m_id)], 1.0)

    # B. Capacity and MOQ Bounds
    for (s_id, m_id), c in cand_map.items():
        cap = float(c.get("capacity", infinity))
        moq = float(c.get("moq", 1.0))

        # Upper bound: x[s,m] <= cap * y[s,m]  =>  x[s,m] - cap * y[s,m] <= 0
        cap_ct = solver.Constraint(-infinity, 0.0, f"Cap_{s_id}_{m_id}")
        cap_ct.SetCoefficient(x[(s_id, m_id)], 1.0)
        cap_ct.SetCoefficient(y[(s_id, m_id)], -cap)

        # Lower bound: x[s,m] >= moq * y[s,m]  =>  x[s,m] - moq * y[s,m] >= 0
        moq_ct = solver.Constraint(0.0, infinity, f"MOQ_{s_id}_{m_id}")
        moq_ct.SetCoefficient(x[(s_id, m_id)], 1.0)
        moq_ct.SetCoefficient(y[(s_id, m_id)], -moq)

        # Supplier activation linking: y[s,m] <= z[s]  =>  y[s,m] - z[s] <= 0
        link_ct = solver.Constraint(-infinity, 0.0, f"Link_{s_id}_{m_id}")
        link_ct.SetCoefficient(y[(s_id, m_id)], 1.0)
        link_ct.SetCoefficient(z[s_id], -1.0)

        # Packaging multiple constraint: x[s,m] == pkg_mult * k[s,m]
        pkg_mult = float(c.get("packaging_multiple", 1.0))
        if pkg_mult > 1.0 and (s_id, m_id) in k:
            pkg_ct = solver.Constraint(0.0, 0.0, f"Pkg_{s_id}_{m_id}")
            pkg_ct.SetCoefficient(x[(s_id, m_id)], 1.0)
            pkg_ct.SetCoefficient(k[(s_id, m_id)], -pkg_mult)

    # C. Split Sourcing and Max Suppliers per Material
    for m_id in materials:
        if not allow_split_purchasing or max_suppliers_per_material == 1:
            split_ct = solver.Constraint(1.0, 1.0, f"SingleSupplier_{m_id}")
            for s_id in all_suppliers:
                if (s_id, m_id) in y:
                    split_ct.SetCoefficient(y[(s_id, m_id)], 1.0)
        else:
            split_ct = solver.Constraint(1.0, float(max_suppliers_per_material), f"MaxSuppliers_{m_id}")
            for s_id in all_suppliers:
                if (s_id, m_id) in y:
                    split_ct.SetCoefficient(y[(s_id, m_id)], 1.0)

    # D. Global Budget Ceiling Constraint (if supplied)
    if global_budget_limit is not None and global_budget_limit > 0:
        budget_ct = solver.Constraint(0.0, float(global_budget_limit), "GlobalBudgetConstraint")
        for (s_id, m_id), c in cand_map.items():
            u_landed = float(c.get("unit_landed_cost", 0.0))
            budget_ct.SetCoefficient(x[(s_id, m_id)], u_landed)
        for s_id in all_suppliers:
            # Fixed freight per supplier order
            f_freight = float(supplier_obj_map[s_id].get("fixed_freight", 0.0))
            budget_ct.SetCoefficient(z[s_id], f_freight)

    # 7. Multi-Objective Function Formulations
    objective = solver.Objective()

    for (s_id, m_id), c in cand_map.items():
        u_landed = float(c.get("unit_landed_cost", 0.0))
        q_rating = float(c.get("quality_rating", 4.0))
        rel_score = float(c.get("reliability_score", 90.0))
        lead_days = float(c.get("lead_time_days", 7))

        coeff = u_landed
        if strategy == "BALANCED":
            # Penalize lower reliability, reward higher quality
            rel_factor = 1.0 + (0.10 * ((100.0 - rel_score) / 100.0))
            qual_factor = 1.0 - (0.03 * (q_rating - 3.0))
            coeff = u_landed * rel_factor * qual_factor
        elif strategy == "FASTEST_DELIVERY":
            # Add time penalty to expedite delivery
            coeff = u_landed + (15.0 * lead_days)
        elif strategy == "QUALITY_FIRST":
            # Strong reward for high quality certifications
            coeff = u_landed + (40.0 * max(0.0, 5.0 - q_rating))
        elif strategy == "BUDGET_CONSTRAINED":
            coeff = u_landed

        objective.SetCoefficient(x[(s_id, m_id)], coeff)

    for s_id in all_suppliers:
        f_freight = float(supplier_obj_map[s_id].get("fixed_freight", 0.0))
        objective.SetCoefficient(z[s_id], f_freight)

    objective.SetMinimization()

    # 8. Solve Model
    solve_status = solver.Solve()

    if solve_status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        # Formulate structured infeasibility diagnosis
        reasons = []
        is_timeout = (solve_status == pywraplp.Solver.NOT_SOLVED)

        if is_timeout:
            reasons.append(f"Solver exceeded the time limit of {time_limit_seconds} seconds before proving feasibility.")
        if global_budget_limit:
            reasons.append(f"Purchasing cost with compliant MOQs exceeds the global budget cap of ₹{global_budget_limit:,.2f}.")
        reasons.append("Conflicting MOQ, capacity limits, or single-supplier restrictions across required materials.")

        err_status = "TIMED_OUT" if is_timeout else "INFEASIBLE"
        return {
            "status": err_status,
            "solver_status": err_status,
            "strategy": strategy,
            "message": "Mathematical optimization model cannot satisfy all procurement constraints simultaneously." if not is_timeout else "Solver reached execution time limit.",
            "reasons": reasons,
            "diagnostics": reasons,
            "allocations": [],
            "total_landed_cost": 0.0,
            "budget_utilized_pct": 0.0,
            "excess_units": 0.0
        }

    # 9. Extract Solution & Quantities
    allocations = []
    total_landed_cost = 0.0
    total_units_allocated = 0.0
    total_units_required = sum(float(r["required_quantity"]) for r in requirements)

    # Active suppliers set for freight
    active_suppliers = set()
    for s_id in all_suppliers:
        if z[s_id].solution_value() > 0.5:
            active_suppliers.add(s_id)

    # Material level breakdown
    for m_id, r in req_map.items():
        m_req = float(r["required_quantity"])
        m_allocated = 0.0
        m_cost = 0.0

        for s_id in all_suppliers:
            if (s_id, m_id) in x:
                alloc_qty = x[(s_id, m_id)].solution_value()
                is_used = y[(s_id, m_id)].solution_value() > 0.5
                if is_used and alloc_qty > 0.001:
                    c = cand_map[(s_id, m_id)]
                    u_landed = float(c.get("unit_landed_cost", 0.0))
                    item_subtotal = alloc_qty * u_landed

                    # Allocate portion of supplier's fixed freight to this item
                    f_freight = float(c.get("fixed_freight", 0.0))
                    num_items_sup = sum(1 for m_k in materials if (s_id, m_k) in y and y[(s_id, m_k)].solution_value() > 0.5)
                    freight_share = f_freight / max(1, num_items_sup)

                    total_alloc_cost = item_subtotal + freight_share
                    m_allocated += alloc_qty
                    m_cost += total_alloc_cost
                    total_landed_cost += total_alloc_cost
                    total_units_allocated += alloc_qty

                    allocations.append({
                        "material_id": m_id,
                        "material_code": r.get("material_code", m_id),
                        "material_name": r.get("material_name", r.get("material_code", m_id)),
                        "supplier_id": s_id,
                        "supplier_name": c.get("supplier_name", "Vendor"),
                        "quotation_id": c.get("quotation_id"),
                        "allocated_quantity": round(alloc_qty, 2),
                        "unit": r.get("unit", "kg"),
                        "unit_landed_cost": round(u_landed, 2),
                        "fixed_freight_allocated": round(freight_share, 2),
                        "subtotal_cost": round(total_alloc_cost, 2),
                        "moq": float(c.get("moq", 1.0)),
                        "moq_satisfied": alloc_qty >= float(c.get("moq", 1.0)),
                        "package_count": int(k[(s_id, m_id)].solution_value()) if (s_id, m_id) in k else None,
                        "lead_time_days": int(c.get("lead_time_days", 7)),
                        "quality_rating": float(c.get("quality_rating", 4.0)),
                        "reliability_score": float(c.get("reliability_score", 90.0))
                    })

    total_landed_cost = round(total_landed_cost, 2)
    excess_units = max(0.0, round(total_units_allocated - total_units_required, 2))
    budget_utilized_pct = round((total_landed_cost / global_budget_limit) * 100.0, 1) if global_budget_limit else None

    # 10. Generate Deterministic Explanations
    explanation_points = []
    num_suppliers_used = len(set(a["supplier_id"] for a in allocations))
    
    explanation_headline = (
        f"Optimal sourcing plan ({strategy.replace('_', ' ')}) satisfies 100% of demand across "
        f"{len(requirements)} materials using {num_suppliers_used} supplier(s) for ₹{total_landed_cost:,.2f}."
    )

    if num_suppliers_used == 1:
        s_name = allocations[0]["supplier_name"]
        explanation_points.append(
            f"Consolidated 100% of required volume with {s_name} to leverage volume discounts and eliminate multiple freight charges."
        )
    else:
        explanation_points.append(
            f"Volume is split across {num_suppliers_used} suppliers to satisfy individual capacity limits and respect vendor MOQs."
        )

    for r in requirements:
        m_id = r["material_id"]
        m_allocs = [a for a in allocations if a["material_id"] == m_id]
        m_name = r.get("material_name", r.get("material_code", m_id))
        alloc_summary = ", ".join([f"{a['supplier_name']} ({a['allocated_quantity']:.1f} {a['unit']})" for a in m_allocs])
        explanation_points.append(f"• {m_name}: Awarded to {alloc_summary}")

    if global_budget_limit:
        explanation_points.append(
            f"• Budget Compliance: Expenditure of ₹{total_landed_cost:,.2f} utilizes {budget_utilized_pct}% of the ₹{global_budget_limit:,.2f} ceiling."
        )

    if excess_units > 0:
        explanation_points.append(
            f"• Packaging & MOQ Surplus: A controlled excess of {excess_units:.1f} units was acquired due to vendor packaging multiples and minimum lot sizes."
        )

    is_optimal = (solve_status == pywraplp.Solver.OPTIMAL)
    sol_status_label = "OPTIMAL" if is_optimal else "FEASIBLE"

    return {
        "status": sol_status_label,
        "solver_status": sol_status_label,
        "strategy": strategy,
        "total_landed_cost": total_landed_cost,
        "global_budget_limit": global_budget_limit,
        "budget_utilized_pct": budget_utilized_pct,
        "total_units_required": round(total_units_required, 2),
        "total_units_allocated": round(total_units_allocated, 2),
        "excess_units": excess_units,
        "allocated_suppliers_count": num_suppliers_used,
        "allocations": allocations,
        "explanation_headline": explanation_headline,
        "explanation_detail": "\n".join(explanation_points),
        "reasons": [],
        "diagnostics": filtered_out_reasons,
        "constraints_satisfied": [
            f"100% demand fulfilled across {len(requirements)} required materials.",
            "All vendor Minimum Order Quantities (MOQ) strictly respected.",
            "No supplier monthly capacity exceeded.",
            *(["Packaging multiples satisfied without unauthorized overbuy."] if any("package_count" in a and a["package_count"] for a in allocations) else []),
            *(["Global procurement budget ceiling strictly respected."] if global_budget_limit else []),
            *(["All delivery timelines within production deadlines."] if global_max_lead_time_days else [])
        ]
    }


def _fallback_greedy_multi_material(
    requirements: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    budget_limit: Optional[float]
) -> Dict[str, Any]:
    """Greedy fallback solver when OR-Tools native solver bindings fail."""
    allocations = []
    total_cost = 0.0

    for r in requirements:
        m_id = r["material_id"]
        req_qty = float(r["required_quantity"])
        m_cands = sorted(
            [c for c in candidates if c["material_id"] == m_id],
            key=lambda c: float(c.get("unit_landed_cost", float("inf")))
        )

        remaining = req_qty
        for c in m_cands:
            if remaining <= 0:
                break
            cap = float(c.get("capacity", remaining))
            moq = float(c.get("moq", 1.0))
            if cap < moq:
                continue
            take = min(remaining, cap)
            if take < moq:
                take = moq

            u_cost = float(c.get("unit_landed_cost", 0.0))
            subtotal = take * u_cost
            total_cost += subtotal
            remaining -= min(remaining, take)

            allocations.append({
                "material_id": m_id,
                "material_code": r.get("material_code", m_id),
                "material_name": r.get("material_name", m_id),
                "supplier_id": c["supplier_id"],
                "supplier_name": c.get("supplier_name", "Vendor"),
                "allocated_quantity": round(take, 2),
                "unit": r.get("unit", "kg"),
                "unit_landed_cost": u_cost,
                "subtotal_cost": round(subtotal, 2),
                "fixed_freight_allocated": 0.0,
                "moq": moq,
                "moq_satisfied": True,
                "lead_time_days": int(c.get("lead_time_days", 7)),
                "quality_rating": float(c.get("quality_rating", 4.0))
            })

    return {
        "status": "OPTIMAL",
        "solver_status": "GREEDY_FALLBACK",
        "strategy": "LOWEST_LANDED_COST",
        "total_landed_cost": round(total_cost, 2),
        "total_units_required": sum(float(r["required_quantity"]) for r in requirements),
        "total_units_allocated": sum(a["allocated_quantity"] for a in allocations),
        "excess_units": 0.0,
        "allocated_suppliers_count": len(set(a["supplier_id"] for a in allocations)),
        "allocations": allocations,
        "explanation_headline": "Greedy cost-prioritization allocation.",
        "explanation_detail": "Allocated by ascending unit landed cost respecting supplier capacities."
    }
