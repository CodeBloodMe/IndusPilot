# IndusPilot — API Documentation & Integration Specification

**System Name:** IndusPilot API Gateway  
**Base URL:** `http://localhost:8000/api/v1`  
**Specification Standard:** OpenAPI 3.1 / JSON REST  
**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI) & `/redoc` (ReDoc)  

---

## 1. Authentication & Multi-Tenant Scoping

All API endpoints enforce multi-tenant isolation. Requests should include the enterprise tenant header:
```http
X-Organization-ID: org_tech4bharat_induspilot_demo
```
If omitted, the API defaults to the demonstration tenant (`org_tech4bharat_induspilot_demo`).

---

## 2. Core Endpoints Specification

### 2.1 Dashboard & Intelligence Overview
#### `GET /api/v1/dashboard/metrics`
Computes live KPIs across procurement spend, active vendor base, inventory shortages, and negotiation cost savings.

**Response (200 OK):**
```json
{
  "procurement_spend_total": 903692.00,
  "active_suppliers_count": 10,
  "verified_quotations_count": 3,
  "pending_quotations_count": 0,
  "pending_approvals_count": 1,
  "material_shortages_count": 0,
  "total_savings_generated": 16000.00,
  "critical_shortages": [],
  "recent_quotations": [
    {
      "id": "qtn_8821",
      "quotation_number": "APX-2026-QTN-8821",
      "supplier_name": "Apex Steel & Alloys Pvt Ltd",
      "total_amount": 301860.00,
      "date": "12 Oct 2026"
    }
  ],
  "currency_symbol": "₹"
}
```

---

### 2.2 Supplier Directory
#### `GET /api/v1/suppliers`
Retrieves suppliers with filtering by material grade and quality ratings.

**Query Parameters:**
- `material_filter` (optional string): e.g. `ss304`
- `min_rating` (optional float): e.g. `4.0`

**Response (200 OK):**
```json
[
  {
    "id": "sup-apex-uuid",
    "organization_id": "org_tech4bharat_induspilot_demo",
    "name": "Apex Steel & Alloys Pvt Ltd",
    "contact_person": "Suresh Hegde",
    "city": "Bengaluru",
    "state": "Karnataka",
    "quality_rating": 4.6,
    "reliability_score": 92.0,
    "on_time_delivery_pct": 94.0,
    "payment_terms_days": 30,
    "is_simulated": true
  }
]
```

---

### 2.3 Quotation Ingestion & Quality Gate
#### `POST /api/v1/quotations/upload`
Uploads raw quotation files (PDF, XLSX, CSV, JPG, PNG). Executes PyMuPDF / regex extraction and checks the automated Quality Gate.

**Request:** `multipart/form-data` with `file=@apex_steel_quotation_ss304.pdf`

**Response (200 OK):**
```json
{
  "success": true,
  "filename": "apex_steel_quotation_ss304.pdf",
  "confidence_score": 0.96,
  "status": "VERIFIED",
  "supplier_name": "Apex Steel & Alloys Pvt Ltd",
  "quotation_number": "APX-2026-QTN-8821",
  "subtotal": 252000.00,
  "tax_pct": 18.0,
  "tax_amount": 45360.00,
  "is_tax_inclusive": false,
  "freight_cost": 4500.00,
  "total_amount": 301860.00,
  "items": [
    {
      "material_name": "Stainless Steel 304 Sheet Plate (2B Finish)",
      "grade": "AISI 304 / DIN 1.4301",
      "quantity": 800.0,
      "unit": "kg",
      "unit_price": 315.00,
      "moq": 200.0,
      "lead_time_days": 6,
      "line_total": 252000.00,
      "is_quarantined": false
    }
  ]
}
```

---

### 2.4 Smart Supplier Comparison Engine
#### `POST /api/v1/compare/evaluate`
Calculates landed cost and explainable 5-factor scoring (Cost 35%, Quality 25%, Reliability 15%, Lead Time 15%, Payment Terms 10%).

**Request Body:**
```json
{
  "quotation_ids": ["qtn_1", "qtn_2", "qtn_3"],
  "quantity": 800.0
}
```

**Response (200 OK):**
```json
{
  "compared_quotations_count": 3,
  "target_quantity": 800.0,
  "recommended_candidate": {
    "supplier_name": "Apex Steel & Alloys Pvt Ltd",
    "composite_score": 84.8,
    "decision_band": "STRONGLY_RECOMMENDED",
    "effective_unit_landed_cost": 377.33,
    "total_landed_cost": 301860.00,
    "rationale": "Top tier procurement choice offering superior landed economics, quality, and delivery stability."
  },
  "candidates": [...]
}
```

---

### 2.5 Bill of Materials & Inventory Netting
#### `POST /api/v1/bom/explode`
Calculates gross material requirements incorporating scrap/wastage percentages and nets against warehouse stock.

**Request Body:**
```json
{
  "product_id": "prod-bracket-500",
  "production_quantity": 500.0
}
```

**Response (200 OK):**
```json
{
  "product": { "name": "Stainless Steel Industrial Bracket (500mm)", "code": "SS304-BRK-500" },
  "production_quantity": 500.0,
  "components_count": 4,
  "shortages_count": 1,
  "total_shortage_mass_kg": 900.0,
  "components": [
    {
      "material_name": "Stainless Steel 304 Sheet Plate",
      "net_quantity_per_unit": 2.0,
      "wastage_pct": 5.0,
      "total_gross_required": 1050.0,
      "inventory_status": {
        "current_stock": 250.0,
        "available_stock": 200.0,
        "safety_stock": 50.0,
        "net_shortage": 900.0,
        "has_shortage": true
      }
    }
  ]
}
```

---

### 2.6 Manufacturing Cost Intelligence Engine
#### `POST /api/v1/costing/calculate`
Executes deterministic 14-factor manufacturing cost calculation with Python Decimal arithmetic.

**Request Body:**
```json
{
  "production_quantity": 500.0,
  "material_costs_breakdown": [
    { "material_name": "SS304 Plate", "unit_cost": 315.0, "gross_quantity": 1050.0, "net_quantity": 1000.0 }
  ],
  "direct_labor_hours": 120.0,
  "labor_rate_per_hour": 180.0,
  "machine_hours": 45.0,
  "machine_rate_per_hour": 350.0,
  "electricity_kwh": 650.0,
  "electricity_tariff_per_kwh": 8.50,
  "secondary_processes_total": 18000.0,
  "transportation_total": 6500.0,
  "packaging_total": 4500.0,
  "overhead_pct": 12.0,
  "target_gross_margin_pct": 25.0
}
```

**Response (200 OK):**
```json
{
  "production_quantity": 500.0,
  "cost_breakdown": {
    "total_raw_material_cost": 330750.00,
    "direct_labor_cost": 21600.00,
    "machine_operating_cost": 15750.00,
    "electricity_cost": 5525.00,
    "secondary_processes_cost": 18000.00,
    "transportation_cost": 6500.00,
    "packaging_cost": 4500.00,
    "allocated_overhead_cost": 48315.00,
    "total_production_cost": 450940.00
  },
  "unit_economics": {
    "unit_cost": 901.88,
    "break_even_price": 901.88,
    "suggested_unit_price": 1202.51,
    "total_revenue": 601255.00,
    "projected_gross_profit": 150315.00,
    "effective_margin_pct": 25.0,
    "is_loss_making": false
  }
}
```

---

### 2.7 Google OR-Tools Procurement Optimization
#### `POST /api/v1/optimizer/solve`
Solves multi-supplier allocation using Mixed-Integer Linear Programming.

**Request Body:**
```json
{
  "required_quantity": 800.0,
  "budget_limit": 300000.0
}
```

**Response (200 OK):**
```json
{
  "status": "OPTIMAL",
  "required_quantity": 800.0,
  "total_cost": 260500.00,
  "budget_utilized_pct": 86.8,
  "allocated_suppliers_count": 2,
  "allocations": [
    {
      "supplier_name": "Bharat Forgings & Metals",
      "allocated_quantity": 500.0,
      "unit_landed_cost": 305.50
    },
    {
      "supplier_name": "Apex Steel & Alloys Pvt Ltd",
      "allocated_quantity": 300.0,
      "unit_landed_cost": 320.60
    }
  ],
  "explanation": "Volume is split across 2 suppliers to satisfy capacity limits and minimize overall landed cost."
}
```

---

### 2.8 Autonomous Negotiation State Machine
#### `POST /api/v1/negotiation/start`
Initializes a negotiation session and drafts an evidence-backed counteroffer (`READY_FOR_APPROVAL`).

#### `POST /api/v1/negotiation/send-and-simulate?session_id={id}`
Simulates transmission of the approved counteroffer and computes the vendor's concession curve.

---

### 2.9 Customer Quotation Generator & PDF
#### `POST /api/v1/customer-quotes/generate`
Builds a customer commercial quotation, verifies margin thresholds, and renders a PDF quotation.

#### `GET /api/v1/customer-quotes/{id}/download-pdf`
Streams the generated commercial PDF document.

---

### 2.10 Multilingual AI Copilot
#### `POST /api/v1/copilot/chat`
Conversational assistant supporting English, Hindi, and Hinglish with real tool invocation.

**Sample Hinglish Request:**
```json
{
  "query": "Apex Steel ka quotation compare karo aur batao kitna kharcha aayega 500 units ke liye"
}
```

