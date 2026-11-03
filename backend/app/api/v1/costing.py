from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_org_id
from app.schemas.domain import ManufacturingCostRequest
from app.calculations.cost_engine import calculate_manufacturing_cost

router = APIRouter()

@router.post("/calculate")
def calculate_production_costs(
    payload: ManufacturingCostRequest,
    org_id: str = Depends(get_current_org_id)
):
    """
    Executes deterministic 14-factor manufacturing cost calculation with Python Decimal.
    Computes break-even price, suggested selling price, and alerts on loss-making orders.
    """
    try:
        mat_breakdown = [m.model_dump() for m in payload.material_costs_breakdown]
        result = calculate_manufacturing_cost(
            production_quantity=payload.production_quantity,
            material_costs_breakdown=mat_breakdown,
            direct_labor_hours=payload.direct_labor_hours,
            labor_rate_per_hour=payload.labor_rate_per_hour,
            machine_hours=payload.machine_hours,
            machine_rate_per_hour=payload.machine_rate_per_hour,
            electricity_kwh=payload.electricity_kwh,
            electricity_tariff_per_kwh=payload.electricity_tariff_per_kwh,
            secondary_processes_total=payload.secondary_processes_total,
            transportation_total=payload.transportation_total,
            packaging_total=payload.packaging_total,
            overhead_pct=payload.overhead_pct,
            target_gross_margin_pct=payload.target_gross_margin_pct,
            custom_selling_price_per_unit=payload.custom_selling_price_per_unit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cost calculation failed: {str(e)}")

