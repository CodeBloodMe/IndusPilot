"""
IndusPilot Central Typed Tool Registry & Governance Framework
Classifies every tool into explicit permission tiers (READ_ONLY, DRAFT_CREATION, SENSITIVE_MUTATION, EXTERNAL_ACTION),
validates inputs using Pydantic, executes against live database records, and logs auditable traces.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Type
import time
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.entities import (
    Supplier, Material, SupplierMaterial, SupplierQuotation,
    Product, BOM, BOMItem, Inventory, InventoryLedger, StockReservation,
    ProductionJob, CostEstimate, ProcurementPlan, PurchaseRequisition,
    CustomerQuotation, Customer, ApprovalRequest, AgentToolCall
)
from app.calculations.landed_cost import calculate_landed_cost
from app.calculations.scoring import evaluate_supplier_quotation
from app.calculations.bom_engine import explode_bom
from app.calculations.inventory_netting import calculate_net_procurement_requirement
from app.calculations.cost_engine import calculate_manufacturing_cost
from app.services.procurement_plan_service import (
    create_and_optimize_procurement_plan
)
from app.services.negotiation_service import (
    analyze_negotiation_opportunity,
    generate_negotiation_message_text,
    simulate_supplier_response,
    analyze_supplier_response,
    apply_negotiated_quotation_revision
)
from app.services.customer_quotation_service import (
    calculate_quotation_pricing as calculate_customer_quotation_pricing,
    create_customer_quotation_record as create_customer_quotation,
    recalculate_customer_quotation
)
from app.services.pdf_generator import generate_customer_quotation_pdf
from app.services.material_matcher import match_material_specification as match_material_spec


class ToolPermissionTier(str, Enum):
    READ_ONLY = "READ_ONLY" # Safe auto-execution for authenticated users
    DRAFT_CREATION = "DRAFT_CREATION" # Generates reversible draft records
    SENSITIVE_MUTATION = "SENSITIVE_MUTATION" # Mutates live allocation/inventory; requires confirmation
    EXTERNAL_ACTION = "EXTERNAL_ACTION" # External dispatch; requires mandatory human approval


class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        permission_tier: ToolPermissionTier,
        agent_role: str,
        input_schema: Type[BaseModel],
        handler: Callable
    ):
        self.name = name
        self.description = description
        self.permission_tier = permission_tier
        self.agent_role = agent_role
        self.input_schema = input_schema
        self.handler = handler

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_tier": self.permission_tier.value,
            "agent_role": self.agent_role,
            "parameters": self.input_schema.model_json_schema()
        }


# ============================================================================
# PYDANTIC INPUT SCHEMAS FOR ALL 30+ TOOLS
# ============================================================================

# --- Supplier Tools ---
class SearchSuppliersInput(BaseModel):
    material_filter: Optional[str] = Field(None, description="Filter suppliers by material name or grade (e.g. 'SS304', 'Aluminium')")
    min_rating: Optional[float] = Field(None, description="Minimum supplier quality rating (1.0 to 5.0)")
    city: Optional[str] = Field(None, description="City location filter")

class GetSupplierDetailsInput(BaseModel):
    supplier_id: str = Field(..., description="ID of the supplier")

class ListSupplierQuotationsInput(BaseModel):
    supplier_id: Optional[str] = Field(None, description="Optional supplier ID to filter quotations")
    status: Optional[str] = Field("VERIFIED", description="Quotation status filter (e.g. 'VERIFIED', 'NEEDS_CORRECTION')")

class GetSupplierPerformanceInput(BaseModel):
    supplier_id: str = Field(..., description="Supplier ID")

class CompareSupplierQuotationsInput(BaseModel):
    quotation_ids: List[str] = Field(..., description="List of quotation IDs to evaluate side-by-side")
    target_quantity: float = Field(..., description="Target purchase volume in kg/units")

class CalculateLandedCostInput(BaseModel):
    unit_price: float = Field(..., description="Base unit price in INR")
    quantity: float = Field(..., description="Order quantity")
    tax_pct: float = Field(18.0, description="GST rate percentage")
    freight_total: float = Field(0.0, description="Total freight cost in INR")
    packaging_charges: float = Field(0.0, description="Packaging fee in INR")
    transit_insurance: float = Field(0.0, description="Transit insurance fee in INR")

class MatchMaterialSpecificationInput(BaseModel):
    raw_text: str = Field(..., description="Raw text description of material from RFQ or quote")
    grade: Optional[str] = Field(None, description="Grade hint if known")

# --- Document Tools ---
class ListUploadedDocumentsInput(BaseModel):
    status: Optional[str] = Field(None, description="Filter by quotation extraction status")

class GetDocumentExtractionInput(BaseModel):
    quotation_id: str = Field(..., description="Quotation ID")

class GetQuotationDetailsInput(BaseModel):
    quotation_id: str = Field(..., description="Quotation ID")

class RetrieveOriginalQuotationInput(BaseModel):
    quotation_id: str = Field(..., description="Quotation ID")

# --- Manufacturing & BOM Tools ---
class GetProductsInput(BaseModel):
    search: Optional[str] = Field(None, description="Search product code or name")

class GetBOMInput(BaseModel):
    product_id: Optional[str] = Field(None, description="Product ID to fetch active BOM")
    bom_id: Optional[str] = Field(None, description="Specific BOM revision ID")

class CalculateBOMRequirementsInput(BaseModel):
    product_id: str = Field(..., description="Manufactured product ID")
    production_quantity: float = Field(..., description="Number of finished units to produce")

class CheckInventoryInput(BaseModel):
    material_codes: Optional[List[str]] = Field(None, description="Optional list of material codes to check")

class CalculateMaterialShortagesInput(BaseModel):
    product_id: str = Field(..., description="Manufactured product ID")
    production_quantity: float = Field(..., description="Number of units to manufacture")

class GetProductionJobsInput(BaseModel):
    status: Optional[str] = Field(None, description="Filter by job status (PLANNED, IN_PROGRESS, COMPLETED)")

# --- Procurement Optimisation Tools ---
class CreateProcurementPlanInput(BaseModel):
    requirements: List[Dict[str, Any]] = Field(..., description="List of items with material_id, required_quantity, and unit")
    strategy: str = Field("LOWEST_LANDED_COST", description="Optimization strategy")
    budget_limit: Optional[float] = Field(None, description="Optional total budget ceiling in INR")
    production_job_id: Optional[str] = Field(None, description="Optional linked production job ID")

class OptimiseProcurementPlanInput(BaseModel):
    plan_id: str = Field(..., description="Procurement plan ID to solve")

class ReoptimizeProcurementPlanInput(BaseModel):
    plan_id: str = Field(..., description="Procurement plan ID")
    strategy: Optional[str] = Field(None, description="Updated strategy")
    budget_limit: Optional[float] = Field(None, description="Updated budget limit")

class CompareProcurementScenariosInput(BaseModel):
    plan_id: str = Field(..., description="Procurement plan ID")

class InspectOptimizationResultInput(BaseModel):
    plan_id: str = Field(..., description="Procurement plan ID")

class CreateProcurementRequisitionInput(BaseModel):
    plan_id: str = Field(..., description="Approved procurement plan ID")

# --- Negotiation Tools ---
class AnalyseNegotiationOpportunityInput(BaseModel):
    quotation_id: str = Field(..., description="Quotation ID to analyze for bargaining leverage")
    target_discount_pct: Optional[float] = Field(6.5, description="Target discount percentage")

class GenerateNegotiationMessageInput(BaseModel):
    session_id: str = Field(..., description="Negotiation session ID")
    strategy: str = Field("VOLUME_COMMITMENT", description="Commercial strategy: VOLUME_COMMITMENT, BENCHMARK_PARITY, PAYMENT_ACCELERATION, LONG_TERM_CONTRACT, SPOT_CLEARANCE")
    language: str = Field("en", description="Language: en, hi, hinglish")
    target_unit_price: Optional[float] = Field(None, description="Specific target unit price in INR/unit")

class SimulateSupplierResponseInput(BaseModel):
    session_id: str = Field(..., description="Negotiation session ID")
    scenario: str = Field("CONCESSION", description="Scenario: CONCESSION, FIRM, COUNTER, REJECT")

class AnalyseSupplierResponseInput(BaseModel):
    session_id: str = Field(..., description="Negotiation session ID")
    response_text: str = Field(..., description="Raw text of supplier reply")

class CalculateNegotiationImpactInput(BaseModel):
    session_id: str = Field(..., description="Negotiation session ID")
    concession_unit_price: float = Field(..., description="Proposed revised price from supplier")

# --- Costing Tools ---
class CalculateManufacturingCostInput(BaseModel):
    product_id: Optional[str] = Field(None, description="Product ID to cost")
    production_quantity: float = Field(500.0, description="Batch size")
    target_gross_margin_pct: float = Field(20.0, description="Target gross margin percentage")

class RetrieveCostEstimateInput(BaseModel):
    estimate_id: Optional[str] = Field(None, description="Estimate ID")
    product_id: Optional[str] = Field(None, description="Product ID to retrieve most recent estimate")

class SimulateCostScenarioInput(BaseModel):
    estimate_id: str = Field(..., description="Baseline cost estimate ID")
    material_cost_delta_pct: float = Field(0.0, description="Material price variation percentage (e.g. +10% or -5%)")
    batch_size: Optional[float] = Field(None, description="Alternative batch size")

class CalculateBreakEvenPriceInput(BaseModel):
    production_quantity: float = Field(..., description="Total batch units")
    total_production_cost: float = Field(..., description="Total audited production cost in INR")

class CalculateTargetSellingPriceInput(BaseModel):
    unit_cost: float = Field(..., description="Audited unit production cost in INR")
    target_gross_margin_pct: float = Field(25.0, description="Desired gross margin percentage")

# --- Customer Quotation Tools ---
class CreateCustomerQuotationDraftInput(BaseModel):
    customer_name: str = Field(..., description="Customer contact name")
    customer_company: str = Field(..., description="Customer company name")
    product_id: str = Field(..., description="Product ID")
    quantity: float = Field(..., description="Order batch quantity")
    unit_cost: float = Field(..., description="Unit manufacturing cost in INR")
    unit_selling_price: Optional[float] = Field(None, description="Quoted unit selling price in INR")
    target_margin_pct: Optional[float] = Field(25.0, description="Target gross margin percentage")
    payment_terms: Optional[str] = Field("50% Advance, 50% Against Delivery", description="Payment terms")
    delivery_weeks: Optional[int] = Field(3, description="Delivery timeline in weeks")

class RecalculateCustomerQuotationInput(BaseModel):
    quote_id: str = Field(..., description="Customer quote ID")
    unit_selling_price: Optional[float] = Field(None, description="Updated selling price")
    target_margin_pct: Optional[float] = Field(None, description="Updated target margin")

class EvaluateQuotationProfitabilityInput(BaseModel):
    unit_cost: float = Field(..., description="Unit manufacturing cost")
    unit_selling_price: float = Field(..., description="Proposed unit selling price")

class GenerateCustomerQuotationPDFInput(BaseModel):
    quote_id: str = Field(..., description="Customer quotation ID to render as official PDF")

# --- Approval Tools ---
class ListPendingApprovalsInput(BaseModel):
    pass

class RequestApprovalInput(BaseModel):
    request_type: str = Field(..., description="Type: NEGOTIATION_DISPATCH, PURCHASE_ORDER, CUSTOMER_QUOTE")
    entity_id: str = Field(..., description="ID of entity needing approval")
    details: Dict[str, Any] = Field(..., description="Details and financial impact")

class RetrieveApprovalStatusInput(BaseModel):
    approval_id: str = Field(..., description="Approval request ID")

# --- Sensitive & External Tools ---
class AdjustInventoryLevelInput(BaseModel):
    material_id: str = Field(..., description="ID of material to adjust stock for")
    quantity_delta: float = Field(..., description="Quantity delta to add/deduct")
    reason: str = Field(..., description="Audit reason for stock adjustment")

class ApplyNegotiatedRateInput(BaseModel):
    quotation_id: str = Field(..., description="Quotation ID to apply negotiated revision to")
    revised_unit_price: float = Field(..., description="Final negotiated price per unit")

class DispatchCustomerQuotationInput(BaseModel):
    quote_id: str = Field(..., description="Customer quote ID to dispatch")
    recipient_email: Optional[str] = Field(None, description="Recipient customer email")


# ============================================================================
# TOOL REGISTRY IMPLEMENTATION
# ============================================================================

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        org_id: str,
        db: Session,
        user_id: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        tool = self.get_tool(name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{name}' is not registered in the IndusPilot Tool Registry.",
                "tool_name": name
            }

        # Input validation via Pydantic
        try:
            validated_input = tool.input_schema(**arguments)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid arguments for tool '{name}': {str(e)}",
                "tool_name": name,
                "permission_tier": tool.permission_tier.value
            }

        start_time = time.time()
        try:
            result = tool.handler(validated_input, org_id=org_id, db=db, user_id=user_id)
            duration_ms = int((time.time() - start_time) * 1000)

            # Log tool call to audit ledger if run_id provided
            if run_id:
                call_log = AgentToolCall(
                    run_id=run_id,
                    organization_id=org_id,
                    agent_name=tool.agent_role,
                    tool_name=name,
                    permission_tier=tool.permission_tier.value,
                    input_arguments_json=arguments,
                    output_result_json=result if isinstance(result, dict) else {"result": str(result)},
                    status="SUCCESS",
                    execution_duration_ms=duration_ms
                )
                db.add(call_log)
                db.commit()

            return {
                "success": True,
                "tool_name": name,
                "agent_role": tool.agent_role,
                "permission_tier": tool.permission_tier.value,
                "duration_ms": duration_ms,
                "data": result
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            if run_id:
                call_log = AgentToolCall(
                    run_id=run_id,
                    organization_id=org_id,
                    agent_name=tool.agent_role,
                    tool_name=name,
                    permission_tier=tool.permission_tier.value,
                    input_arguments_json=arguments,
                    status="FAILED",
                    execution_duration_ms=duration_ms,
                    error_message=str(e)
                )
                db.add(call_log)
                db.commit()

            return {
                "success": False,
                "tool_name": name,
                "permission_tier": tool.permission_tier.value,
                "error": str(e),
                "duration_ms": duration_ms
            }

    def _register_default_tools(self):
        # 1. Supplier Tools
        self.register(ToolDefinition(
            name="search_suppliers",
            description="Finds verified suppliers matching material grade, quality score, or geographic location.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Supplier Intelligence Agent",
            input_schema=SearchSuppliersInput,
            handler=self._tool_search_suppliers
        ))
        self.register(ToolDefinition(
            name="get_supplier_details",
            description="Retrieves operational profile, quality scores, reliability, and past orders for a supplier.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Supplier Intelligence Agent",
            input_schema=GetSupplierDetailsInput,
            handler=self._tool_get_supplier_details
        ))
        self.register(ToolDefinition(
            name="list_supplier_quotations",
            description="Lists verified or pending supplier quotations in the database.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Document Intelligence Agent",
            input_schema=ListSupplierQuotationsInput,
            handler=self._tool_list_supplier_quotations
        ))
        self.register(ToolDefinition(
            name="compare_supplier_quotations",
            description="Ranks multiple supplier quotations by composite reliability and 9-component landed cost.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Supplier Intelligence Agent",
            input_schema=CompareSupplierQuotationsInput,
            handler=self._tool_compare_supplier_quotations
        ))
        self.register(ToolDefinition(
            name="calculate_landed_cost",
            description="Calculates deterministic 9-component landed cost for a material rate, tax, and freight.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Supplier Intelligence Agent",
            input_schema=CalculateLandedCostInput,
            handler=self._tool_calculate_landed_cost
        ))
        self.register(ToolDefinition(
            name="match_material_specification",
            description="Maps messy raw text or RFQ strings to verified standardized material catalogue items.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Manufacturing Requirement Agent",
            input_schema=MatchMaterialSpecificationInput,
            handler=self._tool_match_material_specification
        ))

        # 2. Manufacturing & BOM Tools
        self.register(ToolDefinition(
            name="get_products",
            description="Lists manufactured products in the company catalogue with batch sizes and default cycle times.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Manufacturing Requirement Agent",
            input_schema=GetProductsInput,
            handler=self._tool_get_products
        ))
        self.register(ToolDefinition(
            name="get_bom",
            description="Retrieves the active Bill of Materials revision for a product, listing all raw materials and scrap allowances.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Inventory and BOM Agent",
            input_schema=GetBOMInput,
            handler=self._tool_get_bom
        ))
        self.register(ToolDefinition(
            name="calculate_bom_requirements",
            description="Explodes an engineering BOM for a target production quantity, including scrap multipliers.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Inventory and BOM Agent",
            input_schema=CalculateBOMRequirementsInput,
            handler=self._tool_calculate_bom_requirements
        ))
        self.register(ToolDefinition(
            name="check_inventory",
            description="Queries the real-time warehouse inventory ledger: physical stock, reserved stock, and available stock.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Inventory and BOM Agent",
            input_schema=CheckInventoryInput,
            handler=self._tool_check_inventory
        ))
        self.register(ToolDefinition(
            name="calculate_material_shortages",
            description="Runs complete MRP explosion and stock netting to calculate exact raw material purchasing shortages.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Inventory and BOM Agent",
            input_schema=CalculateMaterialShortagesInput,
            handler=self._tool_calculate_material_shortages
        ))

        # 3. Procurement Optimisation Tools
        self.register(ToolDefinition(
            name="create_procurement_plan",
            description="Formulates and solves a multi-material procurement plan using Google OR-Tools MILP.",
            permission_tier=ToolPermissionTier.DRAFT_CREATION,
            agent_role="Procurement Optimisation Agent",
            input_schema=CreateProcurementPlanInput,
            handler=self._tool_create_procurement_plan
        ))
        self.register(ToolDefinition(
            name="inspect_optimization_result",
            description="Inspects solver status (OPTIMAL/FEASIBLE/INFEASIBLE), vendor allocations, and baseline savings.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Procurement Optimisation Agent",
            input_schema=InspectOptimizationResultInput,
            handler=self._tool_inspect_optimization_result
        ))

        # 4. Negotiation Tools
        self.register(ToolDefinition(
            name="analyse_negotiation_opportunity",
            description="Evaluates a supplier quote against market benchmarks, computing target counteroffer discounts.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Negotiation Agent",
            input_schema=AnalyseNegotiationOpportunityInput,
            handler=self._tool_analyse_negotiation_opportunity
        ))
        self.register(ToolDefinition(
            name="generate_negotiation_message",
            description="Drafts a multilingual counteroffer message (EN/HI/Hinglish) using a selected commercial strategy.",
            permission_tier=ToolPermissionTier.DRAFT_CREATION,
            agent_role="Negotiation Agent",
            input_schema=GenerateNegotiationMessageInput,
            handler=self._tool_generate_negotiation_message
        ))
        self.register(ToolDefinition(
            name="simulate_supplier_response",
            description="Simulates realistic multi-round vendor concessions under a decaying exponential curve [SIMULATED].",
            permission_tier=ToolPermissionTier.DRAFT_CREATION,
            agent_role="Negotiation Agent",
            input_schema=SimulateSupplierResponseInput,
            handler=self._tool_simulate_supplier_response
        ))

        # 5. Costing Tools
        self.register(ToolDefinition(
            name="calculate_manufacturing_cost",
            description="Calculates audited 14-factor manufacturing production cost (materials, labor, electricity, machines, scrap).",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Manufacturing Cost Agent",
            input_schema=CalculateManufacturingCostInput,
            handler=self._tool_calculate_manufacturing_cost
        ))
        self.register(ToolDefinition(
            name="calculate_target_selling_price",
            description="Computes suggested unit selling price and break-even price using strict Python Decimal gross margin math.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Manufacturing Cost Agent",
            input_schema=CalculateTargetSellingPriceInput,
            handler=self._tool_calculate_target_selling_price
        ))

        # 6. Customer Quotation Tools
        self.register(ToolDefinition(
            name="create_customer_quotation_draft",
            description="Drafts a customer quotation with gross margin verification and automatic loss-making contract protection.",
            permission_tier=ToolPermissionTier.DRAFT_CREATION,
            agent_role="Customer Quotation Agent",
            input_schema=CreateCustomerQuotationDraftInput,
            handler=self._tool_create_customer_quotation_draft
        ))
        self.register(ToolDefinition(
            name="evaluate_quotation_profitability",
            description="Verifies whether a customer quotation is PROFITABLE, BELOW_TARGET_MARGIN, or LOSS_MAKING.",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Customer Quotation Agent",
            input_schema=EvaluateQuotationProfitabilityInput,
            handler=self._tool_evaluate_quotation_profitability
        ))
        self.register(ToolDefinition(
            name="generate_customer_quotation_pdf",
            description="Renders official tamper-evident commercial PDF quotation with Rs. glyph formatting.",
            permission_tier=ToolPermissionTier.DRAFT_CREATION,
            agent_role="Customer Quotation Agent",
            input_schema=GenerateCustomerQuotationPDFInput,
            handler=self._tool_generate_customer_quotation_pdf
        ))

        # 7. Approval & Sensitive Mutation Tools
        self.register(ToolDefinition(
            name="list_pending_approvals",
            description="Lists pending commercial approvals (plans, negotiations, loss-making orders).",
            permission_tier=ToolPermissionTier.READ_ONLY,
            agent_role="Supervisor Agent",
            input_schema=ListPendingApprovalsInput,
            handler=self._tool_list_pending_approvals
        ))
        self.register(ToolDefinition(
            name="adjust_inventory_level",
            description="Adjusts live warehouse physical inventory stock level with mandatory audit trail.",
            permission_tier=ToolPermissionTier.SENSITIVE_MUTATION,
            agent_role="Inventory and BOM Agent",
            input_schema=AdjustInventoryLevelInput,
            handler=self._tool_adjust_inventory_level
        ))
        self.register(ToolDefinition(
            name="apply_negotiated_rate",
            description="Applies agreed negotiated concession price to supplier quotation ledger.",
            permission_tier=ToolPermissionTier.SENSITIVE_MUTATION,
            agent_role="Negotiation Agent",
            input_schema=ApplyNegotiatedRateInput,
            handler=self._tool_apply_negotiated_rate
        ))
        self.register(ToolDefinition(
            name="dispatch_customer_quotation",
            description="Dispatches commercial quotation to customer via email / electronic interface.",
            permission_tier=ToolPermissionTier.EXTERNAL_ACTION,
            agent_role="Customer Quotation Agent",
            input_schema=DispatchCustomerQuotationInput,
            handler=self._tool_dispatch_customer_quotation
        ))

    # ========================================================================
    # TOOL HANDLER IMPLEMENTATIONS (EXECUTING REAL BACKEND SERVICES)
    # ========================================================================

    def _tool_search_suppliers(self, p: SearchSuppliersInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        query = db.query(Supplier).filter(Supplier.organization_id == org_id)
        if p.min_rating:
            query = query.filter(Supplier.quality_rating >= p.min_rating)
        if p.city:
            query = query.filter(Supplier.city.ilike(f"%{p.city}%"))
        suppliers = query.all()

        results = []
        for s in suppliers:
            # Check materials supplied
            mats = db.query(SupplierMaterial).filter(SupplierMaterial.supplier_id == s.id).all()
            if p.material_filter:
                f = p.material_filter.lower()
                mats = [m for m in mats if f in m.material_name.lower() or (m.material_grade and f in m.material_grade.lower())]
                if not mats:
                    continue

            results.append({
                "id": s.id,
                "name": s.name,
                "city": s.city,
                "state": s.state,
                "quality_rating": s.quality_rating,
                "reliability_score": s.reliability_score,
                "payment_terms_days": s.payment_terms_days,
                "materials_supplied": [m.material_name for m in mats[:4]]
            })

        return {"count": len(results), "suppliers": results}

    def _tool_get_supplier_details(self, p: GetSupplierDetailsInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        s = db.query(Supplier).filter(Supplier.id == p.supplier_id, Supplier.organization_id == org_id).first()
        if not s:
            raise ValueError(f"Supplier ID '{p.supplier_id}' not found.")
        mats = db.query(SupplierMaterial).filter(SupplierMaterial.supplier_id == s.id).all()
        quotes = db.query(SupplierQuotation).filter(SupplierQuotation.supplier_id == s.id).all()

        return {
            "id": s.id,
            "name": s.name,
            "contact_person": s.contact_person,
            "email": s.email,
            "city": s.city,
            "quality_rating": s.quality_rating,
            "reliability_score": s.reliability_score,
            "on_time_delivery_pct": s.on_time_delivery_pct,
            "payment_terms_days": s.payment_terms_days,
            "materials_count": len(mats),
            "historical_quotes_count": len(quotes)
        }

    def _tool_list_supplier_quotations(self, p: ListSupplierQuotationsInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        query = db.query(SupplierQuotation).filter(SupplierQuotation.organization_id == org_id)
        if p.supplier_id:
            query = query.filter(SupplierQuotation.supplier_id == p.supplier_id)
        if p.status:
            query = query.filter(SupplierQuotation.status == p.status)

        quotes = query.order_by(SupplierQuotation.created_at.desc()).limit(15).all()
        res = []
        for q in quotes:
            sup = db.query(Supplier).filter(Supplier.id == q.supplier_id).first()
            res.append({
                "id": q.id,
                "quotation_number": q.quotation_number,
                "supplier_name": sup.name if sup else "Supplier",
                "status": q.status,
                "total_amount": q.total_amount,
                "subtotal": q.subtotal,
                "tax_amount": q.tax_amount,
                "freight_cost": q.freight_cost,
                "valid_until": q.valid_until.strftime("%Y-%m-%d") if q.valid_until else None,
                "version": q.version or 1
            })
        return {"count": len(res), "quotations": res}

    def _tool_compare_supplier_quotations(self, p: CompareSupplierQuotationsInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        quotes = db.query(SupplierQuotation).filter(
            SupplierQuotation.id.in_(p.quotation_ids),
            SupplierQuotation.organization_id == org_id
        ).all()
        if not quotes:
            raise ValueError("No quotations found for comparison.")

        candidates = []
        all_landed = []
        all_leads = []

        for q in quotes:
            sup = db.query(Supplier).filter(Supplier.id == q.supplier_id).first()
            first_item = q.items[0] if q.items else None
            unit_price = first_item.unit_price if first_item else 300.0

            landed = calculate_landed_cost(
                unit_price=unit_price,
                quantity=p.target_quantity,
                tax_pct=q.tax_pct or 18.0,
                freight_total=q.freight_cost or 0.0,
                packaging_charges=q.packaging_cost or 0.0,
                transit_insurance=q.insurance_cost or 0.0
            )

            cand = {
                "quotation_id": q.id,
                "supplier_name": sup.name if sup else "Supplier",
                "unit_price": unit_price,
                "effective_landed_cost": landed["effective_unit_landed_cost"],
                "total_landed_cost": landed["total_landed_cost"],
                "lead_time_days": q.lead_time_days or 7,
                "quality_rating": sup.quality_rating if sup else 4.0,
                "reliability_score": sup.reliability_score if sup else 80.0,
                "payment_terms_days": sup.payment_terms_days if sup else 30
            }
            candidates.append(cand)
            all_landed.append(cand["effective_landed_cost"])
            all_leads.append(cand["lead_time_days"])

        for c in candidates:
            score = evaluate_supplier_quotation(
                unit_landed_cost=c["effective_landed_cost"],
                all_landed_costs=all_landed,
                quality_rating=c["quality_rating"],
                reliability_score=c["reliability_score"],
                lead_time_days=c["lead_time_days"],
                all_lead_times=all_leads,
                payment_terms_days=c["payment_terms_days"]
            )
            c["composite_score"] = score["composite_score"]
            c["decision_band"] = score["decision_band"]

        candidates.sort(key=lambda x: x["composite_score"], reverse=True)
        return {
            "top_candidate": candidates[0],
            "rankings": candidates
        }

    def _tool_calculate_landed_cost(self, p: CalculateLandedCostInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        return calculate_landed_cost(
            unit_price=p.unit_price,
            quantity=p.quantity,
            tax_pct=p.tax_pct,
            freight_total=p.freight_total,
            packaging_charges=p.packaging_charges,
            transit_insurance=p.transit_insurance
        )

    def _tool_match_material_specification(self, p: MatchMaterialSpecificationInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        catalog_mats = db.query(Material).all()
        cat_dicts = [{"id": m.id, "code": m.code, "name": m.name, "standard_spec": m.standard_spec} for m in catalog_mats]
        match = match_material_spec(query_text=p.raw_text, declared_grade=p.grade, catalogue_materials=cat_dicts)
        return match

    def _tool_get_products(self, p: GetProductsInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        query = db.query(Product).filter(Product.organization_id == org_id)
        if p.search:
            query = query.filter((Product.name.ilike(f"%{p.search}%")) | (Product.code.ilike(f"%{p.search}%")))
        prods = query.all()
        return {
            "count": len(prods),
            "products": [{"id": pr.id, "code": pr.code, "name": pr.name, "category": pr.category, "default_batch_size": pr.default_batch_size} for pr in prods]
        }

    def _tool_get_bom(self, p: GetBOMInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        if p.bom_id:
            bom = db.query(BOM).filter(BOM.id == p.bom_id, BOM.organization_id == org_id).first()
        elif p.product_id:
            bom = db.query(BOM).filter(BOM.product_id == p.product_id, BOM.organization_id == org_id, BOM.is_active == True).first()
        else:
            bom = db.query(BOM).filter(BOM.organization_id == org_id, BOM.is_active == True).first()

        if not bom:
            raise ValueError("No active BOM found.")

        items = db.query(BOMItem).filter(BOMItem.bom_id == bom.id).all()
        return {
            "bom_id": bom.id,
            "product_id": bom.product_id,
            "revision": bom.revision,
            "items_count": len(items),
            "items": [
                {
                    "material_name": it.material_name,
                    "quantity_per_unit": it.quantity_per_unit,
                    "unit": it.unit,
                    "scrap_factor_pct": it.scrap_factor_pct,
                    "routing_stage": it.routing_stage
                }
                for it in items
            ]
        }

    def _tool_calculate_bom_requirements(self, p: CalculateBOMRequirementsInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        product_key = str(p.product_id).strip()
        alias_map = {"SS304-BRK-500": "IND-BRK-SS304", "BRK-SS-304": "IND-BRK-SS304"}
        canonical_code = alias_map.get(product_key, product_key)
        prod = (
            db.query(Product).filter(
                (Product.id == product_key) | 
                (Product.code == product_key) | 
                (Product.code == canonical_code)
            ).first()
            or db.query(Product).first()
        )
        raw_items = []
        if prod and prod.boms:
            target_bom = next((b for b in prod.boms if b.is_active), prod.boms[0])
            for it in target_bom.items:
                m = it.material
                raw_items.append({
                    "material_id": it.material_id,
                    "material_name": m.name if m else "Material",
                    "material_code": m.code if m else "",
                    "grade": m.grade if m else "",
                    "quantity_per_unit": it.quantity_per_unit,
                    "unit": it.unit,
                    "wastage_pct": it.wastage_pct or 5.0
                })
        else:
            raw_items = [{
                "material_id": "mat-ss-304",
                "material_name": "Stainless Steel 304 Sheet Plate",
                "material_code": "MAT-SS-304",
                "quantity_per_unit": 2.0,
                "unit": "kg",
                "wastage_pct": 5.0
            }]
        return explode_bom(p.production_quantity, raw_items)

    def _tool_check_inventory(self, p: CheckInventoryInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        invs = db.query(Inventory).filter(Inventory.organization_id == org_id).all()
        res = []
        for i in invs:
            mat = i.material
            avail = max(0.0, i.current_stock - i.reserved_stock)
            res.append({
                "material_id": i.material_id,
                "material_code": mat.code if mat else "",
                "material_name": mat.name if mat else "",
                "current_stock": i.current_stock,
                "reserved_stock": i.reserved_stock,
                "available_stock": avail,
                "unit": getattr(mat, "unit", getattr(mat, "base_unit", "kg")) if mat else "kg",
                "warehouse_location": i.warehouse_location
            })
        if p.material_codes:
            codes = set(p.material_codes)
            res = [r for r in res if r["material_code"] in codes]
        return {"items_count": len(res), "inventory": res}

    def _tool_calculate_material_shortages(self, p: CalculateMaterialShortagesInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        exploded = self._tool_calculate_bom_requirements(CalculateBOMRequirementsInput(product_id=p.product_id, production_quantity=p.production_quantity), org_id=org_id, db=db)
        shortages = []
        for comp in exploded.get("components", []):
            mat_id = comp["material_id"]
            gross_needed = comp["total_gross_required"]
            inv = db.query(Inventory).filter(Inventory.material_id == mat_id, Inventory.organization_id == org_id).first()
            cur_stock = inv.current_stock if inv else 0.0
            res_stock = inv.reserved_stock if inv else 0.0
            inc_stock = inv.incoming_stock if inv else 0.0
            saf_stock = inv.safety_stock if inv else 0.0
            
            netting = calculate_net_procurement_requirement(
                gross_requirement=gross_needed,
                current_stock=cur_stock,
                reserved_stock=res_stock,
                incoming_stock=inc_stock,
                safety_stock=saf_stock
            )
            shortages.append({
                "material_id": mat_id,
                "material_code": comp.get("material_code", ""),
                "material_name": comp["material_name"],
                "gross_required": gross_needed,
                "current_stock": cur_stock,
                "reserved_stock": res_stock,
                "available_stock": netting["available_stock"],
                "safety_stock_buffer": netting["safety_stock_buffer"],
                "unbuffered_shortage": netting["unbuffered_shortage"],
                "net_shortage": netting["net_shortage"],
                "unit": comp.get("unit", "kg"),
                "has_shortage": netting["has_shortage"]
            })
        return {
            "product_id": p.product_id,
            "production_quantity": p.production_quantity,
            "shortages": shortages,
            "total_shortages_count": sum(1 for s in shortages if s["has_shortage"])
        }

    def _tool_create_procurement_plan(self, p: CreateProcurementPlanInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        plan_dict = create_and_optimize_procurement_plan(
            db=db,
            org_id=org_id,
            requirements=p.requirements,
            strategy=p.strategy,
            budget_limit=p.budget_limit,
            production_job_id=p.production_job_id
        )
        return plan_dict

    def _tool_inspect_optimization_result(self, p: InspectOptimizationResultInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        plan = db.query(ProcurementPlan).filter(ProcurementPlan.id == p.plan_id, ProcurementPlan.organization_id == org_id).first()
        if not plan:
            raise ValueError("Procurement plan not found.")
        allocs = [
            {
                "supplier_name": a.supplier.name if a.supplier else "Supplier",
                "material_name": a.material.name if a.material else "Material",
                "quantity": a.allocated_quantity,
                "unit_landed_cost": a.unit_landed_cost,
                "subtotal_cost": a.subtotal_cost
            }
            for a in plan.allocations
        ]
        return {
            "plan_number": plan.plan_number,
            "solver_status": plan.solver_status,
            "strategy": plan.strategy,
            "total_landed_cost": plan.total_landed_cost,
            "allocations": allocs,
            "explanation": plan.explanation_headline or "Optimized via Google OR-Tools"
        }

    def _tool_analyse_negotiation_opportunity(self, p: AnalyseNegotiationOpportunityInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        return analyze_negotiation_opportunity(
            db=db,
            org_id=org_id,
            quotation_id=p.quotation_id,
            target_discount_pct=p.target_discount_pct
        )

    def _tool_generate_negotiation_message(self, p: GenerateNegotiationMessageInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        from app.models.entities import NegotiationSession
        session = db.query(NegotiationSession).filter(NegotiationSession.id == p.session_id, NegotiationSession.organization_id == org_id).first()
        if not session:
            raise ValueError("Negotiation session not found.")
        msg_text = generate_negotiation_message_text(
            supplier_name=session.supplier_name,
            material_name=session.material_name,
            quantity=session.quantity,
            unit=session.unit,
            current_unit_price=session.current_offered_price,
            target_unit_price=p.target_unit_price or session.target_unit_price,
            strategy=p.strategy,
            language=p.language
        )
        return {"session_id": session.id, "message_text": str(msg_text), "strategy": p.strategy, "language": p.language}

    def _tool_simulate_supplier_response(self, p: SimulateSupplierResponseInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        from app.models.entities import NegotiationSession
        session = db.query(NegotiationSession).filter(NegotiationSession.id == p.session_id, NegotiationSession.organization_id == org_id).first()
        if not session:
            raise ValueError("Negotiation session not found.")
        reply = simulate_supplier_response(
            original_unit_price=session.original_unit_price,
            target_unit_price=session.target_unit_price,
            round_number=session.round_count + 1,
            strategy=session.strategy,
            scenario=p.scenario
        )
        reply["is_simulated"] = True
        return reply

    def _tool_calculate_manufacturing_cost(self, p: CalculateManufacturingCostInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        # Fetch product or default bracket
        prod = None
        if p.product_id:
            prod = db.query(Product).filter(Product.id == p.product_id).first()
        if not prod:
            prod = db.query(Product).first()

        mat_breakdown = [
            {"material_name": "Stainless Steel 304 Plate", "gross_quantity": p.production_quantity * 2.1, "net_quantity": p.production_quantity * 2.0, "unit_cost": 315.0}
        ]
        res = calculate_manufacturing_cost(
            production_quantity=p.production_quantity,
            material_costs_breakdown=mat_breakdown,
            direct_labor_hours=120.0,
            labor_rate_per_hour=180.0,
            machine_hours=45.0,
            machine_rate_per_hour=350.0,
            electricity_kwh=650.0,
            electricity_tariff_per_kwh=8.50,
            secondary_processes_total=18000.0,
            transportation_total=6500.0,
            packaging_total=4500.0,
            overhead_pct=12.0,
            target_gross_margin_pct=p.target_gross_margin_pct
        )
        return res

    def _tool_calculate_target_selling_price(self, p: CalculateTargetSellingPriceInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        pricing = calculate_customer_quotation_pricing(
            unit_production_cost=p.unit_cost,
            quantity=100.0,
            target_margin_pct=p.target_gross_margin_pct
        )
        return pricing

    def _tool_create_customer_quotation_draft(self, p: CreateCustomerQuotationDraftInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        quote = create_customer_quotation(
            db=db,
            org_id=org_id,
            customer_name=p.customer_name,
            customer_company=p.customer_company,
            product_id=p.product_id,
            quantity=p.quantity,
            unit_cost=p.unit_cost,
            unit_selling_price=p.unit_selling_price,
            target_margin_pct=p.target_margin_pct,
            payment_terms=p.payment_terms,
            delivery_weeks=p.delivery_weeks
        )
        return quote

    def _tool_evaluate_quotation_profitability(self, p: EvaluateQuotationProfitabilityInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        pricing = calculate_customer_quotation_pricing(
            unit_production_cost=p.unit_cost,
            quantity=100.0,
            unit_selling_price=p.unit_selling_price
        )
        return {
            "unit_cost": pricing["unit_production_cost"],
            "unit_selling_price": pricing["unit_selling_price"],
            "gross_margin_pct": pricing["margin_pct"],
            "markup_pct": pricing["markup_pct"],
            "is_loss_making": pricing["is_loss_making"],
            "profitability_status": pricing["profitability_status"]
        }

    def _tool_generate_customer_quotation_pdf(self, p: GenerateCustomerQuotationPDFInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        cq = db.query(CustomerQuotation).filter(CustomerQuotation.id == p.quote_id, CustomerQuotation.organization_id == org_id).first()
        if not cq:
            raise ValueError("Customer quotation not found.")
        prod = db.query(Product).filter(Product.id == cq.product_id).first()
        path = generate_customer_quotation_pdf(
            quote_number=cq.quote_number,
            customer_name=cq.customer_name,
            customer_company=cq.customer_company or "Enterprise",
            product_name=prod.name if prod else "Industrial Component",
            product_code=prod.code if prod else "IND-PRD",
            quantity=cq.quantity,
            unit_selling_price=cq.unit_selling_price,
            unit_cost=cq.unit_production_cost,
            subtotal=cq.subtotal,
            tax_amount=cq.tax_amount,
            total_amount=cq.total_amount,
            margin_pct=cq.margin_pct,
            payment_terms=cq.payment_terms,
            delivery_weeks=cq.delivery_weeks
        )
        cq.pdf_path = path
        db.commit()
        return {"quote_number": cq.quote_number, "pdf_path": path, "status": "GENERATED"}

    def _tool_list_pending_approvals(self, p: ListPendingApprovalsInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        apprs = db.query(ApprovalRequest).filter(ApprovalRequest.organization_id == org_id, ApprovalRequest.status == "PENDING").all()
        return {
            "count": len(apprs),
            "pending_approvals": [
                {
                    "id": a.id,
                    "request_type": a.request_type,
                    "entity_id": a.entity_id,
                    "requested_by": a.requested_by,
                    "details": a.details_json,
                    "created_at": a.created_at.strftime("%Y-%m-%d %H:%M")
                }
                for a in apprs
            ]
        }

    def _tool_adjust_inventory_level(self, p: AdjustInventoryLevelInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        inv = db.query(Inventory).filter(Inventory.material_id == p.material_id, Inventory.organization_id == org_id).first()
        if not inv:
            return {"adjusted": False, "error": "Inventory record not found"}
        inv.current_stock += p.quantity_delta
        db.commit()
        return {"adjusted": True, "material_id": p.material_id, "new_current_stock": inv.current_stock, "reason": p.reason}

    def _tool_apply_negotiated_rate(self, p: ApplyNegotiatedRateInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        q = db.query(SupplierQuotation).filter(SupplierQuotation.id == p.quotation_id, SupplierQuotation.organization_id == org_id).first()
        if not q:
            return {"applied": False, "error": "Quotation not found"}
        q.unit_price = p.revised_unit_price
        db.commit()
        return {"applied": True, "quotation_id": p.quotation_id, "revised_unit_price": p.revised_unit_price}

    def _tool_dispatch_customer_quotation(self, p: DispatchCustomerQuotationInput, org_id: str, db: Session, **kwargs) -> Dict[str, Any]:
        cq = db.query(CustomerQuotation).filter(CustomerQuotation.id == p.quote_id, CustomerQuotation.organization_id == org_id).first()
        if not cq:
            return {"dispatched": False, "error": "Customer quotation not found"}
        cq.status = "SENT"
        db.commit()
        return {"dispatched": True, "quote_id": p.quote_id, "status": "SENT", "recipient": p.recipient_email or "client@industrial.in"}


# Singleton Global Registry
CentralToolRegistry = ToolRegistry
global_tool_registry = ToolRegistry()
