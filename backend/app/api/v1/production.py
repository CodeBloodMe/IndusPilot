from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_org_id
from app.models.entities import (
    ProductionJob, ProductionJobMaterialRequirement, Product,
    BillOfMaterials, Material, Inventory, PurchaseRequisition, StockReservation
)
from app.schemas.domain import ProductionJobCreate, ProductionJobUpdate
from app.calculations.bom_engine import explode_bom
from app.calculations.inventory_netting import calculate_net_procurement_requirement
from app.services.inventory_service import reserve_stock

router = APIRouter()


@router.get("/jobs")
def list_production_jobs(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    product_id: Optional[str] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    query = db.query(ProductionJob).filter(ProductionJob.organization_id == org_id)
    if status:
        query = query.filter(ProductionJob.status == status.upper().strip())
    if priority:
        query = query.filter(ProductionJob.priority == priority.upper().strip())
    if product_id:
        query = query.filter(ProductionJob.product_id == product_id)

    jobs = query.order_by(ProductionJob.created_at.desc()).all()
    results = []
    for j in jobs:
        prod = j.product
        bom = j.bom
        shortage_count = sum(1 for r in j.requirements if not r.is_covered)
        results.append({
            "id": j.id,
            "job_number": j.job_number,
            "customer_order_ref": j.customer_order_ref,
            "product_id": j.product_id,
            "product_name": prod.name if prod else "Unknown Product",
            "product_code": prod.code if prod else "",
            "bom_id": j.bom_id,
            "bom_version": bom.version if bom else "",
            "production_quantity": j.production_quantity,
            "unit": j.unit,
            "priority": j.priority,
            "status": j.status,
            "components_count": len(j.requirements),
            "shortage_count": shortage_count,
            "is_ready_for_production": (shortage_count == 0 and len(j.requirements) > 0),
            "planned_start_date": j.planned_start_date.isoformat() if j.planned_start_date else None,
            "target_completion_date": j.target_completion_date.isoformat() if j.target_completion_date else None,
            "created_at": j.created_at.isoformat() if j.created_at else None
        })
    return results


@router.post("/jobs", status_code=201)
def create_production_job(
    payload: ProductionJobCreate,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    prod = db.query(Product).filter(Product.id == payload.product_id, Product.organization_id == org_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found.")

    if payload.bom_id:
        bom = db.query(BillOfMaterials).filter(
            BillOfMaterials.id == payload.bom_id,
            BillOfMaterials.product_id == prod.id
        ).first()
    else:
        bom = next((b for b in prod.boms if b.is_active), None)

    if not bom:
        raise HTTPException(status_code=400, detail="Product does not have an active BOM. Please create or specify a BOM.")

    # Generate sequential job number
    count = db.query(ProductionJob).filter(ProductionJob.organization_id == org_id).count() + 1
    job_number = f"JOB-2026-{count:04d}"

    start_dt = datetime.fromisoformat(payload.planned_start_date.replace("Z", "")) if payload.planned_start_date else None
    target_dt = datetime.fromisoformat(payload.target_completion_date.replace("Z", "")) if payload.target_completion_date else None

    job = ProductionJob(
        organization_id=org_id,
        job_number=job_number,
        customer_order_ref=payload.customer_order_ref,
        product_id=prod.id,
        bom_id=bom.id,
        production_quantity=payload.production_quantity,
        unit=prod.base_unit or "units",
        planned_start_date=start_dt,
        target_completion_date=target_dt,
        priority=payload.priority.upper(),
        status="PLANNED",
        notes=payload.notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "id": job.id,
        "job_number": job.job_number,
        "product_id": job.product_id,
        "product_name": prod.name,
        "production_quantity": job.production_quantity,
        "status": job.status,
        "priority": job.priority,
        "created_at": job.created_at.isoformat()
    }


@router.get("/jobs/{job_id}")
def get_production_job_details(
    job_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id, ProductionJob.organization_id == org_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found.")

    prod = job.product
    bom = job.bom

    materials = []
    for r in job.requirements:
        m = r.material
        materials.append({
            "requirement_id": r.id,
            "material_id": r.material_id,
            "material_name": m.name if m else "Material",
            "material_code": m.code if m else "",
            "net_quantity_required": r.net_quantity_required,
            "gross_quantity_required": r.gross_quantity_required,
            "unit": r.unit,
            "scrap_quantity": r.scrap_quantity,
            "available_stock": r.available_stock,
            "shortage_quantity": r.shortage_quantity,
            "is_covered": r.is_covered,
            "requisition_id": r.requisition_id
        })

    return {
        "id": job.id,
        "job_number": job.job_number,
        "customer_order_ref": job.customer_order_ref,
        "product_id": job.product_id,
        "product_name": prod.name if prod else "Product",
        "product_code": prod.code if prod else "",
        "bom_id": job.bom_id,
        "bom_version": bom.version if bom else "",
        "production_quantity": job.production_quantity,
        "unit": job.unit,
        "priority": job.priority,
        "status": job.status,
        "notes": job.notes,
        "planned_start_date": job.planned_start_date.isoformat() if job.planned_start_date else None,
        "target_completion_date": job.target_completion_date.isoformat() if job.target_completion_date else None,
        "materials": materials,
        "created_at": job.created_at.isoformat() if job.created_at else None
    }


@router.patch("/jobs/{job_id}")
def update_production_job(
    job_id: str,
    payload: ProductionJobUpdate,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id, ProductionJob.organization_id == org_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found.")

    if payload.status:
        job.status = payload.status.upper().strip()
    if payload.priority:
        job.priority = payload.priority.upper().strip()
    if payload.notes is not None:
        job.notes = payload.notes
    if payload.planned_start_date:
        job.planned_start_date = datetime.fromisoformat(payload.planned_start_date.replace("Z", ""))
    if payload.target_completion_date:
        job.target_completion_date = datetime.fromisoformat(payload.target_completion_date.replace("Z", ""))

    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    return {
        "id": job.id,
        "job_number": job.job_number,
        "status": job.status,
        "priority": job.priority,
        "updated_at": job.updated_at.isoformat()
    }


@router.post("/jobs/{job_id}/material-check")
def run_job_material_check(
    job_id: str,
    reserve_available: bool = Query(False, description="Whether to automatically reserve available stock for this job"),
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    MRP Stage:
    1. Retrieves Job and BOM.
    2. Explodes gross material requirements with scrap/yield.
    3. Checks warehouse stock, confirmed incoming stock, and active reservations.
    4. Computes shortages and saves ProductionJobMaterialRequirement records.
    5. Updates job status to READY_FOR_PRODUCTION (if covered) or AWAITING_PROCUREMENT.
    """
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id, ProductionJob.organization_id == org_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found.")

    bom = job.bom
    if not bom or not bom.items:
        raise HTTPException(status_code=400, detail="Job BOM has no items.")

    # Clear previous material requirements for fresh MRP run
    db.query(ProductionJobMaterialRequirement).filter(
        ProductionJobMaterialRequirement.production_job_id == job.id
    ).delete()

    bom_items_data = [
        {
            "material_id": it.material_id,
            "quantity_per_unit": it.quantity_per_unit,
            "unit": it.unit,
            "wastage_pct": it.wastage_pct,
            "scrap_allowance_method": it.scrap_allowance_method,
            "expected_yield_pct": it.expected_yield_pct,
            "process_stage": it.process_stage
        }
        for it in bom.items
    ]

    explosion = explode_bom(job.production_quantity, bom_items_data)

    shortage_count = 0
    requirements_summary = []

    for comp in explosion["components"]:
        mat_id = comp["material_id"]
        inv = db.query(Inventory).filter(
            Inventory.material_id == mat_id,
            Inventory.organization_id == org_id
        ).first()

        cur_stock = inv.current_stock if inv else 0.0
        res_stock = inv.reserved_stock if inv else 0.0
        inc_stock = inv.incoming_stock if inv else 0.0
        saf_stock = inv.safety_stock if inv else 0.0

        netting = calculate_net_procurement_requirement(
            gross_requirement=comp["total_gross_required"],
            current_stock=cur_stock,
            reserved_stock=res_stock,
            incoming_stock=inc_stock,
            safety_stock=saf_stock
        )

        shortage = netting["net_shortage"]
        is_cov = not netting["has_shortage"]

        if netting["has_shortage"]:
            shortage_count += 1

        req_row = ProductionJobMaterialRequirement(
            production_job_id=job.id,
            material_id=mat_id,
            net_quantity_required=comp["total_net_required"],
            gross_quantity_required=comp["total_gross_required"],
            unit=comp["unit"],
            scrap_quantity=comp["total_wastage_scrap"],
            available_stock=netting["available_stock"],
            shortage_quantity=shortage,
            is_covered=is_cov,
            created_at=datetime.utcnow()
        )
        db.add(req_row)

        # Optionally reserve available stock right away
        if reserve_available and netting["available_stock"] > 0:
            qty_to_reserve = min(comp["total_gross_required"], netting["available_stock"])
            try:
                reserve_stock(
                    db=db,
                    org_id=org_id,
                    material_id=mat_id,
                    quantity=qty_to_reserve,
                    production_job_id=job.id,
                    unit=comp["unit"],
                    notes=f"Auto-reserved from MRP check for job {job.job_number}"
                )
            except Exception:
                pass

        requirements_summary.append({
            "material_id": mat_id,
            "material_name": comp["material_name"],
            "gross_required": comp["total_gross_required"],
            "unit": comp["unit"],
            "available_stock": netting["available_stock"],
            "shortage": shortage,
            "is_covered": is_cov
        })

    # Update job status
    if shortage_count == 0:
        job.status = "READY_FOR_PRODUCTION"
    else:
        job.status = "AWAITING_PROCUREMENT"
    job.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(job)

    return {
        "job_id": job.id,
        "job_number": job.job_number,
        "new_status": job.status,
        "shortages_count": shortage_count,
        "is_ready_for_production": shortage_count == 0,
        "requirements": requirements_summary
    }


@router.post("/jobs/{job_id}/procurement-handoff")
def handoff_job_to_procurement(
    job_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Creates official PurchaseRequisition records for all un-covered material shortages in the job.
    Links the requisition to the job requirement records.
    """
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id, ProductionJob.organization_id == org_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found.")

    uncovered_reqs = [r for r in job.requirements if not r.is_covered and r.shortage_quantity > 0]
    if not uncovered_reqs:
        return {
            "message": "No shortages exist for this job. All materials are covered by stock.",
            "requisitions_created": 0,
            "job_status": job.status
        }

    created_reqs = []
    for r in uncovered_reqs:
        mat = r.material
        req_count = db.query(PurchaseRequisition).filter(PurchaseRequisition.organization_id == org_id).count() + 1
        req_num = f"PR-2026-JOB-{req_count:04d}"

        pr = PurchaseRequisition(
            organization_id=org_id,
            requisition_number=req_num,
            material_id=r.material_id,
            required_quantity=r.shortage_quantity,
            unit=r.unit,
            required_by_date=job.planned_start_date,
            delivery_deadline=job.planned_start_date,
            reason=f"MRP Shortage for Production Job {job.job_number} ({job.product.name})",
            status="PENDING",
            created_at=datetime.utcnow()
        )
        db.add(pr)
        db.flush()

        r.requisition_id = pr.id
        created_reqs.append({
            "requisition_id": pr.id,
            "requisition_number": pr.requisition_number,
            "material_id": r.material_id,
            "material_name": mat.name if mat else "Material",
            "quantity": r.shortage_quantity,
            "unit": r.unit
        })

    job.status = "AWAITING_PROCUREMENT"
    job.updated_at = datetime.utcnow()
    db.commit()

    return {
        "job_id": job.id,
        "job_number": job.job_number,
        "requisitions_count": len(created_reqs),
        "requisitions": created_reqs,
        "new_job_status": job.status
    }

