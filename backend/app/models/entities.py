import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON, Enum
)
from sqlalchemy.orm import relationship
from app.database.session import Base

def generate_uuid():
    return str(uuid.uuid4())

# --- Identity & Organization ---
class Organization(Base):
    __tablename__ = "organisations"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    manufacturing_category = Column(String(100), default="Metal Fabrication")
    currency = Column(String(10), default="INR")
    currency_symbol = Column(String(5), default="₹")
    tax_id = Column(String(50), nullable=True) # GSTIN
    default_overhead_pct = Column(Float, default=12.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    factories = relationship("Factory", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")


class Factory(Base):
    __tablename__ = "factories"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False) # e.g., "Peenya Industrial Area, Bengaluru"
    capacity_monthly_hours = Column(Float, default=1200.0)
    electricity_tariff_kwh = Column(Float, default=8.50) # INR / kWh
    default_labor_rate_hr = Column(Float, default=180.0) # INR / hour
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="factories")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="OWNER") # OWNER, PROCUREMENT_MANAGER, ESTIMATOR, VIEWER
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")


# --- Suppliers & Vendor Performance ---
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    contact_person = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    postal_code = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    gst_number = Column(String(50), nullable=True)
    
    # Business attributes
    category = Column(String(100), default="Primary Raw Materials") # Primary Raw Materials, Fasteners, Consumables, Hardware
    manufacturing_specialisation = Column(Text, nullable=True)
    credit_period_days = Column(Integer, default=30)
    moq_general = Column(Float, default=100.0)
    capacity_monthly_tons = Column(Float, default=50.0)
    lead_time_days = Column(Integer, default=7)

    # Performance & Rating metrics
    quality_rating = Column(Float, default=4.2) # out of 5.0
    reliability_score = Column(Float, default=85.0) # 0-100
    on_time_delivery_pct = Column(Float, default=90.0)
    payment_terms_days = Column(Integer, default=30)
    total_historical_spend = Column(Float, default=0.0)
    total_orders_count = Column(Integer, default=0)
    rejection_rate_pct = Column(Float, default=0.5)
    
    is_active = Column(Boolean, default=True)
    is_simulated = Column(Boolean, default=True) # Tag demo/simulated vs real verified vendors
    created_at = Column(DateTime, default=datetime.utcnow)

    materials_supplied = relationship("SupplierMaterial", back_populates="supplier", cascade="all, delete-orphan")
    quotations = relationship("SupplierQuotation", back_populates="supplier")


class SupplierMaterial(Base):
    __tablename__ = "supplier_materials"

    id = Column(String, primary_key=True, default=generate_uuid)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False, index=True)
    material_name = Column(String(255), nullable=False)
    material_grade = Column(String(100), nullable=True)
    standard_unit_price = Column(Float, nullable=False)
    unit = Column(String(50), default="kg")
    moq = Column(Float, default=100.0) # Minimum Order Quantity
    typical_lead_time_days = Column(Integer, default=7)
    capacity_monthly_units = Column(Float, default=10000.0)

    supplier = relationship("Supplier", back_populates="materials_supplied")


# --- Materials & Inventory ---
class Material(Base):
    __tablename__ = "materials"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    code = Column(String(100), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="Raw Material") # Sheet Metal, Fasteners, Consumables, Coating
    grade = Column(String(100), nullable=True) # e.g. SS304, SS316, MS IS2062, AL6061
    specifications = Column(String(255), nullable=True) # e.g. ASTM A240 / ASME SA240, DIN 17440
    manufacturing_forms = Column(String(255), default="Sheet, Plate") # Sheet, Plate, Coil, Bar, Wire, Fasteners
    unit = Column(String(50), default="kg")
    density_g_cm3 = Column(Float, nullable=True)
    standard_cost = Column(Float, default=0.0)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    inventory_item = relationship("Inventory", back_populates="material", uselist=False, cascade="all, delete-orphan")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False, unique=True, index=True)
    current_stock = Column(Float, default=0.0)
    reserved_stock = Column(Float, default=0.0)
    incoming_stock = Column(Float, default=0.0)
    safety_stock = Column(Float, default=50.0)
    reorder_level = Column(Float, default=100.0)
    reorder_quantity = Column(Float, default=200.0)
    unit_cost_valuation = Column(Float, default=0.0)
    warehouse_location = Column(String(100), default="Rack A-1")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    material = relationship("Material", back_populates="inventory_item")

# Alias for concise reference
InventoryLedger = Inventory


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False, index=True)
    movement_type = Column(String(50), nullable=False) # INWARD, ISSUE, RESERVATION, RELEASE, ADJUSTMENT, SCRAP
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), default="kg")
    source = Column(String(100), nullable=True) # e.g. "Vendor Receipt", "Shopfloor Return"
    destination = Column(String(100), nullable=True) # e.g. "Machine 01", "Scrap Bin"
    reference_id = Column(String(100), nullable=True) # PO number, Job number, etc.
    user_id = Column(String(100), nullable=True)
    unit_cost = Column(Float, nullable=True)
    production_job_id = Column(String, nullable=True)
    idempotency_key = Column(String(100), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StockReservation(Base):
    __tablename__ = "stock_reservations"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False, index=True)
    production_job_id = Column(String, nullable=True, index=True)
    reserved_quantity = Column(Float, nullable=False)
    unit = Column(String(50), default="kg")
    status = Column(String(50), default="ACTIVE") # ACTIVE, FULFILLED, RELEASED, CANCELLED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    released_at = Column(DateTime, nullable=True)

    material = relationship("Material")


# --- Products & Bill of Materials (BOM) ---
class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    code = Column(String(100), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="Fabrication")
    description = Column(Text, nullable=True)
    manufacturing_process = Column(String(100), default="CNC Machining & Sheet Fabrication")
    base_unit = Column(String(50), default="units")
    default_batch_size = Column(Float, default=500.0)
    estimated_duration_hours = Column(Float, default=24.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    boms = relationship("BillOfMaterials", back_populates="product", cascade="all, delete-orphan")


class BillOfMaterials(Base):
    __tablename__ = "bills_of_materials"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    name = Column(String(255), default="Primary Production BOM")
    version = Column(String(50), default="v1.0")
    effective_date = Column(DateTime, default=datetime.utcnow)
    revision_status = Column(String(50), default="ACTIVE") # DRAFT, ACTIVE, ARCHIVED, SUPERSEDED
    is_active = Column(Boolean, default=True)
    batch_quantity = Column(Float, default=1.0)
    scrap_allowance_method = Column(String(50), default="ADDITIVE_SCRAP") # ADDITIVE_SCRAP, YIELD_BASED
    expected_yield_pct = Column(Float, default=95.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="boms")
    items = relationship("BOMItem", back_populates="bom", cascade="all, delete-orphan")

# Alias for concise reference
BOM = BillOfMaterials


class BOMItem(Base):
    __tablename__ = "bom_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    bom_id = Column(String, ForeignKey("bills_of_materials.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False)
    quantity_per_unit = Column(Float, nullable=False)
    unit = Column(String(50), default="kg")
    wastage_pct = Column(Float, default=5.0) # scrap allowance percentage
    scrap_allowance_method = Column(String(50), default="ADDITIVE_SCRAP") # ADDITIVE_SCRAP, YIELD_BASED
    expected_yield_pct = Column(Float, default=95.0)
    process_stage = Column(String(100), default="Cutting & Forming")
    notes = Column(Text, nullable=True)

    bom = relationship("BillOfMaterials", back_populates="items")
    material = relationship("Material")


# --- Production Jobs & MRP ---
class ProductionJob(Base):
    __tablename__ = "production_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    job_number = Column(String(100), unique=True, index=True, nullable=False)
    customer_order_ref = Column(String(100), nullable=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    bom_id = Column(String, ForeignKey("bills_of_materials.id"), nullable=False, index=True)
    production_quantity = Column(Float, nullable=False)
    unit = Column(String(50), default="units")
    planned_start_date = Column(DateTime, nullable=True)
    target_completion_date = Column(DateTime, nullable=True)
    priority = Column(String(50), default="MEDIUM") # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(50), default="PLANNED") # DRAFT, PLANNED, MATERIAL_CHECKED, AWAITING_PROCUREMENT, READY_FOR_PRODUCTION, IN_PROGRESS, COMPLETED, CANCELLED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product")
    bom = relationship("BillOfMaterials")
    requirements = relationship("ProductionJobMaterialRequirement", back_populates="job", cascade="all, delete-orphan")


class ProductionJobMaterialRequirement(Base):
    __tablename__ = "production_job_materials"

    id = Column(String, primary_key=True, default=generate_uuid)
    production_job_id = Column(String, ForeignKey("production_jobs.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False, index=True)
    net_quantity_required = Column(Float, nullable=False)
    gross_quantity_required = Column(Float, nullable=False)
    unit = Column(String(50), default="kg")
    scrap_quantity = Column(Float, default=0.0)
    available_stock = Column(Float, default=0.0)
    shortage_quantity = Column(Float, default=0.0)
    is_covered = Column(Boolean, default=False)
    requisition_id = Column(String, ForeignKey("purchase_requisitions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("ProductionJob", back_populates="requirements")
    material = relationship("Material")


# --- Quotations & Document Intelligence ---
class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False) # PDF, IMAGE, EXCEL, CSV
    file_size = Column(Integer, default=0)
    processing_status = Column(String(50), default="UPLOADED") # UPLOADED, QUEUED, PROCESSING, EXTRACTED, NEEDS_REVIEW, VERIFIED, FAILED
    validation_status = Column(String(50), default="PENDING") # READY_FOR_REVIEW, NEEDS_CORRECTION, QUARANTINED
    status = Column(String(50), default="PENDING_REVIEW") # Legacy status alias for UI backward compatibility
    confidence_score = Column(Float, default=0.0) # OCR confidence 0.0-1.0
    error_message = Column(Text, nullable=True)
    extraction_result_json = Column(JSON, nullable=True) # Full raw machine extraction snapshot
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier")


class SupplierQuotation(Base):
    __tablename__ = "supplier_quotations"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("uploaded_documents.id"), nullable=True)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False, index=True)
    quotation_number = Column(String(100), nullable=False)
    quotation_date = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    tax_pct = Column(Float, default=18.0) # GST 18% standard
    freight_cost = Column(Float, default=0.0)
    other_charges = Column(Float, default=0.0)
    is_tax_inclusive = Column(Boolean, default=False)
    total_amount = Column(Float, default=0.0) # Total Landed Base
    currency = Column(String(10), default="INR")
    status = Column(String(50), default="DRAFT") # DRAFT, VERIFIED, QUARANTINED, ARCHIVED
    review_notes = Column(Text, nullable=True)
    
    # Audit trail: machine raw vs human corrected snapshots
    original_extracted_json = Column(JSON, nullable=True)
    user_corrected_json = Column(JSON, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="quotations")
    document = relationship("UploadedDocument")
    items = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")

    @property
    def unit_price(self):
        return self.items[0].unit_price if self.items else 0.0

    @unit_price.setter
    def unit_price(self, val):
        if self.items:
            self.items[0].unit_price = val

    @property
    def lead_time_days(self):
        return self.items[0].lead_time_days if self.items else 7

    @lead_time_days.setter
    def lead_time_days(self, val):
        if self.items:
            self.items[0].lead_time_days = val

    @property
    def payment_terms(self):
        if hasattr(self, "_payment_terms") and self._payment_terms:
            return self._payment_terms
        sup_terms = self.supplier.payment_terms_days if self.supplier else None
        return f"Net {sup_terms}" if sup_terms else "30 Days Net"

    @payment_terms.setter
    def payment_terms(self, val):
        self._payment_terms = val

    @property
    def version(self):
        return getattr(self, "_version", 1)

    @version.setter
    def version(self, val):
        self._version = val


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    quotation_id = Column(String, ForeignKey("supplier_quotations.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=True)
    material_name_raw = Column(String(255), nullable=False)
    grade = Column(String(100), nullable=True)
    thickness_mm = Column(Float, nullable=True)
    dimensions = Column(String(100), nullable=True)
    quantity = Column(Float, default=1.0)
    unit = Column(String(50), default="kg")
    unit_price = Column(Float, nullable=False)
    moq = Column(Float, default=1.0)
    lead_time_days = Column(Integer, default=7)
    line_total = Column(Float, default=0.0)
    tax_pct = Column(Float, default=18.0)
    match_confidence = Column(Float, default=0.0)
    is_quarantined = Column(Boolean, default=False)
    quarantine_reason = Column(String(255), nullable=True)

    quotation = relationship("SupplierQuotation", back_populates="items")
    material = relationship("Material", foreign_keys=[material_id])


# --- Production Costing & Customer Quotation ---
class ProductionCostEstimate(Base):
    __tablename__ = "production_cost_estimates"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    estimate_number = Column(String(100), unique=True, index=True, nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    bom_id = Column(String, ForeignKey("bills_of_materials.id"), nullable=False)
    batch_size = Column(Float, default=500.0)
    calculation_version = Column(String(50), default="v1.0")
    data_quality_status = Column(String(50), default="COMPLETE") # COMPLETE, ESTIMATED, NEEDS_INPUT, INVALID
    currency = Column(String(10), default="INR")
    
    # 14 Cost Breakdown Attributes
    raw_material_cost = Column(Float, default=0.0)
    wastage_cost = Column(Float, default=0.0)
    direct_labor_cost = Column(Float, default=0.0)
    machine_cost = Column(Float, default=0.0)
    electricity_cost = Column(Float, default=0.0)
    secondary_processes_cost = Column(Float, default=0.0)
    transport_cost = Column(Float, default=0.0)
    packaging_cost = Column(Float, default=0.0)
    overhead_cost = Column(Float, default=0.0)
    other_expenses = Column(Float, default=0.0)
    
    total_production_cost = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)
    break_even_price = Column(Float, default=0.0)
    target_margin_pct = Column(Float, default=25.0)
    suggested_selling_price = Column(Float, default=0.0)
    effective_selling_price = Column(Float, default=0.0)
    effective_margin_pct = Column(Float, default=25.0)
    markup_pct = Column(Float, default=33.33)
    total_revenue = Column(Float, default=0.0)
    projected_profit = Column(Float, default=0.0)
    overhead_allocation_method = Column(String(50), default="PERCENTAGE_PRIME_COST")
    is_loss_making = Column(Boolean, default=False)
    
    # Traceability & Audit Snapshots
    assumptions_snapshot_json = Column(JSON, nullable=True)
    items_breakdown_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product")
    bom = relationship("BillOfMaterials")
    scenarios = relationship("CostingScenario", back_populates="estimate", cascade="all, delete-orphan")

# Alias for concise reference
CostEstimate = ProductionCostEstimate


class CostingScenario(Base):
    __tablename__ = "costing_scenarios"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    cost_estimate_id = Column(String, ForeignKey("production_cost_estimates.id"), nullable=False, index=True)
    scenario_name = Column(String(255), nullable=False)
    scenario_description = Column(Text, nullable=True)
    input_parameters_json = Column(JSON, nullable=False)
    simulated_results_json = Column(JSON, nullable=False)
    delta_total_cost = Column(Float, default=0.0)
    delta_unit_cost = Column(Float, default=0.0)
    delta_margin_pct = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    estimate = relationship("ProductionCostEstimate", back_populates="scenarios")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    customer_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    billing_address = Column(Text, nullable=True)
    shipping_address = Column(Text, nullable=True)
    gst_number = Column(String(50), nullable=True)
    credit_limit = Column(Float, default=500000.0)
    payment_terms = Column(String(100), default="30 Days Net")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CustomerQuotation(Base):
    __tablename__ = "customer_quotations"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    quote_number = Column(String(100), unique=True, index=True, nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(255), nullable=False)
    customer_company = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)
    cost_estimate_id = Column(String, ForeignKey("production_cost_estimates.id"), nullable=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_production_cost = Column(Float, nullable=False)
    unit_selling_price = Column(Float, nullable=False)
    markup_pct = Column(Float, default=0.0)
    margin_pct = Column(Float, nullable=False)
    min_margin_pct = Column(Float, default=15.0)
    gross_profit = Column(Float, default=0.0)
    subtotal = Column(Float, nullable=False)
    discount_pct = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    tax_pct = Column(Float, default=18.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    payment_terms = Column(String(100), default="50% Advance, 50% on Dispatch")
    validity_days = Column(Integer, default=15)
    delivery_weeks = Column(Integer, default=3)
    terms_conditions = Column(Text, nullable=True)
    status = Column(String(50), default="DRAFT") # DRAFT, NEEDS_REVIEW, READY_FOR_APPROVAL, APPROVED, SENT, ACCEPTED, REJECTED, EXPIRED, CANCELLED
    profitability_status = Column(String(50), default="PROFITABLE") # PROFITABLE, LOW_MARGIN, BREAK_EVEN, LOSS_MAKING, NEEDS_REVIEW
    is_loss_making = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    pdf_path = Column(String(500), nullable=True)
    approval_status = Column(String(50), default="DRAFT") # DRAFT, PENDING_APPROVAL, APPROVED, REJECTED
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    customer_response = Column(String(50), nullable=True) # ACCEPTED, REJECTED, COUNTER_REQUESTED
    customer_notes = Column(Text, nullable=True)
    items_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer")
    product = relationship("Product")
    cost_estimate = relationship("ProductionCostEstimate")


# --- Procurement & Optimization ---
class PurchaseRequisition(Base):
    __tablename__ = "purchase_requisitions"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    requisition_number = Column(String(100), unique=True, index=True, nullable=False)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False)
    required_quantity = Column(Float, nullable=False)
    unit = Column(String(50), default="kg")
    required_by_date = Column(DateTime, nullable=True)
    reason = Column(String(255), default="Production Order Shortage")
    budget_limit = Column(Float, nullable=True)
    selected_supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=True)
    selected_quotation_id = Column(String, ForeignKey("supplier_quotations.id"), nullable=True)
    estimated_total_cost = Column(Float, nullable=True)
    delivery_deadline = Column(DateTime, nullable=True)
    comparison_result_id = Column(String, nullable=True)
    status = Column(String(50), default="PENDING") # PENDING, APPROVED, REJECTED, ORDERED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)

    material = relationship("Material")
    selected_supplier = relationship("Supplier", foreign_keys=[selected_supplier_id])
    selected_quotation = relationship("SupplierQuotation", foreign_keys=[selected_quotation_id])


class SupplierComparisonRequest(Base):
    __tablename__ = "supplier_comparison_requests"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=True, index=True)
    material_name = Column(String(255), nullable=False)
    target_quantity = Column(Float, nullable=False)
    unit = Column(String(50), default="kg")
    delivery_deadline = Column(DateTime, nullable=True)
    budget_limit = Column(Float, nullable=True)
    weights_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    material = relationship("Material")
    result = relationship("SupplierComparisonResult", back_populates="request", uselist=False, cascade="all, delete-orphan")


class SupplierComparisonResult(Base):
    __tablename__ = "supplier_comparison_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    request_id = Column(String, ForeignKey("supplier_comparison_requests.id"), nullable=False, index=True)
    recommended_supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=True)
    recommended_quotation_id = Column(String, ForeignKey("supplier_quotations.id"), nullable=True)
    lowest_cost_supplier_id = Column(String, nullable=True)
    fastest_supplier_id = Column(String, nullable=True)
    highest_quality_supplier_id = Column(String, nullable=True)
    summary_headline = Column(String(500), nullable=True)
    concise_recommendation = Column(Text, nullable=True)
    detailed_explanation = Column(Text, nullable=True)
    evaluated_count = Column(Integer, default=0)
    eligible_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    request = relationship("SupplierComparisonRequest", back_populates="result")
    recommended_supplier = relationship("Supplier", foreign_keys=[recommended_supplier_id])
    recommended_quotation = relationship("SupplierQuotation", foreign_keys=[recommended_quotation_id])
    candidates = relationship("SupplierComparisonCandidate", back_populates="comparison_result", cascade="all, delete-orphan")


class SupplierComparisonCandidate(Base):
    __tablename__ = "supplier_comparison_candidates"

    id = Column(String, primary_key=True, default=generate_uuid)
    comparison_result_id = Column(String, ForeignKey("supplier_comparison_results.id"), nullable=False, index=True)
    quotation_id = Column(String, ForeignKey("supplier_quotations.id"), nullable=False, index=True)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False, index=True)
    rank = Column(Integer, default=1)
    eligibility_status = Column(String(50), default="ELIGIBLE")
    ineligibility_reasons_json = Column(JSON, nullable=True)
    effective_unit_landed_cost = Column(Float, nullable=False)
    total_landed_cost = Column(Float, nullable=False)
    composite_score = Column(Float, nullable=False)
    decision_band = Column(String(50), default="VIABLE_ALTERNATIVE")
    data_completeness_pct = Column(Float, default=100.0)
    scorecard_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    comparison_result = relationship("SupplierComparisonResult", back_populates="candidates")
    quotation = relationship("SupplierQuotation")
    supplier = relationship("Supplier")


class ProcurementRecommendation(Base):
    __tablename__ = "procurement_recommendations"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    requisition_id = Column(String, ForeignKey("purchase_requisitions.id"), nullable=True)
    allocation_json = Column(JSON, nullable=False) # list of {supplier_id, supplier_name, quantity, unit_price, landed_cost}
    total_cost = Column(Float, nullable=False)
    budget_limit = Column(Float, nullable=True)
    budget_utilized_pct = Column(Float, nullable=True)
    solver_status = Column(String(50), default="OPTIMAL") # OPTIMAL, FEASIBLE, INFEASIBLE
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# --- Negotiation State Machine ---
class NegotiationSession(Base):
    __tablename__ = "negotiation_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    session_number = Column(String(100), unique=True, index=True, nullable=True)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False)
    quotation_id = Column(String, ForeignKey("supplier_quotations.id"), nullable=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=True)
    material_name = Column(String(255), nullable=False)
    material_specs = Column(Text, nullable=True)
    strategy = Column(String(50), default="BALANCED_COMMERCIAL") # PRICE_FOCUSED, VOLUME_BASED, COMPETITIVE_OFFER, DELIVERY_FOCUSED, BALANCED_COMMERCIAL
    quantity = Column(Float, default=1.0)
    original_unit_price = Column(Float, nullable=False)
    target_unit_price = Column(Float, nullable=False)
    max_acceptable_price = Column(Float, nullable=True)
    current_offered_price = Column(Float, nullable=False)
    original_landed_cost = Column(Float, default=0.0)
    current_landed_cost = Column(Float, default=0.0)
    final_agreed_price = Column(Float, nullable=True)
    final_landed_cost = Column(Float, nullable=True)
    net_savings_abs = Column(Float, default=0.0)
    net_savings_pct = Column(Float, default=0.0)
    delivery_deadline_days = Column(Integer, nullable=True)
    payment_terms = Column(String(100), nullable=True)
    competitor_quote_id = Column(String, ForeignKey("supplier_quotations.id"), nullable=True)
    revised_quotation_id = Column(String, ForeignKey("supplier_quotations.id"), nullable=True)
    status = Column(String(50), default="DRAFT") # DRAFT, ANALYSING, PROPOSAL_GENERATED, AWAITING_APPROVAL, APPROVED_TO_SEND, SENT, RESPONSE_RECEIVED, RESPONSE_ANALYSED, COUNTEROFFER_GENERATED, AWAITING_COUNTEROFFER_APPROVAL, COUNTEROFFER_SENT, ACCEPTANCE_PROPOSED, REJECTION_PROPOSED, COMPLETED, CANCELLED, FAILED
    approval_status = Column(String(50), default="DRAFT") # DRAFT, PENDING_APPROVAL, APPROVED, REJECTED
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    commercial_impact_json = Column(JSON, nullable=True)
    simulation_mode = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier", foreign_keys=[supplier_id])
    quotation = relationship("SupplierQuotation", foreign_keys=[quotation_id])
    competitor_quote = relationship("SupplierQuotation", foreign_keys=[competitor_quote_id])
    revised_quotation = relationship("SupplierQuotation", foreign_keys=[revised_quotation_id])
    material = relationship("Material", foreign_keys=[material_id])
    messages = relationship("NegotiationMessage", back_populates="session", cascade="all, delete-orphan")


class NegotiationMessage(Base):
    __tablename__ = "negotiation_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("negotiation_sessions.id"), nullable=False, index=True)
    round_number = Column(Integer, default=1)
    sender_type = Column(String(50), nullable=False) # BUYER_AGENT, SUPPLIER, HUMAN_OPERATOR
    language = Column(String(20), default="en") # en, hi, hinglish
    subject = Column(String(255), nullable=True)
    message_text = Column(Text, nullable=False)
    proposed_unit_price = Column(Float, nullable=True)
    payment_terms = Column(String(100), nullable=True)
    delivery_days = Column(Integer, nullable=True)
    extracted_terms_json = Column(JSON, nullable=True)
    classification = Column(String(50), nullable=True) # ACCEPTED_TARGET, ACCEPTABLE_COUNTEROFFER, COUNTEROFFER_REQUIRES_REVIEW, REJECTED_TARGET, INCOMPLETE_RESPONSE, NEEDS_HUMAN_REVIEW
    email_dispatch_status = Column(String(50), default="SIMULATED") # SIMULATED, SENT, PENDING_APPROVAL, FAILED
    email_recipient = Column(String(255), nullable=True)
    idempotency_key = Column(String(100), nullable=True)
    is_simulated = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("NegotiationSession", back_populates="messages")

    session = relationship("NegotiationSession", back_populates="messages")


# --- Human Approvals & Audit Trail ---
class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    request_type = Column(String(50), nullable=False) # NEGOTIATION_DISPATCH, PURCHASE_ORDER, CUSTOMER_QUOTE
    entity_id = Column(String(100), nullable=False)
    requested_by = Column(String(255), default="IndusPilot Agent")
    details_json = Column(JSON, nullable=False)
    status = Column(String(50), default="PENDING") # PENDING, APPROVED, REJECTED
    decision_reason = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    user_id = Column(String, nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=True)
    changes_json = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# --- Phase 6: Advanced Procurement Planning & Multi-Supplier Optimisation ---
class ProcurementPlan(Base):
    __tablename__ = "procurement_plans"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    plan_number = Column(String(100), unique=True, index=True, nullable=False)
    production_job_id = Column(String, ForeignKey("production_jobs.id"), nullable=True, index=True)
    strategy = Column(String(50), default="LOWEST_LANDED_COST") # LOWEST_LANDED_COST, BALANCED, FASTEST_DELIVERY, QUALITY_FIRST, BUDGET_CONSTRAINED
    status = Column(String(50), default="DRAFT") # DRAFT, OPTIMIZING, OPTIMIZED, NEEDS_REVIEW, AWAITING_APPROVAL, APPROVED, REJECTED, EXPIRED
    budget_limit = Column(Float, nullable=True)
    max_suppliers_per_material = Column(Integer, default=3)
    allow_split_purchasing = Column(Boolean, default=True)
    max_overbuy_pct = Column(Float, default=10.0)
    min_quality_rating = Column(Float, default=3.5)
    required_by_date = Column(DateTime, nullable=True)
    solver_status = Column(String(50), default="OPTIMAL")
    total_landed_cost = Column(Float, default=0.0)
    budget_utilized_pct = Column(Float, nullable=True)
    total_units_required = Column(Float, default=0.0)
    total_units_allocated = Column(Float, default=0.0)
    excess_units = Column(Float, default=0.0)
    baseline_comparison_json = Column(JSON, nullable=True)
    explanation_headline = Column(String(500), nullable=True)
    explanation_detail = Column(Text, nullable=True)
    input_snapshot_json = Column(JSON, nullable=True)
    approval_status = Column(String(50), default="PENDING") # PENDING, APPROVED, REJECTED
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    production_job = relationship("ProductionJob")
    items = relationship("ProcurementPlanItem", back_populates="plan", cascade="all, delete-orphan")
    allocations = relationship("ProcurementPlanAllocation", back_populates="plan", cascade="all, delete-orphan")


class ProcurementPlanItem(Base):
    __tablename__ = "procurement_plan_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    procurement_plan_id = Column(String, ForeignKey("procurement_plans.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False, index=True)
    required_quantity = Column(Float, nullable=False)
    unit = Column(String(50), default="kg")
    delivery_deadline = Column(DateTime, nullable=True)
    allocated_quantity = Column(Float, default=0.0)
    allocated_cost = Column(Float, default=0.0)
    shortage_quantity = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = relationship("ProcurementPlan", back_populates="items")
    material = relationship("Material")


class ProcurementPlanAllocation(Base):
    __tablename__ = "procurement_plan_allocations"

    id = Column(String, primary_key=True, default=generate_uuid)
    procurement_plan_id = Column(String, ForeignKey("procurement_plans.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False, index=True)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False, index=True)
    quotation_id = Column(String, ForeignKey("supplier_quotations.id"), nullable=True)
    allocated_quantity = Column(Float, nullable=False)
    unit = Column(String(50), default="kg")
    unit_landed_cost = Column(Float, nullable=False)
    subtotal_cost = Column(Float, nullable=False)
    fixed_freight_allocated = Column(Float, default=0.0)
    moq = Column(Float, default=1.0)
    moq_satisfied = Column(Boolean, default=True)
    package_count = Column(Integer, nullable=True)
    lead_time_days = Column(Integer, default=7)
    delivery_date = Column(DateTime, nullable=True)
    supplier_risk_score = Column(Float, default=0.0)
    quality_rating = Column(Float, default=4.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = relationship("ProcurementPlan", back_populates="allocations")
    material = relationship("Material")
    supplier = relationship("Supplier")
    quotation = relationship("SupplierQuotation")


# --- Phase 8: Intelligent Manufacturing Copilot & Multi-Agent Orchestration ---

class CopilotConversation(Base):
    __tablename__ = "copilot_conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    title = Column(String(255), default="New Manufacturing Discussion")
    summary = Column(Text, nullable=True)
    context_state_json = Column(JSON, default={})
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    messages = relationship("CopilotMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="CopilotMessage.created_at.asc()")
    runs = relationship("AgentRun", back_populates="conversation", cascade="all, delete-orphan")


class CopilotMessage(Base):
    __tablename__ = "copilot_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("copilot_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False) # user, assistant, system, tool
    agent_name = Column(String(100), nullable=True) # Supervisor Agent, Inventory and BOM Agent, etc.
    content = Column(Text, nullable=False)
    structured_data_json = Column(JSON, nullable=True) # comparison table, BOM explosion, shortage card, quotation preview
    tool_calls_json = Column(JSON, nullable=True)
    run_id = Column(String(100), nullable=True, index=True)
    requires_human_approval = Column(Boolean, default=False)
    pending_action_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("CopilotConversation", back_populates="messages")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("copilot_conversations.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String, nullable=True)
    objective = Column(Text, nullable=False)
    selected_agents_json = Column(JSON, default=[])
    status = Column(String(50), default="STARTED") # STARTED, PLANNING, EXECUTING, AWAITING_APPROVAL, PAUSED, COMPLETED, FAILED, CANCELLED
    workflow_state_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    conversation = relationship("CopilotConversation", back_populates="runs")
    steps = relationship("AgentRunStep", back_populates="run", cascade="all, delete-orphan", order_by="AgentRunStep.step_number.asc()")
    tool_calls = relationship("AgentToolCall", back_populates="run", cascade="all, delete-orphan")
    pending_actions = relationship("PendingAgentAction", back_populates="run", cascade="all, delete-orphan")


class AgentRunStep(Base):
    __tablename__ = "agent_run_steps"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    agent_name = Column(String(100), nullable=False)
    step_type = Column(String(50), default="THOUGHT") # INTENT, PLANNING, TOOL_EXECUTION, SYNTHESIS, APPROVAL_CHECKPOINT
    description = Column(Text, nullable=False)
    input_json = Column(JSON, nullable=True)
    output_json = Column(JSON, nullable=True)
    status = Column(String(50), default="COMPLETED") # COMPLETED, FAILED, SKIPPED
    timestamp = Column(DateTime, default=datetime.utcnow)

    run = relationship("AgentRun", back_populates="steps")


class AgentToolCall(Base):
    __tablename__ = "agent_tool_calls"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    tool_name = Column(String(100), nullable=False)
    permission_tier = Column(String(50), default="READ_ONLY") # READ_ONLY, DRAFT_CREATION, SENSITIVE_MUTATION, EXTERNAL_ACTION
    input_arguments_json = Column(JSON, nullable=False)
    output_result_json = Column(JSON, nullable=True)
    status = Column(String(50), default="SUCCESS") # SUCCESS, FAILED, BLOCKED_UNAUTHORIZED
    execution_duration_ms = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("AgentRun", back_populates="tool_calls")


class PendingAgentAction(Base):
    __tablename__ = "pending_agent_actions"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    conversation_id = Column(String, nullable=True, index=True)
    action_type = Column(String(100), nullable=False) # TRANSMIT_NEGOTIATION, CREATE_PURCHASE_REQUISITIONS, APPROVE_CUSTOMER_QUOTE
    agent_name = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    proposed_payload_json = Column(JSON, nullable=False)
    financial_impact_summary = Column(String(255), nullable=True)
    status = Column(String(50), default="PENDING") # PENDING, APPROVED, REJECTED, EXPIRED
    decision_by = Column(String(100), nullable=True)
    decision_reason = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("AgentRun", back_populates="pending_actions")


class WorkflowCheckpoint(Base):
    __tablename__ = "workflow_checkpoints"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    checkpoint_id = Column(String(100), nullable=False)
    thread_id = Column(String(100), nullable=False, index=True)
    state_dump_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


