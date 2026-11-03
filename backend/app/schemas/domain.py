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

# --- BOM & Shortage ---
class BOMItemInput(BaseModel):
    material_id: str
    quantity_per_unit: float
    unit: str = "kg"
    wastage_pct: float = 5.0
    process_stage: str = "Cutting"
    notes: Optional[str] = None

class BOMCreate(BaseModel):
    product_name: str
    product_code: str
    category: str = "Fabrication"
    description: Optional[str] = None
    version: str = "v1.0"
    items: List[BOMItemInput]

class BOMExplodeRequest(BaseModel):
    product_id: Optional[str] = None
    production_quantity: float = 500.0
    custom_items: Optional[List[BOMItemInput]] = None

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
    quantity: float = 800.0
    weights: Optional[Dict[str, float]] = None

# --- Costing ---
class MaterialCostItem(BaseModel):
    material_name: str
    unit_cost: float
    gross_quantity: float
    net_quantity: Optional[float] = None

class ManufacturingCostRequest(BaseModel):
    production_quantity: float = 500.0
    material_costs_breakdown: List[MaterialCostItem]
    direct_labor_hours: float = 120.0
    labor_rate_per_hour: float = 180.0
    machine_hours: float = 45.0
    machine_rate_per_hour: float = 350.0
    electricity_kwh: float = 650.0
    electricity_tariff_per_kwh: float = 8.50
    secondary_processes_total: float = 18000.0
    transportation_total: float = 6500.0
    packaging_total: float = 4500.0
    overhead_pct: float = 12.0
    target_gross_margin_pct: float = 25.0
    custom_selling_price_per_unit: Optional[float] = None

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

# --- Negotiation ---
class NegotiationStartRequest(BaseModel):
    supplier_id: str
    quotation_id: Optional[str] = None
    material_name: str
    quantity: float = 800.0
    original_unit_price: float
    target_unit_price: float
    payment_terms: str = "15 Days Net"

class NegotiationCounterRequest(BaseModel):
    session_id: str
    counter_price: float
    notes: Optional[str] = None

class NegotiationTransitionRequest(BaseModel):
    session_id: str
    new_status: str
    reason: Optional[str] = None

# --- Customer Quotation ---
class CustomerQuoteGenerateRequest(BaseModel):
    customer_name: str
    customer_company: str
    customer_email: Optional[str] = None
    product_id: Optional[str] = None
    quantity: float = 500.0
    unit_cost: float = 637.0
    unit_selling_price: float = 850.0
    tax_pct: float = 18.0
    payment_terms: str = "50% Advance, 50% on Dispatch"
    delivery_weeks: int = 3
    terms_conditions: Optional[str] = None

# --- Copilot & Approvals ---
class CopilotChatRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None

class ApprovalActionRequest(BaseModel):
    action: str = "APPROVE" # APPROVE, REJECT
    reason: Optional[str] = None

