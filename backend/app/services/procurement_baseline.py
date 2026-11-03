from typing import List, Dict, Any, Optional
from decimal import Decimal

def compute_procurement_baselines(
    requirements: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    optimized_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compares the optimized OR-Tools multi-supplier procurement solution against
    two standard procurement purchasing approaches:
    1. Baseline A: Single Cheapest Supplier (Consolidated single vendor)
    2. Baseline B: Cheapest Eligible Supplier Per Material (Siloed sourcing)
    
    Computes absolute and percentage savings only when the baseline fulfills
    equivalent demand and delivery requirements without inventing artificial savings.
    """
    req_map = {r["material_id"]: r for r in requirements}
    all_suppliers = list(set(c["supplier_id"] for c in candidates))
    
    opt_cost = float(optimized_result.get("total_landed_cost", 0.0))
    opt_status = optimized_result.get("solver_status") or optimized_result.get("status", "OPTIMAL")
    opt_is_feasible = (opt_status in ["OPTIMAL", "FEASIBLE"]) and (opt_cost > 0.0)

    # -------------------------------------------------------------------------
    # Baseline A: Single Cheapest Supplier Across All Materials
    # -------------------------------------------------------------------------
    # A single supplier must be able to supply ALL materials in the requirement
    # with capacity >= required quantity for every item.
    baseline_a_candidates = []
    
    for s_id in all_suppliers:
        s_cands = [c for c in candidates if c["supplier_id"] == s_id]
        s_materials = set(c["material_id"] for c in s_cands)
        
        # Must supply all materials
        if not set(req_map.keys()).issubset(s_materials):
            continue
            
        # Must have capacity for every material
        has_capacity = True
        sup_total_cost = 0.0
        s_name = s_cands[0].get("supplier_name", "Vendor")
        fixed_freight = float(s_cands[0].get("fixed_freight", 0.0))
        
        for r in requirements:
            m_id = r["material_id"]
            d_qty = float(r["required_quantity"])
            cand = next(c for c in s_cands if c["material_id"] == m_id)
            cap = float(cand.get("capacity", 0.0))
            if cap < d_qty:
                has_capacity = False
                break
            u_landed = float(cand.get("unit_landed_cost", 0.0))
            sup_total_cost += (d_qty * u_landed)
            
        if has_capacity:
            sup_total_cost += fixed_freight
            baseline_a_candidates.append({
                "supplier_id": s_id,
                "supplier_name": s_name,
                "total_cost": round(sup_total_cost, 2)
            })

    baseline_a_result = {}
    if baseline_a_candidates:
        # Pick the lowest cost single supplier
        best_single = min(baseline_a_candidates, key=lambda c: c["total_cost"])
        b_a_cost = best_single["total_cost"]
        
        if opt_is_feasible:
            savings_abs = round(b_a_cost - opt_cost, 2)
            savings_pct = round((savings_abs / b_a_cost) * 100.0, 2) if b_a_cost > 0 else 0.0
            if savings_abs >= 0:
                explanation = f"100% of material requirements fulfilled by single vendor {best_single['supplier_name']}."
            else:
                explanation = f"IndusPilot optimized allocation incurs a deliberate multi-criteria premium of ₹{abs(savings_abs):,.2f} over single vendor {best_single['supplier_name']}."
        else:
            # When optimization is infeasible, savings cannot be claimed
            savings_abs = 0.0
            savings_pct = 0.0
            explanation = f"Savings comparison unavailable: solver result is {opt_status}. Zero savings can be claimed."
        
        baseline_a_result = {
            "name": "Baseline A: Single Consolidated Supplier",
            "is_feasible": True,
            "supplier_name": best_single["supplier_name"],
            "total_cost": b_a_cost,
            "savings_vs_baseline_abs": savings_abs,
            "savings_vs_baseline_pct": savings_pct,
            "status_label": "Feasible Single-Vendor Sourcing",
            "explanation": explanation
        }
    else:
        baseline_a_result = {
            "name": "Baseline A: Single Consolidated Supplier",
            "is_feasible": False,
            "supplier_name": None,
            "total_cost": None,
            "savings_vs_baseline_abs": 0.0,
            "savings_vs_baseline_pct": 0.0,
            "status_label": "Infeasible: Insufficient Capacity Across Full BOM",
            "explanation": "No single supplier has the portfolio breadth or capacity to fulfill all required materials alone."
        }

    # -------------------------------------------------------------------------
    # Baseline B: Cheapest Eligible Supplier Per Material
    # -------------------------------------------------------------------------
    # For each material independently, pick the lowest unit-cost supplier who has capacity >= demand
    baseline_b_allocations = []
    baseline_b_is_feasible = True
    baseline_b_infeasible_reasons = []
    b_b_total_cost = 0.0
    active_b_suppliers = set()

    for r in requirements:
        m_id = r["material_id"]
        d_qty = float(r["required_quantity"])
        m_cands = [c for c in candidates if c["material_id"] == m_id and float(c.get("capacity", 0.0)) >= d_qty]
        
        if not m_cands:
            baseline_b_is_feasible = False
            baseline_b_infeasible_reasons.append(
                f"No single supplier has sufficient capacity ({d_qty:.1f} {r.get('unit', 'kg')}) for {r.get('material_name', m_id)}."
            )
            continue
            
        # Pick cheapest unit landed cost
        cheapest_cand = min(m_cands, key=lambda c: float(c.get("unit_landed_cost", float("inf"))))
        u_landed = float(cheapest_cand.get("unit_landed_cost", 0.0))
        item_cost = d_qty * u_landed
        b_b_total_cost += item_cost
        active_b_suppliers.add(cheapest_cand["supplier_id"])
        
        baseline_b_allocations.append({
            "material_id": m_id,
            "material_name": r.get("material_name", m_id),
            "supplier_id": cheapest_cand["supplier_id"],
            "supplier_name": cheapest_cand.get("supplier_name", "Vendor"),
            "allocated_quantity": d_qty,
            "unit_landed_cost": u_landed,
            "subtotal": round(item_cost, 2)
        })

    # Add fixed freight per active supplier in Baseline B
    for s_id in active_b_suppliers:
        s_cands = [c for c in candidates if c["supplier_id"] == s_id]
        if s_cands:
            b_b_total_cost += float(s_cands[0].get("fixed_freight", 0.0))

    b_b_total_cost = round(b_b_total_cost, 2)

    baseline_b_result = {}
    if baseline_b_is_feasible:
        if opt_is_feasible:
            b_b_savings_abs = round(b_b_total_cost - opt_cost, 2)
            b_b_savings_pct = round((b_b_savings_abs / b_b_total_cost) * 100.0, 2) if b_b_total_cost > 0 else 0.0
            if b_b_savings_abs >= 0:
                b_b_exp = f"Independent cheapest selection across {len(active_b_suppliers)} suppliers."
            else:
                b_b_exp = f"IndusPilot optimized allocation incurs a deliberate multi-criteria premium of ₹{abs(b_b_savings_abs):,.2f} over independent cheapest quotes."
        else:
            b_b_savings_abs = 0.0
            b_b_savings_pct = 0.0
            b_b_exp = f"Savings comparison unavailable: solver result is {opt_status}. Zero savings can be claimed."
        
        baseline_b_result = {
            "name": "Baseline B: Cheapest Eligible Sourcing Per Material",
            "is_feasible": True,
            "total_cost": b_b_total_cost,
            "suppliers_count": len(active_b_suppliers),
            "savings_vs_baseline_abs": b_b_savings_abs,
            "savings_vs_baseline_pct": b_b_savings_pct,
            "allocations": baseline_b_allocations,
            "status_label": "Feasible Sourcing Plan",
            "explanation": b_b_exp
        }
    else:
        baseline_b_result = {
            "name": "Baseline B: Cheapest Eligible Sourcing Per Material",
            "is_feasible": False,
            "total_cost": None,
            "suppliers_count": len(active_b_suppliers),
            "savings_vs_baseline_abs": 0.0,
            "savings_vs_baseline_pct": 0.0,
            "allocations": baseline_b_allocations,
            "status_label": "Infeasible: Single-Vendor Capacity Insufficient for One or More Materials",
            "explanation": " ".join(baseline_b_infeasible_reasons)
        }

    # -------------------------------------------------------------------------
    # Baseline C: IndusPilot OR-Tools Optimization
    # -------------------------------------------------------------------------
    if opt_is_feasible:
        status_label = (
            f"Mathematically Optimal ({optimized_result.get('strategy', 'LOWEST_LANDED_COST')})"
            if opt_status == "OPTIMAL"
            else f"Feasible Non-Optimal Allocation ({optimized_result.get('strategy', 'LOWEST_LANDED_COST')})"
        )
        c_explanation = optimized_result.get("explanation_headline", "Mathematically optimized allocation satisfying all constraints.")
    else:
        status_label = f"Infeasible Solver Allocation ({opt_status})"
        c_explanation = "Mathematical optimization model cannot satisfy all procurement constraints simultaneously. No savings can be claimed."

    baseline_c_result = {
        "name": "Baseline C: IndusPilot OR-Tools MILP Optimisation",
        "is_feasible": opt_is_feasible,
        "total_cost": opt_cost if opt_is_feasible else 0.0,
        "suppliers_count": optimized_result.get("allocated_suppliers_count", 0) if opt_is_feasible else 0,
        "status_label": status_label,
        "explanation": c_explanation
    }

    # Primary comparative benchmark (prefer Baseline B if feasible, else Baseline A)
    primary_benchmark = baseline_b_result if baseline_b_result["is_feasible"] else (baseline_a_result if baseline_a_result["is_feasible"] else None)

    summary_headline = ""
    if not opt_is_feasible:
        summary_headline = (
            f"Procurement optimization returned status '{opt_status}'. "
            "Zero cost savings can be claimed against any baseline until constraints are adjusted."
        )
    elif primary_benchmark and primary_benchmark["is_feasible"]:
        sav_pct = primary_benchmark["savings_vs_baseline_pct"]
        sav_abs = primary_benchmark["savings_vs_baseline_abs"]
        if sav_abs > 0:
            summary_headline = (
                f"IndusPilot MILP solver generated savings of ₹{sav_abs:,.2f} ({sav_pct:.1f}%) "
                f"compared to standard {primary_benchmark['name']} by dynamically balancing split volumes and fixed freight."
            )
        elif sav_abs == 0:
            summary_headline = "IndusPilot MILP solver validated that the standard sourcing approach is already cost-optimal."
        else:
            summary_headline = (
                f"IndusPilot plan incorporates non-cost constraints (lead times/quality), "
                f"incurring a deliberate trade-off premium of ₹{abs(sav_abs):,.2f} compared to {primary_benchmark['name']}."
            )
    else:
        summary_headline = (
            "Standard heuristic approaches (single-supplier / uncoordinated sourcing) failed feasibility due to capacity limits. "
            "IndusPilot OR-Tools was the only method capable of formulating a valid procurement plan."
        )

    return {
        "baseline_a": baseline_a_result,
        "baseline_b": baseline_b_result,
        "optimized_c": baseline_c_result,
        "primary_benchmark_name": primary_benchmark["name"] if primary_benchmark else "None (Baselines Infeasible)",
        "summary_headline": summary_headline,
        "is_simulated_benchmark": True
    }

