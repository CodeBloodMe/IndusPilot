# IndusPilot — Agentic AI for Intelligent Manufacturing

<p align="center">
  <img src="https://img.shields.io/badge/Tech4Bharat-2026-blue?style=for-the-badge" alt="Tech4Bharat 2026">
  <img src="https://img.shields.io/badge/Theme-Industrial%20Manufacturing-orange?style=for-the-badge" alt="Theme">
  <img src="https://img.shields.io/badge/Problem%20Statement-4.1%20Procurement%20%26%20Quotation-green?style=for-the-badge" alt="Problem Statement 4.1">
  <img src="https://img.shields.io/badge/Engine-Python%20Decimal%20%2B%20OR--Tools-teal?style=for-the-badge" alt="Deterministic Engine">
</p>

> **"Buy smarter. Calculate accurately. Manufacture profitably."**  
> IndusPilot is an Agentic AI-powered manufacturing procurement and profitability intelligence platform designed for small and medium-sized industrial manufacturing enterprises (MSMEs).

---

## 🏆 Tech4Bharat 2026 Hackathon Submission

- **Challenge:** The GAVS Hackathon — Tech4Bharat 2026
- **Track:** Industrial Manufacturing
- **Problem Statement 4.1:** Raw material procurement and manufacturing quotation optimisation
- **Official Problem Portal:** [thegavshackathon.com/challenges](https://thegavshackathon.com/challenges)

---

## 🏭 The Central Problem

Small and medium manufacturing businesses face a critical two-way profit squeeze:
1. **Upstream Procurement Chaos:** Sourcing raw materials (sheet steel, structural alloys, fasteners, consumables) across unstructured quotations received via WhatsApp, scanned PDFs, spreadsheets, and emails. Buyers inadvertently overpay due to uncalculated freight, hidden taxes, or misjudged Minimum Order Quantities (MOQ).
2. **Downstream Under-Costed Quotations:** Inaccurate estimation of manufacturing conversion costs (scrap/wastage, machine hourly depreciation, labor rates, kilowatt-hour electricity, and overheads) causes factories to win unprofitable, loss-making orders.

**IndusPilot connects these activities into one unified, agentic system.**

---

## 🌟 Key Innovations & Architecture

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                               INDUSPILOT WEB FRONTEND                             │
│                  Next.js App Router | TypeScript | Tailwind CSS                   │
└─────────────────────────────────────────┬─────────────────────────────────────────┘
                                          │ REST / JSON (FastAPI)
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI ENTERPRISE API GATEWAY                          │
│                Multi-Tenant Scoping | Audit Logger | JWT Auth Middleware          │
└─────────┬───────────────────┬──────────────────────┬────────────────────┬─────────┘
          │                   │                      │                    │
          ▼                   ▼                      ▼                    ▼
┌──────────────────┐ ┌─────────────────┐ ┌──────────────────────┐ ┌────────────────┐
│ DOCUMENT INTEL   │ │ DETERMINISTIC   │ │ MATHEMATICAL         │ │ AGENTIC        │
│ & QUALITY GATE   │ │ FINANCIAL MATH  │ │ OPTIMIZATION         │ │ ORCHESTRATION  │
│ - PyMuPDF / OCR  │ │ - Python Decimal│ │ - Google OR-Tools    │ │ - LangGraph    │
│ - pdfplumber     │ │ - 14-Factor Cost│ │   MILP Solver        │ │ - 9 Agents     │
│ - openpyxl       │ │ - Net Inventory │ │ - Capacity Bounds    │ │ - Multilingual │
│ - Quarantine     │ │ - Scrap Yields  │ │ - MOQ & Budget Split │ │   (EN/HI/HING) │
└──────────────────┘ └─────────────────┘ └──────────────────────┘ └────────────────┘
          │                   │                      │                    │
          └───────────────────┴──────────┬───────────┴────────────────────┘
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                            RELATIONAL PERSISTENCE LAYER                           │
│                 PostgreSQL (Docker) / SQLite Local Fallback Engine                │
│    [Suppliers] [Materials] [Inventory] [BOMs] [Quotations] [Negotiations] [Audit] │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 1. The Zero-Hallucination Separation Principle
- **Code owns the numbers; models own the words.**
- Large Language Models are strictly prohibited from calculating landed costs, taxes, scrap yields, or selling prices. All financial computations execute in pure, tested Python services using `Decimal` arithmetic.

### 2. Multi-Format Quotation Processing with Quality Gate
- Ingests PDFs, scanned documents, Excel sheets, and images.
- An automated **Quality Gate** quarantines documents with missing prices, unverified suppliers, or expired validity, requiring human review before saving.

### 3. Google OR-Tools Procurement Optimization
- Mixed-Integer Linear Programming (MILP) solver that determines the optimal purchasing split across suppliers respecting capacity limits, MOQs, lead time bounds, and budget ceilings.

### 4. Autonomous Negotiation State Machine
- Manages multi-round supplier dialogues with evidence-backed counteroffers.
- Features a high-fidelity simulated vendor response engine modeling realistic concession curves for demonstrations.
- **Mandatory Human Approval Safeguard:** External commitments and counteroffers require explicit human sign-off.

### 5. Deterministic 14-Factor Manufacturing Cost Engine
- Accurately models raw material, cutting scrap, operator labor, machine amortization, electricity kWh, finishing, and factory overheads.
- Features an automated **Loss-Making Order Alert** to prevent underpricing.

### 6. Multilingual Conversational Copilot
- Understands English, Hindi, and Hinglish queries (e.g., *"500 brackets ke liye material shortage check karo"*).

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.11+ (or `uv`)
- Node.js 18+ & npm
- Docker & Docker Compose (optional for containerized deployment)

### Option A: Local Development (Instant Launch)

#### 1. Backend Setup (FastAPI)
```bash
cd backend
# Create virtual environment and install dependencies
uv venv
.\.venv\Scripts\activate   # On Linux/macOS: source .venv/bin/activate
uv pip install -r requirements.txt

# Start backend server (auto-seeds demo data)
uvicorn app.main:app --reload --port 8000
```
Backend API will be running at `http://localhost:8000`. Interactive documentation at `http://localhost:8000/docs`.

#### 2. Frontend Setup (Next.js)
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

### Option B: Docker Compose (Full Stack)
```bash
docker-compose up --build
```
This spins up PostgreSQL, the FastAPI backend, and the Next.js frontend in isolated containers.

---

## 🧪 Running Automated Tests

IndusPilot features a comprehensive automated integration and unit test suite covering all 12 core domains:
```bash
cd backend
pytest tests/test_induspilot_core.py -v
```
**Test Coverage:**
- `test_health_check`: API Gateway health
- `test_dashboard_metrics`: Live KPI computation
- `test_suppliers_directory`: Vendor catalog & ratings
- `test_materials_and_inventory`: Stock levels & reorder alerts
- `test_bom_explosion_and_netting`: Bill of Materials scrap yield & shortage netting
- `test_supplier_comparison_scoring`: 5-factor weighted scorecard
- `test_google_ortools_optimization`: MILP supplier allocation solver
- `test_manufacturing_cost_engine`: 14-factor production costing
- `test_negotiation_workflow_and_simulation`: Counteroffer state machine & concessions
- `test_customer_quotation_and_pdf`: Commercial quote & PDF generation
- `test_multilingual_copilot`: English and Hinglish NLP routing
- `test_approvals_flow`: Human authorization safeguards

---

## 📋 Hackathon Canonical Walkthrough

For the full step-by-step judge demonstration script for **500 Stainless Steel Industrial Brackets**, see:  
👉 [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md)

Additional Architecture & Reference Documents:
- [`docs/INDUSTRY_ANALYSIS.md`](docs/INDUSTRY_ANALYSIS.md): Manufacturing Procurement & Costing Architecture Analysis
- [`docs/SUPPLIER_INTELLIGENCE.md`](docs/SUPPLIER_INTELLIGENCE.md): Supplier Intelligence Subsystem & Deduplication
- [`docs/DOCUMENT_PROCESSING.md`](docs/DOCUMENT_PROCESSING.md): Ingestion Pipeline, OCR, & Material Matcher
- [`docs/QUOTATION_DATA_SCHEMA.md`](docs/QUOTATION_DATA_SCHEMA.md): Quotation Audit Trail & Data Schemas
- [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md): System components, data flows, and API boundaries
- [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md): Complete relational entity dictionary
- [`docs/API_DOCUMENTATION.md`](docs/API_DOCUMENTATION.md): OpenAPI specification and payload examples

---

## ⚖️ License

- Developed independently as an original software platform for **Tech4Bharat 2026** under the MIT License.
- All demonstration vendor records, material prices, and customer orders are synthetic and clearly tagged (`is_simulated = True`).

