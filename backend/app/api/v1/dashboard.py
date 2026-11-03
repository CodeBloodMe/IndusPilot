from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_org_id
from app.models.entities import Supplier, SupplierQuotation, Inventory, ApprovalRequest, NegotiationSession, CustomerQuotation

router = APIRouter()

@router.get("/metrics")
@router.get("/summary")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Computes live dashboard statistics from database records.
    Never presents fabricated random metrics.
    """
    total_suppliers = db.query(Supplier).filter(Supplier.organization_id == org_id).count()
    verified_quotes = db.query(SupplierQuotation).filter(
        SupplierQuotation.organization_id == org_id,
        SupplierQuotation.status == "VERIFIED"
    ).all()
    pending_quotes = db.query(SupplierQuotation).filter(
        SupplierQuotation.organization_id == org_id,
        SupplierQuotation.status == "DRAFT"
    ).count()

    total_spend = sum(q.total_amount for q in verified_quotes)

    # Inventory shortages
    inventories = db.query(Inventory).filter(Inventory.organization_id == org_id).all()
    critical_shortages = []
    for inv in inventories:
        avail = max(0.0, inv.current_stock - inv.reserved_stock)
        if avail <= inv.safety_stock:
            critical_shortages.append({
                "material_name": inv.material.name if inv.material else "Material",
                "current_stock": inv.current_stock,
                "available_stock": avail,
                "safety_stock": inv.safety_stock,
                "unit": inv.material.unit if inv.material else "kg"
            })

    # Approvals pending
    pending_approvals = db.query(ApprovalRequest).filter(
        ApprovalRequest.organization_id == org_id,
        ApprovalRequest.status == "PENDING"
    ).count()

    # Negotiation savings calculated from sessions
    sessions = db.query(NegotiationSession).filter(NegotiationSession.organization_id == org_id).all()
    total_savings = 0.0
    for s in sessions:
        if s.current_offered_price < s.original_unit_price:
            total_savings += (s.original_unit_price - s.current_offered_price) * s.quantity

    # Recent quotes
    recent_quotes = []
    for q in verified_quotes[:5]:
        recent_quotes.append({
            "id": q.id,
            "quotation_number": q.quotation_number,
            "supplier_name": q.supplier.name if q.supplier else "Vendor",
            "total_amount": q.total_amount,
            "date": q.quotation_date.strftime("%d %b %Y") if q.quotation_date else "Today"
        })

    return {
        "procurement_spend_total": round(total_spend, 2),
        "active_suppliers_count": total_suppliers,
        "verified_quotations_count": len(verified_quotes),
        "pending_quotations_count": pending_quotes,
        "pending_approvals_count": pending_approvals,
        "material_shortages_count": len(critical_shortages),
        "total_savings_generated": round(total_savings, 2),
        "critical_shortages": critical_shortages,
        "recent_quotations": recent_quotes,
        "currency_symbol": "₹"
    }

