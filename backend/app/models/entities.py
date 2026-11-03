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
    warehouse_location = Column(String(100), default="Rack A-1")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    material = relationship("Material", back_populates="inventory_item")


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False)
    movement_type = Column(String(50), nullable=False) # INWARD, RESERVATION, CONSUMPTION, ADJUSTMENT
    quantity = Column(Float, nullable=False)
    reference_id = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# --- Products & Bill of Materials (BOM) ---
class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    code = Column(String(100), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="Fabrication")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    boms = relationship("BillOfMaterials", back_populates="product", cascade="all, delete-orphan")


class BillOfMaterials(Base):
    __tablename__ = "bills_of_materials"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    version = Column(String(50), default="v1.0")
    is_active = Column(Boolean, default=True)
    batch_quantity = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="boms")
    items = relationship("BOMItem", back_populates="bom", cascade="all, delete-orphan")


class BOMItem(Base):
    __tablename__ = "bom_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    bom_id = Column(String, ForeignKey("bills_of_materials.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False)
    quantity_per_unit = Column(Float, nullable=False)
    unit = Column(String(50), default="kg")
    wastage_pct = Column(Float, default=5.0) # scrap/cutting loss allowance percentage
    process_stage = Column(String(100), default="Cutting & Forming")
    notes = Column(Text, nullable=True)

    bom = relationship("BillOfMaterials", back_populates="items")
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
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    bom_id = Column(String, ForeignKey("bills_of_materials.id"), nullable=False)
    batch_size = Column(Float, default=500.0)
    
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
    target_margin_pct = Column(Float, default=25.0)
    suggested_selling_price = Column(Float, default=0.0)
    total_revenue = Column(Float, default=0.0)
    projected_profit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class CustomerQuotation(Base):
    __tablename__ = "customer_quotations"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organisations.id"), nullable=False, index=True)
    quote_number = Column(String(100), unique=True, index=True, nullable=False)
    customer_name = Column(String(255), nullable=False)
    customer_company = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_production_cost = Column(Float, nullable=False)
    unit_selling_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    tax_pct = Column(Float, default=18.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    margin_pct = Column(Float, nullable=False)
    payment_terms = Column(String(100), default="50% Advance, 50% on Dispatch")
    validity_days = Column(Integer, default=15)
    delivery_weeks = Column(Integer, default=3)
    terms_conditions = Column(Text, nullable=True)
    status = Column(String(50), default="DRAFT") # DRAFT, PENDING_APPROVAL, APPROVED, SENT, REJECTED
    is_loss_making = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


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
    status = Column(String(50), default="PENDING") # PENDING, OPTIMIZED, ORDERED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)

    material = relationship("Material")


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
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False)
    quotation_id = Column(String, ForeignKey("supplier_quotations.id"), nullable=True)
    material_name = Column(String(255), nullable=False)
    quantity = Column(Float, default=1.0)
    original_unit_price = Column(Float, nullable=False)
    target_unit_price = Column(Float, nullable=False)
    current_offered_price = Column(Float, nullable=False)
    status = Column(String(50), default="DRAFT") # DRAFT, READY_FOR_APPROVAL, APPROVED_TO_SEND, SENT, RESPONSE_RECEIVED, COUNTEROFFER_PROPOSED, ACCEPTANCE_PROPOSED, REJECTED, CLOSED
    simulation_mode = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier")
    messages = relationship("NegotiationMessage", back_populates="session", cascade="all, delete-orphan")


class NegotiationMessage(Base):
    __tablename__ = "negotiation_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("negotiation_sessions.id"), nullable=False, index=True)
    round_number = Column(Integer, default=1)
    sender_type = Column(String(50), nullable=False) # BUYER_AGENT, SUPPLIER, HUMAN_OPERATOR
    message_text = Column(Text, nullable=False)
    proposed_unit_price = Column(Float, nullable=True)
    payment_terms = Column(String(100), nullable=True)
    delivery_days = Column(Integer, nullable=True)
    is_simulated = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

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

