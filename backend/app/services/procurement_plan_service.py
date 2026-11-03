from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.entities import (
    ProcurementPlan, ProcurementPlanItem, ProcurementPlanAllocation,
    ProductionJob, Material, Supplier, SupplierQuotation, QuotationItem,
    SupplierMaterial, PurchaseRequisition, ApprovalRequest, AuditLog
)
from app.calculations.landed_cost import calculate_landed_cost
from app.services.unit_conversion import convert_unit
from app.optimizers.multi_material_optimizer import solve_multi_material_procurement
from app.services.procurement_baseline import compute_procurement_baselines
from app.calculations.inventory_netting import calculate_net_procurement_requirement
from app.calculations.bom_engine import explode_bom


def generate_procurement_candidates(
    db: Session,
    org_id: str,
    requirements: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Retrieves and filters suitable supplier quotation records from the database
    for the requested materials. Enforces mandatory eligibility rules:
    - Excludes QUARANTINED quotations
    - Excludes expired quotations
    - Excludes items with unit_price <= 0
    - Computes full deterministic landed cost via the Phase 4 engine
    """
    candidates = []
    now = datetime.utcnow()

    for r in requirements:
        m_id = r["material_id"]
        req_qty = float(r["required_quantity"])
        req_unit = r.get("unit", "kg")
        mat = db.query(Material).filter(Material.id == m_id, Material.organization_id == org_id).first()
        if not mat:
            continue

        # Find verified quotations with items matching this material
        quote_items = db.query(QuotationItem).join(SupplierQuotation).filter(
            SupplierQuotation.organization_id == org_id,
            SupplierQuotation.status.in_(["VERIFIED", "ARCHIVED", "READY_FOR_REVIEW"]),
            QuotationItem.is_quarantined == False,
            QuotationItem.unit_price > 0,
            or_(
                QuotationItem.material_id == m_id,
                QuotationItem.material_name_raw.ilike(f"%{mat.code}%"),
                QuotationItem.material_name_raw.ilike(f"%{mat.name}%")
            )
        ).all()

        for qi in quote_items:
            q = qi.quotation
            sup = q.supplier if q else None
            if not sup:
                continue

            # Check expiration
            if q.valid_until and q.valid_until < now:
                # Expired quotation: skip from active candidate pool
                continue

            # Unit conversion if quotation item unit differs from requirement unit
            q_unit = qi.unit or req_unit
            multiplier = 1.0
            if q_unit.lower() != req_unit.lower():
                try:
                    # Convert 1.0 q_unit to req_unit
                    conv_dec = convert_unit(1.0, q_unit, req_unit)
                    multiplier = float(conv_dec)
                except Exception:
                    # Incompatible unit dimension: skip
                    continue

            # Normalized unit price in requirement unit
            effective_unit_price = float(qi.unit_price) / max(0.0001, multiplier)

            # Calculate deterministic landed cost for the required batch slice
            calc_slice_qty = max(1.0, min(req_qty, float(qi.quantity or req_qty)))
            freight_share = float(q.freight_cost or 0.0)
            
            try:
                landed = calculate_landed_cost(
                    unit_price=effective_unit_price,
                    quantity=calc_slice_qty,
                    tax_pct=float(qi.tax_pct or 18.0),
                    is_tax_inclusive=q.is_tax_inclusive,
                    freight_total=0.0, # Freight treated as order-level binary fee
                    discount_pct=float(qi.discount_pct or 0.0)
                )
                u_landed = float(landed["effective_unit_landed_cost"])
            except Exception:
                u_landed = effective_unit_price * (1.0 + (float(qi.tax_pct or 18.0) / 100.0))

            # Supplier capacity
            sm = db.query(SupplierMaterial).filter(
                SupplierMaterial.supplier_id == sup.id,
                or_(
                    SupplierMaterial.material_name.ilike(f"%{mat.code}%"),
                    SupplierMaterial.material_name.ilike(f"%{mat.name}%")
                )
            ).first()

            cap = float(sm.capacity_monthly_units) if sm and sm.capacity_monthly_units else (
                float(sup.capacity_monthly_tons * 1000.0) if sup.capacity_monthly_tons else 15000.0
            )

            # Packaging multiple
            pkg_mult = 1.0
            if "fastener" in mat.category.lower() or "nos" in req_unit.lower():
                pkg_mult = 100.0 if req_qty >= 500 else 1.0

            candidates.append({
                "material_id": m_id,
                "material_code": mat.code,
                "material_name": mat.name,
                "supplier_id": sup.id,
                "supplier_name": sup.name,
                "quotation_id": q.id,
                "quotation_number": q.quotation_number,
                "unit_price": effective_unit_price,
                "unit_landed_cost": u_landed,
                "fixed_freight": freight_share,
                "capacity": cap,
                "moq": float(qi.moq or 1.0),
                "packaging_multiple": pkg_mult,
                "lead_time_days": int(qi.lead_time_days or sup.lead_time_days or 7),
                "quality_rating": float(sup.quality_rating or 4.0),
                "on_time_delivery_pct": float(sup.on_time_delivery_pct or 90.0),
                "reliability_score": float(sup.reliability_score or 88.0)
            })

    return candidates


def create_and_optimize_procurement_plan(
    db: Session,
    org_id: str,
    requirements: List[Dict[str, Any]],
    strategy: str = "LOWEST_LANDED_COST",
    production_job_id: Optional[str] = None,
    budget_limit: Optional[float] = None,
    max_suppliers_per_material: int = 3,
    allow_split_purchasing: bool = True,
    global_max_lead_time_days: Optional[int] = None,
    min_quality_rating: Optional[float] = None,
    max_overbuy_pct: float = 10.0
) -> Dict[str, Any]:
    """
    Creates an immutable ProcurementPlan database entity, executes Google OR-Tools
    multi-material optimization, computes comparative baselines, and persists
    supplier allocations transactionally.
    """
    # 1. Sequential Plan Number (Guaranteed Unique)
    existing_plans = {p[0] for p in db.query(ProcurementPlan.plan_number).all() if p[0]}
    count = db.query(ProcurementPlan).filter(ProcurementPlan.organization_id == org_id).count() + 1
    plan_no = f"PLAN-2026-{count:04d}"
    while plan_no in existing_plans:
        count += 1
        plan_no = f"PLAN-2026-{count:04d}"

    # 2. Candidate Generation
    candidates = generate_procurement_candidates(db, org_id, requirements)

    # 3. Create ProcurementPlan record in DRAFT
    plan = ProcurementPlan(
        organization_id=org_id,
        plan_number=plan_no,
        production_job_id=production_job_id,
        strategy=strategy,
        status="OPTIMIZING",
        budget_limit=budget_limit,
        max_suppliers_per_material=max_suppliers_per_material,
        allow_split_purchasing=allow_split_purchasing,
        max_overbuy_pct=max_overbuy_pct,
        min_quality_rating=min_quality_rating or 3.5,
        required_by_date=datetime.utcnow() + timedelta(days=global_max_lead_time_days or 14),
        total_units_required=sum(float(r["required_quantity"]) for r in requirements),
        input_snapshot_json={
            "requirements": requirements,
            "candidates_count": len(candidates),
            "created_at": datetime.utcnow().isoformat()
        }
    )
    db.add(plan)
    db.flush()

    # 4. Create Plan Items
    for r in requirements:
        db.add(ProcurementPlanItem(
            procurement_plan_id=plan.id,
            material_id=r["material_id"],
            required_quantity=float(r["required_quantity"]),
            unit=r.get("unit", "kg"),
            delivery_deadline=datetime.utcnow() + timedelta(days=r.get("max_lead_time_days") or 14)
        ))
    db.flush()

    # 5. Execute Mathematical Optimization
    opt_solution = solve_multi_material_procurement(
        requirements=requirements,
        candidates=candidates,
        strategy=strategy,
        global_budget_limit=budget_limit,
        max_suppliers_per_material=max_suppliers_per_material,
        allow_split_purchasing=allow_split_purchasing,
        global_max_lead_time_days=global_max_lead_time_days,
        min_quality_rating=min_quality_rating,
        max_overbuy_pct=max_overbuy_pct
    )

    # 6. Baseline Sourcing Comparison
    baselines = compute_procurement_baselines(requirements, candidates, opt_solution)

    # 7. Persist Allocations & Status
    plan.solver_status = opt_solution.get("solver_status", "OPTIMAL")
    plan.total_landed_cost = float(opt_solution.get("total_landed_cost", 0.0))
    plan.budget_utilized_pct = opt_solution.get("budget_utilized_pct")
    plan.total_units_allocated = float(opt_solution.get("total_units_allocated", 0.0))
    plan.excess_units = float(opt_solution.get("excess_units", 0.0))
    plan.baseline_comparison_json = baselines
    plan.explanation_headline = opt_solution.get("explanation_headline")
    plan.explanation_detail = opt_solution.get("explanation_detail")

    if opt_solution["status"] == "INFEASIBLE":
        plan.status = "NEEDS_REVIEW"
    else:
        plan.status = "OPTIMIZED"

        # Record Allocations
        for a in opt_solution.get("allocations", []):
            db.add(ProcurementPlanAllocation(
                procurement_plan_id=plan.id,
                material_id=a["material_id"],
                supplier_id=a["supplier_id"],
                quotation_id=a.get("quotation_id"),
                allocated_quantity=float(a["allocated_quantity"]),
                unit=a["unit"],
                unit_landed_cost=float(a["unit_landed_cost"]),
                subtotal_cost=float(a["subtotal_cost"]),
                fixed_freight_allocated=float(a.get("fixed_freight_allocated", 0.0)),
                moq=float(a.get("moq", 1.0)),
                moq_satisfied=a.get("moq_satisfied", True),
                package_count=a.get("package_count"),
                lead_time_days=int(a.get("lead_time_days", 7)),
                delivery_date=datetime.utcnow() + timedelta(days=int(a.get("lead_time_days", 7))),
                quality_rating=float(a.get("quality_rating", 4.0)),
                supplier_risk_score=round(100.0 - float(a.get("reliability_score", 90.0)), 1)
            ))

    db.commit()

    return {
        "plan_id": plan.id,
        "plan_number": plan.plan_number,
        "status": plan.status,
        "solver_status": plan.solver_status,
        "strategy": plan.strategy,
        "total_landed_cost": plan.total_landed_cost,
        "budget_limit": plan.budget_limit,
        "budget_utilized_pct": plan.budget_utilized_pct,
        "total_units_required": plan.total_units_required,
        "total_units_allocated": plan.total_units_allocated,
        "excess_units": plan.excess_units,
        "allocated_suppliers_count": opt_solution.get("allocated_suppliers_count", 0),
        "allocations": opt_solution.get("allocations", []),
        "explanation_headline": plan.explanation_headline,
        "explanation_detail": plan.explanation_detail,
        "baseline_comparison": baselines,
        "reasons": opt_solution.get("reasons", []),
        "diagnostics": opt_solution.get("diagnostics", []),
        "constraints_satisfied": opt_solution.get("constraints_satisfied", [])
    }


def request_plan_approval(
    db: Session,
    org_id: str,
    plan_id: str,
    requested_by: str = "Procurement Lead"
) -> Dict[str, Any]:
    """Submits an optimized procurement plan for formal managerial approval."""
    plan = db.query(ProcurementPlan).filter(
        ProcurementPlan.id == plan_id,
        ProcurementPlan.organization_id == org_id
    ).first()
    if not plan:
        raise ValueError("Procurement plan not found.")

    if plan.status not in ["OPTIMIZED", "NEEDS_REVIEW"]:
        raise ValueError(f"Cannot request approval for plan in status '{plan.status}'.")

    plan.status = "AWAITING_APPROVAL"
    plan.approval_status = "PENDING"

    # Create formal ApprovalRequest record
    appr = ApprovalRequest(
        organization_id=org_id,
        request_type="PROCUREMENT_PLAN",
        entity_id=plan.id,
        requested_by=requested_by,
        details_json={
            "plan_number": plan.plan_number,
            "strategy": plan.strategy,
            "total_landed_cost": plan.total_landed_cost,
            "budget_limit": plan.budget_limit,
            "allocations_count": len(plan.allocations)
        },
        status="PENDING"
    )
    db.add(appr)
    db.commit()

    return {
        "plan_id": plan.id,
        "plan_number": plan.plan_number,
        "status": plan.status,
        "approval_id": appr.id
    }


def approve_procurement_plan(
    db: Session,
    org_id: str,
    plan_id: str,
    approved_by: str = "Chief Financial Officer"
) -> Dict[str, Any]:
    """Approves an optimized procurement plan, unlocking purchase order generation."""
    plan = db.query(ProcurementPlan).filter(
        ProcurementPlan.id == plan_id,
        ProcurementPlan.organization_id == org_id
    ).first()
    if not plan:
        raise ValueError("Procurement plan not found.")

    plan.status = "APPROVED"
    plan.approval_status = "APPROVED"
    plan.approved_by = approved_by
    plan.approved_at = datetime.utcnow()

    # Update associated ApprovalRequest if exists
    appr = db.query(ApprovalRequest).filter(
        ApprovalRequest.entity_id == plan.id,
        ApprovalRequest.request_type == "PROCUREMENT_PLAN"
    ).first()
    if appr:
        appr.status = "APPROVED"
        appr.decided_at = datetime.utcnow()

    db.commit()

    return {
        "plan_id": plan.id,
        "plan_number": plan.plan_number,
        "status": plan.status,
        "approved_by": plan.approved_by,
        "approved_at": plan.approved_at.isoformat()
    }


def reject_procurement_plan(
    db: Session,
    org_id: str,
    plan_id: str,
    rejected_by: str = "Chief Financial Officer",
    reason: str = "Budget constraint re-evaluation required"
) -> Dict[str, Any]:
    """Rejects an optimized procurement plan."""
    plan = db.query(ProcurementPlan).filter(
        ProcurementPlan.id == plan_id,
        ProcurementPlan.organization_id == org_id
    ).first()
    if not plan:
        raise ValueError("Procurement plan not found.")

    plan.status = "REJECTED"
    plan.approval_status = "REJECTED"
    plan.rejection_reason = reason

    appr = db.query(ApprovalRequest).filter(
        ApprovalRequest.entity_id == plan.id,
        ApprovalRequest.request_type == "PROCUREMENT_PLAN"
    ).first()
    if appr:
        appr.status = "REJECTED"
        appr.decision_reason = reason
        appr.decided_at = datetime.utcnow()

    db.commit()

    return {
        "plan_id": plan.id,
        "plan_number": plan.plan_number,
        "status": plan.status,
        "rejection_reason": reason
    }


def generate_purchase_requisitions_from_plan(
    db: Session,
    org_id: str,
    plan_id: str
) -> Dict[str, Any]:
    """
    Transforms approved supplier allocations into formal PurchaseRequisition records.
    """
    plan = db.query(ProcurementPlan).filter(
        ProcurementPlan.id == plan_id,
        ProcurementPlan.organization_id == org_id
    ).first()
    if not plan:
        raise ValueError("Procurement plan not found.")

    if plan.status != "APPROVED":
        raise ValueError(f"Cannot generate requisitions from unapproved plan (current status: '{plan.status}').")

    created_reqs = []
    for alloc in plan.allocations:
        seq = db.query(PurchaseRequisition).filter(PurchaseRequisition.organization_id == org_id).count() + 1
        req_no = f"REQ-2026-{seq:04d}"

        pr = PurchaseRequisition(
            organization_id=org_id,
            requisition_number=req_no,
            material_id=alloc.material_id,
            required_quantity=alloc.allocated_quantity,
            unit=alloc.unit,
            required_by_date=alloc.delivery_date or (datetime.utcnow() + timedelta(days=alloc.lead_time_days)),
            reason=f"Generated from Approved Procurement Plan {plan.plan_number}",
            selected_supplier_id=alloc.supplier_id,
            selected_quotation_id=alloc.quotation_id,
            estimated_total_cost=alloc.subtotal_cost,
            status="APPROVED"
        )
        db.add(pr)
        db.flush()
        created_reqs.append({
            "requisition_id": pr.id,
            "requisition_number": pr.requisition_number,
            "material_id": pr.material_id,
            "supplier_id": pr.selected_supplier_id,
            "quantity": pr.required_quantity,
            "estimated_cost": pr.estimated_total_cost
        })

    plan.status = "ORDERED"
    db.commit()

    return {
        "plan_id": plan.id,
        "plan_number": plan.plan_number,
        "requisitions_count": len(created_reqs),
        "requisitions": created_reqs
    }
