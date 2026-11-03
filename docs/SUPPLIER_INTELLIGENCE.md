# IndusPilot — Supplier Intelligence Subsystem

## 1. Architectural Overview

The **Supplier Intelligence Subsystem** in IndusPilot manages vendor discovery, lifecycle tracking, commercial terms governance, and historical performance auditing for small-and-medium manufacturing enterprises (MSMEs).

In industrial subcontracting and precision sheet metal fabrication, selecting a supplier solely on nominal raw material rates frequently leads to delayed customer orders, production bottlenecks, and unexpected freight/tax overheads. The Supplier Intelligence Subsystem equips manufacturing estimators with:

1. **Enterprise Vendor Profiles**: Comprehensive tracking of corporate entity information, verified GSTIN tax identification, addresses, contact leadership, and manufacturing specialisations.
2. **Commercial Parameters Governance**: Credit periods (e.g. 15, 30, 45, 60 days), minimum order quantities (MOQ), monthly supply capacity (tons), and standard lead times.
3. **Multi-Factor Performance Tracking**: Continuous evaluation of on-time delivery percentages, certified quality inspection ratings (0.0 to 5.0), past rejection rates, total historical purchase spend, and quotation frequency.
4. **Active Deduplication**: Deterministic rejection of duplicate vendor registrations using case-insensitive corporate names and unique GSTIN validation (returning HTTP `409 Conflict`).
5. **Soft-Deactivation**: Non-destructive deactivation preserving historic quotation records and audit logs.

---

## 2. Data Model Design

The supplier entities are defined in SQLAlchemy with PostgreSQL/SQLite compatibility:

```python
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
    category = Column(String(100), default="Primary Raw Materials")
    manufacturing_specialisation = Column(Text, nullable=True)
    credit_period_days = Column(Integer, default=30)
    moq_general = Column(Float, default=100.0)
    capacity_monthly_tons = Column(Float, default=50.0)
    lead_time_days = Column(Integer, default=7)

    # Performance & Rating metrics
    quality_rating = Column(Float, default=4.2)
    reliability_score = Column(Float, default=85.0)
    on_time_delivery_pct = Column(Float, default=90.0)
    payment_terms_days = Column(Integer, default=30)
    total_historical_spend = Column(Float, default=0.0)
    total_orders_count = Column(Integer, default=0)
    rejection_rate_pct = Column(Float, default=0.5)
    
    is_active = Column(Boolean, default=True)
    is_simulated = Column(Boolean, default=False)
```

---

## 3. REST API Specifications

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/suppliers` | List suppliers with filters: `category`, `city`, `material_filter`, `min_rating`, `search`, `is_active` |
| `POST` | `/api/v1/suppliers` | Register new supplier with duplicate detection on name and GSTIN |
| `GET` | `/api/v1/suppliers/{id}` | Retrieve comprehensive supplier profile and performance metrics |
| `PATCH` | `/api/v1/suppliers/{id}` | Update supplier commercial, contact, and rating attributes |
| `DELETE` | `/api/v1/suppliers/{id}` | Soft-deactivate supplier (`is_active = False`) |
| `GET` | `/api/v1/suppliers/{id}/quotations` | Chronological quotation history and price trends for this vendor |

---

## 4. Multi-Criteria Supplier Comparison Scoring

Supplier comparison integrates five weighted dimensions:

$$\text{Score} = w_{\text{cost}} \cdot S_{\text{cost}} + w_{\text{qual}} \cdot S_{\text{qual}} + w_{\text{rel}} \cdot S_{\text{rel}} + w_{\text{lead}} \cdot S_{\text{lead}} + w_{\text{pay}} \cdot S_{\text{pay}}$$

- **Cost Competitiveness** ($w = 0.35$): Evaluated against true landed cost per unit relative to the best quoted price in the comparison pool:
  $$S_{\text{cost}} = \min\left(100, \frac{\text{Landed Cost}_{\min}}{\text{Landed Cost}_{\text{current}}} \times 100\right)$$
- **Quality Track Record** ($w = 0.25$): Derived from verified inspection rating:
  $$S_{\text{qual}} = \frac{\text{Rating}}{5.0} \times 100$$
- **Delivery Reliability** ($w = 0.15$): Historical on-time fulfillment track record (0–100%).
- **Lead Time Performance** ($w = 0.15$): Penalized linearly when exceeding the fastest vendor timeline.
- **Payment Flexibility** ($w = 0.10$): Credit period scoring (60+ days: 100 pts, 30 days: 75 pts, 15 days: 50 pts, advance: 35 pts).

Decision bands:
- $\ge 85.0$: **STRONGLY_RECOMMENDED**
- $70.0 - 84.9$: **VIABLE_ALTERNATIVE**
- $55.0 - 69.9$: **HIGHER_RISK**
- $< 55.0$: **NOT_RECOMMENDED**

