from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# --- Supplier Schemas ---
class SupplierCreate(BaseModel):
    name: str
    company_name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    postal_code: Optional[str] = None
    website: Optional[str] = None
    gst_number: Optional[str] = None
    category: str = "Primary Raw Materials"
    manufacturing_specialisation: Optional[str] = None
    credit_period_days: int = 30
    moq_general: float = 100.0
    capacity_monthly_tons: float = 50.0
    lead_time_days: int = 7
    quality_rating: float = 4.2
    reliability_score: float = 85.0
    on_time_delivery_pct: float = 90.0
    payment_terms_days: int = 30
    is_active: bool = True
    is_simulated: bool = False

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    website: Optional[str] = None
    gst_number: Optional[str] = None
    category: Optional[str] = None
    manufacturing_specialisation: Optional[str] = None
    credit_period_days: Optional[int] = None
    moq_general: Optional[float] = None
    capacity_monthly_tons: Optional[float] = None
    lead_time_days: Optional[int] = None
    quality_rating: Optional[float] = None
    reliability_score: Optional[float] = None
    on_time_delivery_pct: Optional[float] = None
    payment_terms_days: Optional[int] = None
    is_active: Optional[bool] = None

class SupplierOut(SupplierCreate):
    id: str
    organization_id: str
    total_historical_spend: float = 0.0
    total_orders_count: int = 0
    rejection_rate_pct: float = 0.5
    quotation_count: int = 0
    created_at: Optional[str] = None

# --- Material & Inventory ---
class MaterialCreate(BaseModel):
    code: str
    name: str
    category: str = "Sheet Metal"
    grade: Optional[str] = None
    specifications: Optional[str] = None
    manufacturing_forms: Optional[str] = "Sheet, Plate"
    unit: str = "kg"
    density_g_cm3: Optional[float] = None
    standard_cost: float = 0.0
    description: Optional[str] = None
    is_active: bool = True

class MaterialOut(MaterialCreate):
    id: str
    organization_id: str

class MaterialMatchRequest(BaseModel):
    raw_text: str
    grade: Optional[str] = None
    thickness_mm: Optional[float] = None
    dimensions: Optional[str] = None
    unit: Optional[str] = "kg"

class MaterialMatchCandidate(BaseModel):
    material_id: str
    code: str
    name: str
    grade: Optional[str] = None
    category: str
    standard_unit: str
    standard_cost: float
    similarity_score: float # 0.0 - 1.0
    confidence_band: str # EXACT, HIGH_CONFIDENCE, SUGGESTED, UNMATCHED
    match_reason: str

class MaterialMatchResponse(BaseModel):
    query_text: str
    best_match: Optional[MaterialMatchCandidate] = None
    candidates: List[MaterialMatchCandidate] = []
    auto_matched: bool = False

# --- Document Processing Schemas ---
class DocumentOut(BaseModel):
    id: str
    organization_id: str
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    filename: str
    file_type: str
    file_size: int
    processing_status: str
    validation_status: str
    status: str
    confidence_score: float
    error_message: Optional[str] = None
    created_at: Optional[str] = None

class InventoryOut(BaseModel):
    material_id: str
    material_code: str
    material_name: str
    unit: str
    current_stock: float
    reserved_stock: float
    available_stock: float
    incoming_stock: float
    safety_stock: float
    reorder_level: float
    warehouse_location: str
    status: str

# --- BOM & Product Catalogue Schemas ---
class ProductCreate(BaseModel):
    code: str
    name: str
    category: str = "Fabrication"
    description: Optional[str] = None
    manufacturing_process: Optional[str] = "CNC Machining & Sheet Fabrication"
    base_unit: str = "units"
    default_batch_size: float = 500.0
    estimated_duration_hours: float = 24.0
    is_active: bool = True

class ProductUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    manufacturing_process: Optional[str] = None
    base_unit: Optional[str] = None
    default_batch_size: Optional[float] = None
    estimated_duration_hours: Optional[float] = None
    is_active: Optional[bool] = None

class ProductOut(ProductCreate):
    id: str
    organization_id: str
    active_bom_id: Optional[str] = None
    active_bom_version: Optional[str] = None
    boms_count: int = 0
    components_count: int = 0
    created_at: Optional[str] = None

class BOMItemInput(BaseModel):
    material_id: str
    quantity_per_unit: float
    unit: str = "kg"
    wastage_pct: float = 5.0
    scrap_allowance_method: str = "ADDITIVE_SCRAP" # ADDITIVE_SCRAP, YIELD_BASED
    expected_yield_pct: float = 95.0
    process_stage: str = "Cutting & Forming"
    notes: Optional[str] = None

class BOMCreate(BaseModel):
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    product_id: Optional[str] = None
    name: str = "Primary Production BOM"
    category: str = "Fabrication"
    description: Optional[str] = None
    version: str = "v1.0"
    batch_quantity: float = 1.0
    scrap_allowance_method: str = "ADDITIVE_SCRAP"
    expected_yield_pct: float = 95.0
    notes: Optional[str] = None
    items: List[BOMItemInput]

class BOMRevisionRequest(BaseModel):
    new_version: str
    revision_notes: Optional[str] = None
    items: Optional[List[BOMItemInput]] = None

class BOMExplodeRequest(BaseModel):
    product_id: Optional[str] = None
    bom_id: Optional[str] = None
    production_quantity: float = 500.0
    custom_items: Optional[List[BOMItemInput]] = None

# --- Inventory Ledger Schemas ---
class StockReceiveRequest(BaseModel):
    material_id: str
    quantity: float
    unit: str = "kg"
    reference_id: Optional[str] = None
    source: Optional[str] = "Vendor Delivery"
    unit_cost: Optional[float] = None
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None

class StockIssueRequest(BaseModel):
    material_id: str
    quantity: float
    unit: str = "kg"
    reference_id: Optional[str] = None
    destination: Optional[str] = "Shop Floor"
    production_job_id: Optional[str] = None
    notes: Optional[str] = None
    allow_negative_stock: bool = False
    idempotency_key: Optional[str] = None

class StockReserveRequest(BaseModel):
    material_id: str
    quantity: float
    unit: str = "kg"
    production_job_id: Optional[str] = None
    notes: Optional[str] = None

class StockReleaseRequest(BaseModel):
    reservation_id: str
    notes: Optional[str] = None

class StockAdjustRequest(BaseModel):
    material_id: str
    new_physical_stock: float
    reason: str
    notes: Optional[str] = None

class AvailabilityCheckItem(BaseModel):
    material_id: str
    gross_quantity_required: float
    unit: str = "kg"

class StockAvailabilityCheckRequest(BaseModel):
    items: List[AvailabilityCheckItem]

# --- Production Job & MRP Schemas ---
class ProductionJobCreate(BaseModel):
    product_id: str
    bom_id: Optional[str] = None
    production_quantity: float = 500.0
    customer_order_ref: Optional[str] = None
    planned_start_date: Optional[str] = None
    target_completion_date: Optional[str] = None
    priority: str = "MEDIUM" # LOW, MEDIUM, HIGH, CRITICAL
    notes: Optional[str] = None

class ProductionJobUpdate(BaseModel):
    status: Optional[str] = None # DRAFT, PLANNED, MATERIAL_CHECKED, AWAITING_PROCUREMENT, READY_FOR_PRODUCTION, IN_PROGRESS, COMPLETED, CANCELLED
    priority: Optional[str] = None
    notes: Optional[str] = None
    planned_start_date: Optional[str] = None
    target_completion_date: Optional[str] = None

# --- Quotation & Comparison ---
class QuotationItemInput(BaseModel):
    material_name: str
    material_id: Optional[str] = None
    grade: Optional[str] = None
    thickness_mm: Optional[float] = None
    dimensions: Optional[str] = None
    quantity: float
    unit: str = "kg"
    unit_price: float
    moq: float = 1.0
    lead_time_days: int = 7
    line_total: float
    match_confidence: float = 0.0
    is_quarantined: bool = False
    quarantine_reason: Optional[str] = None

class QuotationConfirmRequest(BaseModel):
    supplier_id: Optional[str] = None
    supplier_name: str
    quotation_number: str
    quotation_date: Optional[str] = None
    document_id: Optional[str] = None
    subtotal: float
    tax_pct: float = 18.0
    tax_amount: float
    is_tax_inclusive: bool = False
    freight_cost: float = 0.0
    other_charges: float = 0.0
    total_amount: float
    currency: str = "INR"
    payment_terms: str = "30 Days Net"
    valid_until: Optional[str] = None
    review_notes: Optional[str] = None
    original_extracted_json: Optional[Dict[str, Any]] = None
    user_corrected_json: Optional[Dict[str, Any]] = None
    items: List[QuotationItemInput]

class SupplierCompareRequest(BaseModel):
    quotation_ids: Optional[List[str]] = None
    material_id: Optional[str] = None
    material_name: Optional[str] = None
    grade: Optional[str] = None
    thickness_mm: Optional[float] = None
    quantity: float = 800.0
    unit: str = "kg"
    delivery_deadline: Optional[str] = None
    budget_limit: Optional[float] = None
    weights: Optional[Dict[str, float]] = None
    allow_split_purchasing: bool = False
    save_comparison: bool = True

class ComparisonAnalyzeRequest(BaseModel):
    material_id: Optional[str] = None
    material_name: Optional[str] = "Stainless Steel 304 Sheet"
    grade: Optional[str] = None
    thickness_mm: Optional[float] = None
    quantity: float = 800.0
    unit: str = "kg"
    delivery_deadline: Optional[str] = None
    budget_limit: Optional[float] = None
    quotation_ids: Optional[List[str]] = None
    weights: Optional[Dict[str, float]] = None
    allow_split_purchasing: bool = False
    save_comparison: bool = True

class EligibilityCheckRequest(BaseModel):
    quotation_id: str
    material_name: str
    grade: Optional[str] = None
    thickness_mm: Optional[float] = None
    quantity: float = 800.0
    unit: str = "kg"
    delivery_deadline: Optional[str] = None
    max_lead_time_days: Optional[int] = None
    allow_split_purchasing: bool = False

class LandedCostCalculateRequest(BaseModel):
    unit_price: float
    quantity: float
    tax_pct: float = 18.0
    tax_treatment: Optional[str] = "TAX_EXCLUDED" # TAX_INCLUDED, TAX_EXCLUDED, NO_TAX, UNKNOWN
    is_tax_inclusive: Optional[bool] = None
    freight_total: float = 0.0
    packaging_total: float = 0.0
    other_charges_total: float = 0.0
    discount_pct: float = 0.0
    discount_amount: float = 0.0
    currency: str = "INR"
    base_currency: str = "INR"
    fx_rate_to_base: Optional[float] = None
    requested_quantity: Optional[float] = None

class PurchaseRequisitionCreate(BaseModel):
    material_id: str
    required_quantity: float
    unit: str = "kg"
    required_by_date: Optional[str] = None
    reason: str = "Production Order Shortage"
    budget_limit: Optional[float] = None
    selected_supplier_id: Optional[str] = None
    selected_quotation_id: Optional[str] = None
    estimated_total_cost: Optional[float] = None
    delivery_deadline: Optional[str] = None
    comparison_result_id: Optional[str] = None

# --- Costing ---
class MaterialCostItem(BaseModel):
    material_name: str
    unit_cost: float
    gross_quantity: float
    net_quantity: Optional[float] = None
    is_estimated: bool = False
    quotation_reference: Optional[str] = None
    supplier_name: Optional[str] = None

class ManufacturingCostRequest(BaseModel):
    product_id: Optional[str] = None
    bom_id: Optional[str] = None
    production_quantity: float = 500.0
    material_costs_breakdown: List[MaterialCostItem] = []
    workers_count: int = 1
    direct_labor_hours: float = 120.0
    labor_rate_per_hour: float = 180.0
    machine_hours: float = 45.0
    machine_rate_per_hour: float = 350.0
    machine_setup_hours: float = 0.0
    machine_setup_rate_per_hour: Optional[float] = None
    machine_power_kw: float = 0.0
    electricity_kwh: Optional[float] = 650.0
    electricity_tariff_per_kwh: float = 8.50
    secondary_processes_total: float = 18000.0
    transportation_total: float = 6500.0
    packaging_total: float = 4500.0
    overhead_method: str = "PERCENTAGE_PRIME_COST" # PERCENTAGE_PRIME_COST, PERCENTAGE_DIRECT_LABOR, MACHINE_HOURS, FIXED_PER_BATCH, FIXED_PER_UNIT
    overhead_pct: float = 12.0 # Alias for backward compatibility
    overhead_rate: float = 12.0
    other_expenses_total: float = 0.0
    recoverable_scrap_value_total: float = 0.0
    target_gross_margin_pct: float = 25.0
    custom_selling_price_per_unit: Optional[float] = None
    save_estimate: bool = False

class CostingSimulationRequest(BaseModel):
    baseline_estimate_id: Optional[str] = None
    baseline_inputs: Optional[ManufacturingCostRequest] = None
    simulation_overrides: Dict[str, Any]

# --- Optimization ---
class CandidateSupplierInput(BaseModel):
    supplier_id: str
    supplier_name: str
    unit_landed_cost: float
    fixed_freight: float = 0.0
    capacity: float = 10000.0
    moq: float = 1.0
    lead_time_days: int = 7
    quality_rating: float = 4.0

class OptimizationRequest(BaseModel):
    required_quantity: float = 800.0
    budget_limit: Optional[float] = None
    max_lead_time_days: Optional[int] = None
    enforce_single_supplier: bool = False
    candidates: Optional[List[CandidateSupplierInput]] = None

# --- Phase 6: Multi-Material Procurement Planning & Optimization ---
class ProcurementRequirementItem(BaseModel):
    material_id: str
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    required_quantity: float
    unit: str = "kg"
    max_lead_time_days: Optional[int] = None
    max_overbuy_pct: Optional[float] = 10.0

class ProcurementPlanCreateRequest(BaseModel):
    requirements: List[ProcurementRequirementItem]
    production_job_id: Optional[str] = None
    strategy: str = "LOWEST_LANDED_COST" # LOWEST_LANDED_COST, BALANCED, FASTEST_DELIVERY, QUALITY_FIRST, BUDGET_CONSTRAINED
    budget_limit: Optional[float] = None
    max_suppliers_per_material: int = 3
    allow_split_purchasing: bool = True
    global_max_lead_time_days: Optional[int] = None
    min_quality_rating: Optional[float] = 3.5
    max_overbuy_pct: float = 10.0

class ProcurementPlanFromJobRequest(BaseModel):
    job_id: str
    strategy: str = "LOWEST_LANDED_COST"
    budget_limit: Optional[float] = None
    max_suppliers_per_material: int = 3
    allow_split_purchasing: bool = True
    global_max_lead_time_days: Optional[int] = None
    min_quality_rating: Optional[float] = 3.5
    max_overbuy_pct: float = 10.0

class ProcurementPlanApprovalRequest(BaseModel):
    action: str = "APPROVE" # APPROVE, REJECT
    user_id: Optional[str] = "Chief Financial Officer"
    reason: Optional[str] = None

# --- Negotiation ---
class NegotiationStartRequest(BaseModel):
    supplier_id: str
    quotation_id: Optional[str] = None
    material_id: Optional[str] = None
    material_name: str
    material_specs: Optional[str] = None
    quantity: float = 800.0
    unit: str = "kg"
    original_unit_price: float
    target_unit_price: float
    max_acceptable_price: Optional[float] = None
    strategy: str = "BALANCED_COMMERCIAL"
    language: str = "en"
    delivery_deadline_days: Optional[int] = None
    payment_terms: str = "15 Days Prompt Payment"

class NegotiationProposalRequest(BaseModel):
    strategy: Optional[str] = None
    language: Optional[str] = "en"
    target_unit_price: Optional[float] = None
    payment_terms: Optional[str] = None
    custom_message_text: Optional[str] = None

class NegotiationCounterRequest(BaseModel):
    session_id: str
    counter_price: float
    notes: Optional[str] = None

class NegotiationTransitionRequest(BaseModel):
    session_id: str
    new_status: str
    reason: Optional[str] = None

class NegotiationSimulateRequest(BaseModel):
    scenario: str = "CONCESSION_PARTIAL" # CONCESSION_PARTIAL, ACCEPT_TARGET, REJECT_TARGET

class NegotiationAnalyzeResponseRequest(BaseModel):
    response_text: str
    parsed_price: Optional[float] = None
    parsed_freight: Optional[float] = None
    parsed_delivery_days: Optional[int] = None

class NegotiationApprovalRequest(BaseModel):
    approver_name: str = "Procurement Lead"
    action: str = "APPROVE" # APPROVE, REJECT
    notes: Optional[str] = None

# --- Customer & Customer Quotation ---
class CustomerCreateRequest(BaseModel):
    customer_code: Optional[str] = None
    name: str
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    gst_number: Optional[str] = None
    credit_limit: float = 500000.0
    payment_terms: str = "30 Days Net"

class CustomerQuoteGenerateRequest(BaseModel):
    customer_id: Optional[str] = None
    customer_name: Optional[str] = "Industrial Client"
    customer_company: Optional[str] = "Manufacturing Partner"
    customer_email: Optional[str] = None
    product_id: Optional[str] = None
    cost_estimate_id: Optional[str] = None
    quantity: float = 500.0
    unit_cost: Optional[float] = None
    unit_selling_price: Optional[float] = None
    target_margin_pct: Optional[float] = None
    discount_pct: float = 0.0
    tax_pct: float = 18.0
    min_margin_pct: float = 15.0
    payment_terms: str = "50% Advance, 50% on Dispatch"
    delivery_weeks: int = 3
    validity_days: int = 15
    terms_conditions: Optional[str] = None

class CustomerQuoteResponseRecordRequest(BaseModel):
    response: str # ACCEPTED, REJECTED, COUNTER_REQUESTED
    notes: Optional[str] = None

class CustomerQuoteRecalculateRequest(BaseModel):
    unit_cost: Optional[float] = None
    quantity: Optional[float] = None
    target_margin_pct: Optional[float] = None
    unit_selling_price: Optional[float] = None
    discount_pct: Optional[float] = None
    tax_pct: Optional[float] = None
    min_margin_pct: Optional[float] = None
    payment_terms: Optional[str] = None
    delivery_weeks: Optional[int] = None

class CustomerQuoteApprovalActionRequest(BaseModel):
    approver_name: Optional[str] = "Commercial Director"
    notes: Optional[str] = None

# --- Copilot & Approvals ---
class CopilotChatRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None

class CopilotConversationCreate(BaseModel):
    title: Optional[str] = None

class CopilotConversationUpdate(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None

class CopilotMessagePostRequest(BaseModel):
    content: str

class CopilotActionDecisionRequest(BaseModel):
    approver_name: Optional[str] = "Commercial Director"
    reason: Optional[str] = None

class ApprovalActionRequest(BaseModel):
    action: str = "APPROVE" # APPROVE, REJECT
    reason: Optional[str] = None

