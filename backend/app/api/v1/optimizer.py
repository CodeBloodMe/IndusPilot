from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_org_id
from app.schemas.domain import OptimizationRequest
from app.optimizers.procurement_optimizer import optimize_procurement_split
from app.models.entities import SupplierQuotation

router = APIRouter()

@router.post("/solve")
def solve_procurement_optimization(
    payload: OptimizationRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Executes Google OR-Tools Mixed-Integer Linear Programming solver
    to find the optimal multi-supplier allocation meeting all constraints.
    """
    candidates = []
    if payload.candidates:
        candidates = [c.model_dump() for c in payload.candidates]
    else:
        # Load from verified quotations in DB
        quotes = db.query(SupplierQuotation).filter(
            SupplierQuotation.organization_id == org_id,
            SupplierQuotation.status == "VERIFIED"
        ).all()
        for q in quotes:
            sup = q.supplier
            item = q.items[0] if q.items else None
            if item:
                # Approximate landed cost: unit price + tax (18%) + freight/qty
                u_landed = (item.unit_price * 1.18) + (q.freight_cost / max(1.0, payload.required_quantity))
                candidates.append({
                    "supplier_id": sup.id if sup else q.id,
                    "supplier_name": sup.name if sup else "Vendor",
                    "unit_landed_cost": round(u_landed, 2),
                    "fixed_freight": q.freight_cost,
                    "capacity": 1500.0,
                    "moq": item.moq,
                    "lead_time_days": item.lead_time_days,
                    "quality_rating": sup.quality_rating if sup else 4.0
                })

    if not candidates:
        raise HTTPException(status_code=400, detail="No supplier candidates provided or found in database.")

    try:
        solution = optimize_procurement_split(
            required_quantity=payload.required_quantity,
            supplier_candidates=candidates,
            budget_limit=payload.budget_limit,
            max_lead_time_days=payload.max_lead_time_days,
            enforce_single_supplier=payload.enforce_single_supplier
        )
        return solution
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Optimization solver error: {str(e)}")

