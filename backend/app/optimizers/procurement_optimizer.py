from typing import List, Dict, Any, Optional
from ortools.linear_solver import pywraplp

def optimize_procurement_split(
    required_quantity: float,
    supplier_candidates: List[Dict[str, Any]],
    budget_limit: Optional[float] = None,
    max_lead_time_days: Optional[int] = None,
    enforce_single_supplier: bool = False,
) -> Dict[str, Any]:
    """
    Solves multi-supplier procurement allocation using Google OR-Tools (MILP).
    Considers capacity limits, minimum order quantities (MOQ), landed unit costs,
    fixed freight charges, delivery lead times, and budget ceilings.
    """
    if required_quantity <= 0:
        raise ValueError("Required quantity must be positive.")
    if not supplier_candidates:
        return {
            "status": "INFEASIBLE",
            "message": "No supplier candidates provided for optimization.",
            "allocations": [],
            "total_cost": 0.0,
            "reasons": ["Candidate supplier list is empty."]
        }

    # Filter candidates by lead time if hard constraint is applied
    eligible_candidates = []
    filtered_out_lead_time = []
    for s in supplier_candidates:
        lead = s.get("lead_time_days", 7)
        if max_lead_time_days is not None and lead > max_lead_time_days:
            filtered_out_lead_time.append(f"{s.get('supplier_name')} (Lead time {lead}d > max {max_lead_time_days}d)")
        else:
            eligible_candidates.append(s)

    if not eligible_candidates:
        return {
            "status": "INFEASIBLE",
            "message": "No suppliers satisfy the maximum delivery timeline constraint.",
            "allocations": [],
            "total_cost": 0.0,
            "reasons": [f"Filtered out due to delivery delay: {', '.join(filtered_out_lead_time)}"]
        }

    # Check total aggregate capacity
    total_avail_capacity = sum(s.get("capacity", float("inf")) for s in eligible_candidates)
    if total_avail_capacity < required_quantity:
        return {
            "status": "INFEASIBLE",
            "message": "Aggregate supplier capacity is insufficient to satisfy total required quantity.",
            "allocations": [],
            "total_cost": 0.0,
            "reasons": [
                f"Total available capacity across {len(eligible_candidates)} eligible suppliers is "
                f"{total_avail_capacity:.1f} units, but {required_quantity:.1f} units are required."
            ]
        }

    # Initialize OR-Tools SCIP / CBC solver
    solver = pywraplp.Solver.CreateSolver("SCIP")
    if not solver:
        # Fallback to CBC
        solver = pywraplp.Solver.CreateSolver("CBC")

    if not solver:
        # Deterministic greedy fallback if solver binding fails
        return _greedy_fallback_allocation(required_quantity, eligible_candidates, budget_limit)

    N = len(eligible_candidates)
    x = {} # Continuous: quantity allocated to supplier i
    y = {} # Binary: 1 if supplier i is chosen, 0 otherwise

    infinity = solver.infinity()
    for i in range(N):
        x[i] = solver.NumVar(0.0, infinity, f"x_{i}")
        y[i] = solver.BoolVar(f"y_{i}")

    # 1. Total quantity constraint: sum(x[i]) == required_quantity
    demand_constraint = solver.Constraint(required_quantity, required_quantity, "DemandConstraint")
    for i in range(N):
        demand_constraint.SetCoefficient(x[i], 1.0)

    # 2. Capacity & MOQ linking constraints for each supplier
    for i, s in enumerate(eligible_candidates):
        cap = float(s.get("capacity", required_quantity * 5))
        moq = float(s.get("moq", 1.0))

        # Upper bound: x[i] <= cap * y[i]  =>  x[i] - cap * y[i] <= 0
        cap_constraint = solver.Constraint(-infinity, 0.0, f"Capacity_{i}")
        cap_constraint.SetCoefficient(x[i], 1.0)
        cap_constraint.SetCoefficient(y[i], -cap)

        # Lower bound (MOQ): x[i] >= moq * y[i]  =>  x[i] - moq * y[i] >= 0
        moq_constraint = solver.Constraint(0.0, infinity, f"MOQ_{i}")
        moq_constraint.SetCoefficient(x[i], 1.0)
        moq_constraint.SetCoefficient(y[i], -moq)

    # 3. Enforce single supplier constraint if requested
    if enforce_single_supplier:
        single_sup_constraint = solver.Constraint(1.0, 1.0, "SingleSupplierConstraint")
        for i in range(N):
            single_sup_constraint.SetCoefficient(y[i], 1.0)

    # 4. Budget Constraint (if specified)
    # sum(unit_price * x[i] + fixed_freight * y[i]) <= budget_limit
    if budget_limit is not None and budget_limit > 0:
        budget_constraint = solver.Constraint(0.0, budget_limit, "BudgetConstraint")
        for i, s in enumerate(eligible_candidates):
            u_cost = float(s.get("unit_landed_cost", 0.0))
            f_cost = float(s.get("fixed_freight", 0.0))
            budget_constraint.SetCoefficient(x[i], u_cost)
            budget_constraint.SetCoefficient(y[i], f_cost)

    # Objective: Minimize total purchasing cost
    objective = solver.Objective()
    for i, s in enumerate(eligible_candidates):
        u_cost = float(s.get("unit_landed_cost", 0.0))
        f_cost = float(s.get("fixed_freight", 0.0))
        objective.SetCoefficient(x[i], u_cost)
        objective.SetCoefficient(y[i], f_cost)
    objective.SetMinimization()

    solver_status = solver.Solve()

    if solver_status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        # Identify bottleneck
        reasons = []
        if budget_limit:
            reasons.append(f"Purchasing cost with compliant MOQs exceeds specified budget cap of ₹{budget_limit:,.2f}.")
        reasons.append("Conflicting MOQ and capacity constraints between eligible vendors.")
        return {
            "status": "INFEASIBLE",
            "message": "Optimization model cannot satisfy all purchasing constraints simultaneously.",
            "allocations": [],
            "total_cost": 0.0,
            "reasons": reasons
        }

    # Extract solution
    allocations = []
    total_cost = 0.0
    for i, s in enumerate(eligible_candidates):
        alloc_qty = x[i].solution_value()
        is_active = y[i].solution_value() > 0.5
        if is_active and alloc_qty > 0.01:
            u_cost = float(s.get("unit_landed_cost", 0.0))
            f_cost = float(s.get("fixed_freight", 0.0))
            sup_cost = (alloc_qty * u_cost) + f_cost
            total_cost += sup_cost

            allocations.append({
                "supplier_id": s.get("supplier_id"),
                "supplier_name": s.get("supplier_name"),
                "allocated_quantity": round(alloc_qty, 2),
                "unit_landed_cost": u_cost,
                "fixed_freight": f_cost,
                "supplier_subtotal": round(sup_cost, 2),
                "moq": s.get("moq", 1.0),
                "capacity": s.get("capacity"),
                "lead_time_days": s.get("lead_time_days", 7),
                "quality_rating": s.get("quality_rating", 4.0),
            })

    total_cost = round(total_cost, 2)
    budget_utilized_pct = round((total_cost / budget_limit) * 100.0, 1) if budget_limit else None

    # Formulate explainable reasoning
    explanation_points = []
    if len(allocations) == 1:
        s0 = allocations[0]
        explanation_points.append(
            f"100% of the volume ({s0['allocated_quantity']:.1f} units) is awarded to {s0['supplier_name']} "
            f"as the single most cost-effective option respecting MOQ and capacity."
        )
    else:
        explanation_points.append(
            f"Volume is split across {len(allocations)} suppliers to satisfy capacity limits and minimize overall landed cost."
        )
        for a in allocations:
            explanation_points.append(f"- {a['supplier_name']}: {a['allocated_quantity']:.1f} units @ ₹{a['unit_landed_cost']:.2f}")

    if budget_limit:
        explanation_points.append(
            f"Total expenditure of ₹{total_cost:,.2f} utilizes {budget_utilized_pct}% of the ₹{budget_limit:,.2f} budget."
        )

    return {
        "status": "OPTIMAL",
        "required_quantity": required_quantity,
        "total_cost": total_cost,
        "budget_limit": budget_limit,
        "budget_utilized_pct": budget_utilized_pct,
        "allocated_suppliers_count": len(allocations),
        "allocations": allocations,
        "explanation": "\n".join(explanation_points),
        "constraints_satisfied": [
            f"Demand of {required_quantity} units 100% fulfilled.",
            "All vendor Minimum Order Quantities (MOQ) respected.",
            "No supplier capacity exceeded.",
            *(["Budget ceiling respected."] if budget_limit else []),
            *(["Delivery lead time bounds respected."] if max_lead_time_days else []),
        ]
    }

def _greedy_fallback_allocation(
    required_quantity: float,
    candidates: List[Dict[str, Any]],
    budget_limit: Optional[float]
) -> Dict[str, Any]:
    """Deterministic sorting fallback when OR-Tools native solver is unavailable."""
    # Sort by unit landed cost ascending
    sorted_candidates = sorted(candidates, key=lambda c: c.get("unit_landed_cost", float("inf")))
    remaining = required_quantity
    allocations = []
    total_cost = 0.0

    for s in sorted_candidates:
        if remaining <= 0:
            break
        cap = float(s.get("capacity", remaining))
        moq = float(s.get("moq", 1.0))
        if cap < moq:
            continue
        take = min(remaining, cap)
        if take < moq:
            take = moq # fulfill MOQ

        u_cost = float(s.get("unit_landed_cost", 0.0))
        f_cost = float(s.get("fixed_freight", 0.0))
        subtotal = (take * u_cost) + f_cost
        total_cost += subtotal
        remaining -= min(remaining, take)

        allocations.append({
            "supplier_id": s.get("supplier_id"),
            "supplier_name": s.get("supplier_name"),
            "allocated_quantity": round(take, 2),
            "unit_landed_cost": u_cost,
            "fixed_freight": f_cost,
            "supplier_subtotal": round(subtotal, 2),
            "moq": moq,
            "capacity": cap,
            "lead_time_days": s.get("lead_time_days", 7),
        })

    return {
        "status": "OPTIMAL" if remaining <= 0 else "FEASIBLE",
        "required_quantity": required_quantity,
        "total_cost": round(total_cost, 2),
        "allocations": allocations,
        "explanation": "Greedy cost-prioritization allocation respecting supplier capacities.",
        "constraints_satisfied": ["Quantity allocated by ascending unit landed cost."]
    }

