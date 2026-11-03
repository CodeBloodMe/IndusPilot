from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_org_id
from app.models.entities import ProductionCostEstimate, CostingScenario, Product, BillOfMaterials
from app.schemas.domain import ManufacturingCostRequest, CostingSimulationRequest
from app.calculations.cost_engine import calculate_manufacturing_cost
from app.services.costing_service import create_or_save_cost_estimate, run_what_if_simulation

router = APIRouter()


@router.post("/calculate")
def calculate_production_costs_compat(
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
            workers_count=payload.workers_count,
            machine_hours=payload.machine_hours,
            machine_rate_per_hour=payload.machine_rate_per_hour,
            machine_setup_hours=payload.machine_setup_hours,
            machine_setup_rate_per_hour=payload.machine_setup_rate_per_hour,
            machine_power_kw=payload.machine_power_kw,
            electricity_kwh=payload.electricity_kwh,
            electricity_tariff_per_kwh=payload.electricity_tariff_per_kwh,
            secondary_processes_total=payload.secondary_processes_total,
            transportation_total=payload.transportation_total,
            packaging_total=payload.packaging_total,
            overhead_method=payload.overhead_method,
            overhead_rate=payload.overhead_rate if payload.overhead_rate != 12.0 else payload.overhead_pct,
            other_expenses_total=payload.other_expenses_total,
            recoverable_scrap_value_total=payload.recoverable_scrap_value_total,
            target_gross_margin_pct=payload.target_gross_margin_pct,
            custom_selling_price_per_unit=payload.custom_selling_price_per_unit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cost calculation failed: {str(e)}")


@router.post("/estimate")
def estimate_and_persist_cost(
    payload: ManufacturingCostRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Calculates manufacturing cost and persists an official audited estimate record.
    Preserves all input snapshots, verified quote references, and operational assumptions.
    """
    try:
        mat_breakdown = [m.model_dump() for m in payload.material_costs_breakdown]
        calc_result = calculate_manufacturing_cost(
            production_quantity=payload.production_quantity,
            material_costs_breakdown=mat_breakdown,
            direct_labor_hours=payload.direct_labor_hours,
            labor_rate_per_hour=payload.labor_rate_per_hour,
            workers_count=payload.workers_count,
            machine_hours=payload.machine_hours,
            machine_rate_per_hour=payload.machine_rate_per_hour,
            machine_setup_hours=payload.machine_setup_hours,
            machine_setup_rate_per_hour=payload.machine_setup_rate_per_hour,
            machine_power_kw=payload.machine_power_kw,
            electricity_kwh=payload.electricity_kwh,
            electricity_tariff_per_kwh=payload.electricity_tariff_per_kwh,
            secondary_processes_total=payload.secondary_processes_total,
            transportation_total=payload.transportation_total,
            packaging_total=payload.packaging_total,
            overhead_method=payload.overhead_method,
            overhead_rate=payload.overhead_rate if payload.overhead_rate != 12.0 else payload.overhead_pct,
            other_expenses_total=payload.other_expenses_total,
            recoverable_scrap_value_total=payload.recoverable_scrap_value_total,
            target_gross_margin_pct=payload.target_gross_margin_pct,
            custom_selling_price_per_unit=payload.custom_selling_price_per_unit
        )

        estimate_record = None
        if payload.save_estimate or (payload.product_id and payload.bom_id):
            prod_id = payload.product_id
            bom_id = payload.bom_id
            if not prod_id:
                p = db.query(Product).filter(Product.organization_id == org_id).first()
                prod_id = p.id if p else None
            if not bom_id and prod_id:
                b = db.query(BillOfMaterials).filter(BillOfMaterials.product_id == prod_id).first()
                bom_id = b.id if b else None

            if prod_id and bom_id:
                estimate_record = create_or_save_cost_estimate(
                    db=db,
                    org_id=org_id,
                    product_id=prod_id,
                    bom_id=bom_id,
                    payload_dict=payload.model_dump(),
                    calc_result=calc_result
                )

        response_data = dict(calc_result)
        if estimate_record:
            response_data["saved_estimate_id"] = estimate_record.id
            response_data["estimate_number"] = estimate_record.estimate_number
            response_data["data_quality_status"] = estimate_record.data_quality_status

        return response_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cost estimate failed: {str(e)}")


@router.get("/estimates")
def list_cost_estimates(
    product_id: Optional[str] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    query = db.query(ProductionCostEstimate).filter(ProductionCostEstimate.organization_id == org_id)
    if product_id:
        query = query.filter(ProductionCostEstimate.product_id == product_id)

    estimates = query.order_by(ProductionCostEstimate.created_at.desc()).all()
    results = []
    for est in estimates:
        p = est.product
        b = est.bom
        results.append({
            "id": est.id,
            "estimate_number": est.estimate_number,
            "product_id": est.product_id,
            "product_name": p.name if p else "Product",
            "product_code": p.code if p else "",
            "bom_id": est.bom_id,
            "bom_version": b.version if b else "",
            "batch_size": est.batch_size,
            "total_production_cost": est.total_production_cost,
            "unit_cost": est.unit_cost,
            "break_even_price": est.break_even_price,
            "suggested_selling_price": est.suggested_selling_price,
            "effective_margin_pct": est.effective_margin_pct,
            "data_quality_status": est.data_quality_status,
            "is_loss_making": est.is_loss_making,
            "scenarios_count": len(est.scenarios),
            "created_at": est.created_at.isoformat() if est.created_at else None
        })
    return results


@router.get("/estimates/{estimate_id}")
def get_cost_estimate_detail(
    estimate_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    est = db.query(ProductionCostEstimate).filter(
        ProductionCostEstimate.id == estimate_id,
        ProductionCostEstimate.organization_id == org_id
    ).first()
    if not est:
        raise HTTPException(status_code=404, detail="Cost estimate not found.")

    p = est.product
    b = est.bom

    scenarios = []
    for s in est.scenarios:
        scenarios.append({
            "id": s.id,
            "scenario_name": s.scenario_name,
            "scenario_description": s.scenario_description,
            "delta_total_cost": s.delta_total_cost,
            "delta_unit_cost": s.delta_unit_cost,
            "delta_margin_pct": s.delta_margin_pct,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })

    return {
        "id": est.id,
        "estimate_number": est.estimate_number,
        "product_id": est.product_id,
        "product_name": p.name if p else "Product",
        "product_code": p.code if p else "",
        "bom_id": est.bom_id,
        "bom_version": b.version if b else "",
        "batch_size": est.batch_size,
        "data_quality_status": est.data_quality_status,
        "cost_breakdown": {
            "raw_material_cost": est.raw_material_cost,
            "wastage_cost": est.wastage_cost,
            "direct_labor_cost": est.direct_labor_cost,
            "machine_cost": est.machine_cost,
            "electricity_cost": est.electricity_cost,
            "secondary_processes_cost": est.secondary_processes_cost,
            "transport_cost": est.transport_cost,
            "packaging_cost": est.packaging_cost,
            "overhead_cost": est.overhead_cost,
            "other_expenses": est.other_expenses,
            "total_production_cost": est.total_production_cost,
        },
        "unit_economics": {
            "unit_cost": est.unit_cost,
            "break_even_price": est.break_even_price,
            "suggested_selling_price": est.suggested_selling_price,
            "effective_selling_price": est.effective_selling_price,
            "target_margin_pct": est.target_margin_pct,
            "effective_margin_pct": est.effective_margin_pct,
            "markup_pct": est.markup_pct,
            "total_revenue": est.total_revenue,
            "projected_profit": est.projected_profit,
            "is_loss_making": est.is_loss_making,
        },
        "assumptions_snapshot": est.assumptions_snapshot_json,
        "items_breakdown": est.items_breakdown_json,
        "scenarios": scenarios,
        "created_at": est.created_at.isoformat() if est.created_at else None
    }


@router.post("/simulate")
def simulate_what_if_scenario(
    payload: CostingSimulationRequest,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Executes a side-by-side What-If Cost Simulation:
    Recalculates 14-factor economics with simulation overrides and produces variance diffs.
    Preserves baseline estimate without mutation.
    """
    baseline_payload: Dict[str, Any] = {}

    if payload.baseline_estimate_id:
        est = db.query(ProductionCostEstimate).filter(
            ProductionCostEstimate.id == payload.baseline_estimate_id,
            ProductionCostEstimate.organization_id == org_id
        ).first()
        if not est:
            raise HTTPException(status_code=404, detail="Baseline cost estimate not found.")
        if est.assumptions_snapshot_json and "inputs" in est.assumptions_snapshot_json:
            baseline_payload = est.assumptions_snapshot_json["inputs"]
        else:
            baseline_payload = {
                "production_quantity": est.batch_size,
                "material_costs_breakdown": est.items_breakdown_json or [],
                "direct_labor_hours": 120.0,
                "labor_rate_per_hour": 180.0,
                "machine_hours": 45.0,
                "machine_rate_per_hour": 350.0,
                "electricity_kwh": 650.0,
                "electricity_tariff_per_kwh": 8.5,
                "secondary_processes_total": est.secondary_processes_cost,
                "transportation_total": est.transport_cost,
                "packaging_total": est.packaging_cost,
                "overhead_rate": 12.0,
                "target_gross_margin_pct": est.target_margin_pct
            }
    elif payload.baseline_inputs:
        baseline_payload = payload.baseline_inputs.model_dump()
    else:
        raise HTTPException(status_code=400, detail="Must provide either baseline_estimate_id or baseline_inputs.")

    try:
        simulation = run_what_if_simulation(
            baseline_payload=baseline_payload,
            simulation_overrides=payload.simulation_overrides
        )
        return simulation
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Simulation failed: {str(e)}")


@router.post("/estimates/{estimate_id}/save-scenario")
def save_scenario_endpoint(
    estimate_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Saves a simulation scenario linked to a baseline cost estimate."""
    est = db.query(ProductionCostEstimate).filter(
        ProductionCostEstimate.id == estimate_id,
        ProductionCostEstimate.organization_id == org_id
    ).first()
    if not est:
        raise HTTPException(status_code=404, detail="Baseline cost estimate not found.")

    scenario_name = payload.get("scenario_name", "Alternative Scenario")
    desc = payload.get("scenario_description")
    overrides = payload.get("overrides", {})
    sim_result = payload.get("simulated_result", {})

    delta_total = sim_result.get("variance", {}).get("delta_total_batch_cost", 0.0)
    delta_unit = sim_result.get("variance", {}).get("delta_unit_cost", 0.0)
    delta_margin = sim_result.get("variance", {}).get("delta_gross_margin_pct", 0.0)

    scenario = CostingScenario(
        organization_id=org_id,
        cost_estimate_id=est.id,
        scenario_name=scenario_name,
        scenario_description=desc,
        input_parameters_json=overrides,
        simulated_results_json=sim_result,
        delta_total_cost=delta_total,
        delta_unit_cost=delta_unit,
        delta_margin_pct=delta_margin,
        created_at=datetime.utcnow()
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return {
        "id": scenario.id,
        "cost_estimate_id": est.id,
        "scenario_name": scenario.scenario_name,
        "delta_total_cost": scenario.delta_total_cost,
        "delta_unit_cost": scenario.delta_unit_cost,
        "created_at": scenario.created_at.isoformat()
    }
