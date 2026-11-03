from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_org_id
from app.models.entities import (
    PurchaseRequisition, Material, Supplier, SupplierQuotation, AuditLog,
    ProcurementPlan, ProcurementPlanItem, ProcurementPlanAllocation, ProductionJob,
    BillOfMaterials, Inventory
)
from app.schemas.domain import (
    PurchaseRequisitionCreate,
    ProcurementPlanCreateRequest,
    ProcurementPlanFromJobRequest,
    ProcurementPlanApprovalRequest
)
from app.services.procurement_plan_service import (
    create_and_optimize_procurement_plan,
    request_plan_approval,
    approve_procurement_plan,
    reject_procurement_plan,
    generate_purchase_requisitions_from_plan,
    generate_procurement_candidates
)
from app.optimizers.multi_material_optimizer import solve_multi_material_procurement
from app.services.procurement_baseline import compute_procurement_baselines
from app.calculations.bom_engine import explode_bom

router = APIRouter()


# -----------------------------------------------------------------------------
# 1. Procurement Strategies Catalog
# -----------------------------------------------------------------------------
@router.get("/strategies")
def list_procurement_strategies():
    """Lists the 5 supported mathematical procurement optimization strategies."""
    return [
        {
            "id": "LOWEST_LANDED_COST",
            "name": "Lowest Landed Cost",
            "description": "Pure economic optimization minimizing total landed expenditure (material + freight + taxes).",
            "recommended_for": "Standard commodity metals and high-budget purchasing."
        },
        {
            "id": "BALANCED",
            "name": "Balanced (Cost + Quality + Reliability)",
            "description": "Multi-attribute optimization penalizing lower delivery reliability and rewarding verified quality certifications.",
            "recommended_for": "General production runs requiring dependable supplier fulfillment."
        },
        {
            "id": "FASTEST_DELIVERY",
            "name": "Fastest Feasible Procurement",
            "description": "Prioritizes suppliers with the shortest lead times to prevent assembly line stoppages.",
            "recommended_for": "Urgent breakdown repair and rush customer orders."
        },
        {
            "id": "QUALITY_FIRST",
            "name": "Quality-First Sourcing",
            "description": "Prioritizes suppliers with high verified quality inspection ratings (4.5+ / 5.0).",
            "recommended_for": "High-precision aerospace, marine, and mission-critical assemblies."
        },
        {
            "id": "BUDGET_CONSTRAINED",
            "name": "Budget-Constrained Sourcing",
            "description": "Finds the mathematically feasible sourcing plan strictly within a fixed capital ceiling.",
            "recommended_for": "Cashflow-constrained operations and fixed-price customer contracts."
        }
    ]


# -----------------------------------------------------------------------------
# 2. Multi-Material Procurement Plans
# -----------------------------------------------------------------------------
@router.get("/plans")
def list_procurement_plans(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Lists all formal procurement plans in the organization."""
    q = db.query(ProcurementPlan).filter(ProcurementPlan.organization_id == org_id)
    if status:
        q = q.filter(ProcurementPlan.status == status)
    plans = q.order_by(ProcurementPlan.created_at.desc()).all()

    return [
        {
            "id": p.id,
            "plan_number": p.plan_number,
            "production_job_id": p.production_job_id,
            "strategy": p.strategy,
            "status": p.status,
            "solver_status": p.solver_status,
            "total_landed_cost": p.total_landed_cost,
            "budget_limit": p.budget_limit,
            "budget_utilized_pct": p.budget_utilized_pct,
            "total_units_required": p.total_units_required,
            "total_units_allocated": p.total_units_allocated,
            "excess_units": p.excess_units,
            "items_count": len(p.items),
            "allocations_count": len(p.allocations),
            "approval_status": p.approval_status,
            "approved_by": p.approved_by,
            "approved_at": p.approved_at.isoformat() if p.approved_at else None,
            "explanation_headline": p.explanation_headline,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in plans
    ]


@router.post("/plans")
def create_procurement_plan(
    payload: ProcurementPlanCreateRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Creates and mathematically optimizes a multi-material procurement plan
    using Google OR-Tools MILP solver. Persists plan, items, and allocations.
    """
    req_dicts = [r.model_dump() for r in payload.requirements]
    try:
        res = create_and_optimize_procurement_plan(
            db=db,
            org_id=org_id,
            requirements=req_dicts,
            strategy=payload.strategy,
            production_job_id=payload.production_job_id,
            budget_limit=payload.budget_limit,
            max_suppliers_per_material=payload.max_suppliers_per_material,
            allow_split_purchasing=payload.allow_split_purchasing,
            global_max_lead_time_days=payload.global_max_lead_time_days,
            min_quality_rating=payload.min_quality_rating,
            max_overbuy_pct=payload.max_overbuy_pct
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Procurement planning failed: {str(e)}")


@router.post("/plans/from-job")
def create_procurement_plan_from_job(
    payload: ProcurementPlanFromJobRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Automatically creates a procurement plan by extracting raw material shortages
    from an existing production job's active BOM explosion and inventory netting.
    """
    job = db.query(ProductionJob).filter(
        ProductionJob.id == payload.job_id,
        ProductionJob.organization_id == org_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found.")

    bom = job.bom or db.query(BillOfMaterials).filter(
        BillOfMaterials.product_id == job.product_id,
        BillOfMaterials.is_active == True
    ).first()
    if not bom:
        raise HTTPException(status_code=400, detail="Job has no associated active Bill of Materials.")

    # Explode BOM and calculate requirements
    requirements = []
    for item in bom.items:
        net_qty = float(item.quantity_per_unit) * float(job.production_quantity)
        scrap = float(item.wastage_pct or 0.0)
        gross_qty = net_qty * (1.0 + (scrap / 100.0))

        # Check inventory
        inv = db.query(Inventory).filter(
            Inventory.organization_id == org_id,
            Inventory.material_id == item.material_id
        ).first()

        avail_stock = max(0.0, float(inv.current_stock - inv.reserved_stock)) if inv else 0.0
        shortage = max(0.0, gross_qty - avail_stock)

        # Only require purchasing if there is an unreserved shortage
        if shortage > 0:
            mat = item.material
            requirements.append({
                "material_id": item.material_id,
                "material_code": mat.code if mat else "SKU",
                "material_name": mat.name if mat else "Material",
                "required_quantity": round(shortage, 2),
                "unit": item.unit or "kg",
                "max_lead_time_days": payload.global_max_lead_time_days or 14
            })

    if not requirements:
        return {
            "status": "COMPLETED",
            "message": "All raw materials for this production job are 100% covered by warehouse stock. Zero procurement needed.",
            "job_id": job.id,
            "shortages_count": 0
        }

    try:
        plan_res = create_and_optimize_procurement_plan(
            db=db,
            org_id=org_id,
            requirements=requirements,
            strategy=payload.strategy,
            production_job_id=job.id,
            budget_limit=payload.budget_limit,
            max_suppliers_per_material=payload.max_suppliers_per_material,
            allow_split_purchasing=payload.allow_split_purchasing,
            global_max_lead_time_days=payload.global_max_lead_time_days,
            min_quality_rating=payload.min_quality_rating,
            max_overbuy_pct=payload.max_overbuy_pct
        )
        return plan_res
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Optimization failed: {str(e)}")


@router.get("/plans/{plan_id}")
def get_procurement_plan_details(
    plan_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves complete plan data with item breakdowns, allocations, and baselines."""
    plan = db.query(ProcurementPlan).filter(
        ProcurementPlan.id == plan_id,
        ProcurementPlan.organization_id == org_id
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Procurement plan not found.")

    items_list = []
    for it in plan.items:
        items_list.append({
            "id": it.id,
            "material_id": it.material_id,
            "material_code": it.material.code if it.material else "N/A",
            "material_name": it.material.name if it.material else "N/A",
            "required_quantity": it.required_quantity,
            "unit": it.unit,
            "allocated_quantity": it.allocated_quantity,
            "allocated_cost": it.allocated_cost,
            "delivery_deadline": it.delivery_deadline.isoformat() if it.delivery_deadline else None
        })

    allocations_list = []
    for a in plan.allocations:
        allocations_list.append({
            "id": a.id,
            "material_id": a.material_id,
            "material_code": a.material.code if a.material else "N/A",
            "material_name": a.material.name if a.material else "N/A",
            "supplier_id": a.supplier_id,
            "supplier_name": a.supplier.name if a.supplier else "N/A",
            "quotation_id": a.quotation_id,
            "quotation_number": a.quotation.quotation_number if a.quotation else "N/A",
            "allocated_quantity": a.allocated_quantity,
            "unit": a.unit,
            "unit_landed_cost": a.unit_landed_cost,
            "fixed_freight_allocated": a.fixed_freight_allocated,
            "subtotal_cost": a.subtotal_cost,
            "moq": a.moq,
            "moq_satisfied": a.moq_satisfied,
            "package_count": a.package_count,
            "lead_time_days": a.lead_time_days,
            "delivery_date": a.delivery_date.isoformat() if a.delivery_date else None,
            "quality_rating": a.quality_rating,
            "supplier_risk_score": a.supplier_risk_score
        })

    return {
        "id": plan.id,
        "plan_number": plan.plan_number,
        "production_job_id": plan.production_job_id,
        "strategy": plan.strategy,
        "status": plan.status,
        "solver_status": plan.solver_status,
        "total_landed_cost": plan.total_landed_cost,
        "budget_limit": plan.budget_limit,
        "budget_utilized_pct": plan.budget_utilized_pct,
        "total_units_required": plan.total_units_required,
        "total_units_allocated": plan.total_units_allocated,
        "excess_units": plan.excess_units,
        "max_suppliers_per_material": plan.max_suppliers_per_material,
        "allow_split_purchasing": plan.allow_split_purchasing,
        "min_quality_rating": plan.min_quality_rating,
        "approval_status": plan.approval_status,
        "approved_by": plan.approved_by,
        "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
        "rejection_reason": plan.rejection_reason,
        "explanation_headline": plan.explanation_headline,
        "explanation_detail": plan.explanation_detail,
        "baseline_comparison": plan.baseline_comparison_json,
        "items": items_list,
        "allocations": allocations_list,
        "created_at": plan.created_at.isoformat() if plan.created_at else None
    }


@router.post("/plans/{plan_id}/reoptimize")
def reoptimize_plan(
    plan_id: str,
    strategy: Optional[str] = None,
    budget_limit: Optional[float] = None,
    allow_split_purchasing: Optional[bool] = None,
    max_suppliers_per_material: Optional[int] = None,
    min_quality_rating: Optional[float] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Re-runs mathematical optimization on an existing plan with altered strategy or constraints."""
    plan = db.query(ProcurementPlan).filter(
        ProcurementPlan.id == plan_id,
        ProcurementPlan.organization_id == org_id
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Procurement plan not found.")

    strat = strategy or plan.strategy
    b_limit = budget_limit if budget_limit is not None else plan.budget_limit
    split = allow_split_purchasing if allow_split_purchasing is not None else plan.allow_split_purchasing
    max_sup = max_suppliers_per_material if max_suppliers_per_material is not None else plan.max_suppliers_per_material
    q_rating = min_quality_rating if min_quality_rating is not None else plan.min_quality_rating

    reqs = [
        {
            "material_id": it.material_id,
            "material_code": it.material.code if it.material else it.material_id,
            "material_name": it.material.name if it.material else it.material_id,
            "required_quantity": it.required_quantity,
            "unit": it.unit
        }
        for it in plan.items
    ]

    candidates = generate_procurement_candidates(db, org_id, reqs)
    opt_solution = solve_multi_material_procurement(
        requirements=reqs,
        candidates=candidates,
        strategy=strat,
        global_budget_limit=b_limit,
        max_suppliers_per_material=max_sup,
        allow_split_purchasing=split,
        min_quality_rating=q_rating,
        max_overbuy_pct=plan.max_overbuy_pct
    )

    baselines = compute_procurement_baselines(reqs, candidates, opt_solution)

    # Clear previous allocations
    db.query(ProcurementPlanAllocation).filter(
        ProcurementPlanAllocation.procurement_plan_id == plan.id
    ).delete()

    plan.strategy = strat
    plan.budget_limit = b_limit
    plan.allow_split_purchasing = split
    plan.max_suppliers_per_material = max_sup
    plan.min_quality_rating = q_rating
    plan.solver_status = opt_solution.get("solver_status", "OPTIMAL")
    plan.total_landed_cost = float(opt_solution.get("total_landed_cost", 0.0))
    plan.budget_utilized_pct = opt_solution.get("budget_utilized_pct")
    plan.total_units_allocated = float(opt_solution.get("total_units_allocated", 0.0))
    plan.excess_units = float(opt_solution.get("excess_units", 0.0))
    plan.baseline_comparison_json = baselines
    plan.explanation_headline = opt_solution.get("explanation_headline")
    plan.explanation_detail = opt_solution.get("explanation_detail")
    plan.status = "OPTIMIZED" if opt_solution["status"] != "INFEASIBLE" else "NEEDS_REVIEW"

    # Persist new allocations
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
        "strategy": plan.strategy,
        "total_landed_cost": plan.total_landed_cost,
        "allocations_count": len(opt_solution.get("allocations", [])),
        "baseline_comparison": baselines,
        "explanation": plan.explanation_headline
    }


@router.post("/plans/{plan_id}/request-approval")
def request_approval_route(
    plan_id: str,
    requested_by: str = "Procurement Lead",
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Submits the plan for managerial approval."""
    try:
        return request_plan_approval(db, org_id, plan_id, requested_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/plans/{plan_id}/approve")
def approve_plan_route(
    plan_id: str,
    approved_by: str = "Chief Financial Officer",
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Approves the procurement plan."""
    try:
        return approve_procurement_plan(db, org_id, plan_id, approved_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/plans/{plan_id}/reject")
def reject_plan_route(
    plan_id: str,
    payload: ProcurementPlanApprovalRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Rejects the procurement plan."""
    try:
        return reject_procurement_plan(
            db, org_id, plan_id,
            rejected_by=payload.user_id or "Chief Financial Officer",
            reason=payload.reason or "Rejected by management"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/plans/{plan_id}/generate-requisitions")
def generate_requisitions_route(
    plan_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Converts approved plan allocations into actual purchase requisition entities."""
    try:
        return generate_purchase_requisitions_from_plan(db, org_id, plan_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------------------------------------------------------
# 3. Legacy Requisitions Endpoints (Maintained for Backward Compatibility)
# -----------------------------------------------------------------------------
@router.get("/requisitions")
def list_purchase_requisitions(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Lists all formal procurement requisitions generated from comparison decisions."""
    reqs = db.query(PurchaseRequisition).filter(
        PurchaseRequisition.organization_id == org_id
    ).order_by(PurchaseRequisition.created_at.desc()).all()

    return [
        {
            "id": r.id,
            "requisition_number": r.requisition_number,
            "material_id": r.material_id,
            "material_name": r.material.name if r.material else "N/A",
            "material_code": r.material.code if r.material else "N/A",
            "required_quantity": r.required_quantity,
            "unit": r.unit,
            "required_by_date": r.required_by_date.isoformat() if r.required_by_date else None,
            "reason": r.reason,
            "budget_limit": r.budget_limit,
            "selected_supplier_id": r.selected_supplier_id,
            "selected_supplier_name": r.selected_supplier.name if r.selected_supplier else None,
            "selected_quotation_id": r.selected_quotation_id,
            "selected_quotation_number": r.selected_quotation.quotation_number if r.selected_quotation else None,
            "estimated_total_cost": r.estimated_total_cost,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in reqs
    ]


@router.post("/requisitions")
def create_purchase_requisition(
    payload: PurchaseRequisitionCreate,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Creates a formal Purchase Requisition record from a supplier comparison decision."""
    mat = db.query(Material).filter(
        Material.id == payload.material_id,
        Material.organization_id == org_id
    ).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material specified in requisition not found.")

    if payload.selected_supplier_id:
        sup = db.query(Supplier).filter(
            Supplier.id == payload.selected_supplier_id,
            Supplier.organization_id == org_id
        ).first()
        if not sup:
            raise HTTPException(status_code=404, detail="Selected supplier not found.")

    if payload.selected_quotation_id:
        quote = db.query(SupplierQuotation).filter(
            SupplierQuotation.id == payload.selected_quotation_id,
            SupplierQuotation.organization_id == org_id
        ).first()
        if not quote:
            raise HTTPException(status_code=404, detail="Selected quotation not found.")

    # Generate sequential requisition reference
    seq_num = db.query(PurchaseRequisition).filter(
        PurchaseRequisition.organization_id == org_id
    ).count() + 1
    req_number = f"REQ-2026-{seq_num:04d}"

    req_by_dt = None
    if payload.required_by_date:
        try:
            req_by_dt = datetime.fromisoformat(payload.required_by_date.replace("Z", "+00:00"))
        except Exception:
            pass

    req = PurchaseRequisition(
        organization_id=org_id,
        requisition_number=req_number,
        material_id=payload.material_id,
        required_quantity=payload.required_quantity,
        unit=payload.unit or mat.unit or "kg",
        required_by_date=req_by_dt,
        reason=payload.reason or "Procurement Comparison Recommendation",
        budget_limit=payload.budget_limit,
        selected_supplier_id=payload.selected_supplier_id,
        selected_quotation_id=payload.selected_quotation_id,
        estimated_total_cost=payload.estimated_total_cost,
        comparison_result_id=payload.comparison_result_id,
        status="PENDING"
    )
    db.add(req)

    audit = AuditLog(
        organization_id=org_id,
        action="CREATE_PURCHASE_REQUISITION",
        entity_type="PURCHASE_REQUISITION",
        entity_id=req.id,
        changes_json={
            "requisition_number": req_number,
            "material": mat.name,
            "quantity": payload.required_quantity,
            "estimated_cost": payload.estimated_total_cost
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(req)

    return {
        "status": "CREATED",
        "requisition_id": req.id,
        "requisition_number": req.requisition_number,
        "material_name": mat.name,
        "quantity": req.required_quantity,
        "unit": req.unit,
        "estimated_total_cost": req.estimated_total_cost,
        "approval_status": req.status,
        "message": f"Procurement Requisition {req.requisition_number} successfully logged and awaiting PO release."
    }


