# IndusPilot — Hackathon Demonstration Guide

**Project:** IndusPilot (Agentic AI for Intelligent Manufacturing Procurement & Quotation Optimisation)  
**Hackathon:** Tech4Bharat 2026 (The GAVS Hackathon)  
**Theme:** Industrial Manufacturing  
**Problem Statement:** 4.1 — Raw Material Procurement and Manufacturing Quotation Optimisation  
**Presenter:** IndusPilot Team  

---

## 1. 60-Second Elevator Pitch

> *"Most Indian MSME manufacturing workshops don't lose money on the shop floor; they lose money at the desk. Quotations arrive in messy PDFs and WhatsApp messages; owners guess material scrap yields, overlook freight charges, and pick vendors on unit price alone without checking lead times or minimum order quantities. Then, they quote customers based on gut feel, accidentally winning loss-making contracts.*
>
> *IndusPilot solves this end-to-end. It ingests messy vendor quotes through OCR and a strict Quality Gate, explodes Bills of Materials with scrap allowances, optimizes multi-vendor purchasing using Google OR-Tools, negotiates better commercial terms through an autonomous agent state machine, and calculates deterministic 14-factor manufacturing costs to generate guaranteed-profitable customer quotes. **Buy smarter. Calculate accurately. Manufacture profitably.**"*

---

## 2. The Canonical Hackathon Demo Scenario

**Enterprise Profile:** Apex Precision Fabrication Works Pvt Ltd (Peenya Industrial Area, Bengaluru)  
**Customer Order:** 500 Stainless Steel 304 Industrial Mounting Brackets (Part #`SS304-BRK-500`)  
**Customer:** Larsen Heavy Machinery Corp  

---

## 3. Step-by-Step Live Demonstration Script

### Step 1: Business Dashboard & Morning Briefing
- **URL:** `http://localhost:3000` (or `http://localhost:8000/docs`)
- **Action:** Open the Executive Dashboard.
- **What to show judges:**
  - Real-time KPIs: ₹9.03 Lakh active procurement spend, 10 registered suppliers, active quotations, and pending human approvals.
  - Notice the **Zero-Fabrication Metric Principle**: All dashboard figures compute from actual database records.

### Step 2: Bill of Materials & Inventory Shortage Audit
- **URL:** `http://localhost:3000/bom` (or `POST /api/v1/bom/explode`)
- **Action:** Select "Stainless Steel Industrial Bracket" and input batch size = 500 units.
- **What to explain:**
  - Standard bracket requires 2.0 kg net SS304 plate.
  - With CNC laser cutting and press brake scrap ($5\%$), gross requirement is $2.1\text{ kg} \times 500 = \mathbf{1,050\text{ kg}}$.
  - The system inspects warehouse inventory: $250\text{ kg}$ on hand, $50\text{ kg}$ reserved for another job, leaving $200\text{ kg}$ available.
  - With $50\text{ kg}$ safety stock, net shortage is calculated deterministically:
    $$\text{Shortage} = 1050 + 50 - 200 = \mathbf{900\text{ kg}}$$
  - **Judge Takeaway:** The system prevented an expensive under-purchase mistake before issuing requisitions.

### Step 3: Quotation Ingestion & Quality Gate Quarantine
- **URL:** `http://localhost:3000/quotations/upload` (or `POST /api/v1/quotations/upload`)
- **Action:** Upload the sample PDF quotation `apex_steel_quotation_ss304.pdf`.
- **What to explain:**
  - PyMuPDF and OCR extract: Supplier Name (*Apex Steel & Alloys*), Grade (*SS304 2B*), Quoted Rate (*₹315/kg*), Freight (*₹4,500*), MOQ (*200 kg*), Lead Time (*6 Days*), and Tax (*GST 18%*).
  - Show the **Quality Gate**: If a document has an expired validity date or missing price, it is quarantined for human review rather than hallucinating financial data.

### Step 4: Explainable Multi-Dimensional Supplier Comparison
- **URL:** `http://localhost:3000/compare` (or `POST /api/v1/compare/evaluate`)
- **Action:** Compare the 3 vendor quotations side by side:
  1. **Bharat Forgings:** ₹298/kg, Freight ₹6,000, MOQ 500kg, 12 Days Lead Time, Reliability 78%
  2. **Apex Steel:** ₹315/kg, Freight ₹4,500, MOQ 200kg, 6 Days Lead Time, Reliability 92%
  3. **Deccan Precision:** ₹330/kg, Freight ₹3,000, MOQ 100kg, 4 Days Lead Time, Reliability 96%
- **What to explain:**
  - A naive buyer would pick Bharat Forgings solely because ₹298 is the lowest face price.
  - IndusPilot evaluates **Total Landed Cost** (incorporating freight and GST) and executes the **5-Factor Weighted Scorecard**:
    - Cost (35%), Quality (25%), Delivery Reliability (15%), Lead Time (15%), Payment Terms (10%).
  - **Result:** Apex Steel earns the highest composite score (**84.8/100 - Strongly Recommended**) due to rapid delivery and superior reliability, protecting the factory from assembly line stoppage.

### Step 5: Autonomous Negotiation & Simulated Vendor Concession
- **URL:** `http://localhost:3000/negotiation` (or `POST /api/v1/negotiation/start`)
- **Action:** Initiate negotiation with Apex Steel. Target price = ₹295/kg.
- **What to explain:**
  - The Negotiation Agent synthesizes order volume (800 kg), competitor pricing benchmarks (₹298/kg), and drafts an evidence-backed counteroffer proposing ₹295/kg with improved 15-day payment terms.
  - **Human-in-the-Loop Safeguard:** The counteroffer is held in `READY_FOR_APPROVAL` state. No email is sent without owner authorization.
  - Owner clicks "Approve & Send".
  - Apex Steel replies (simulated concession curve): Compromises to **₹305.00/kg**, saving **₹8,000.00** on the batch!

### Step 6: Google OR-Tools Mathematical Procurement Optimization
- **URL:** `http://localhost:3000/optimizer` (or `POST /api/v1/optimizer/solve`)
- **Action:** Run the procurement allocation solver for 800 kg under a ₹2.65 Lakh budget ceiling.
- **What to explain:**
  - In real manufacturing, single vendors often hit capacity limits.
  - Google OR-Tools formulates a Mixed-Integer Linear Program (MILP) considering supplier capacities, MOQs, freight charges, and lead times.
  - The solver finds the mathematically optimal split and explains the binding constraints.

### Step 7: Deterministic 14-Factor Manufacturing Cost Intelligence
- **URL:** `http://localhost:3000/costing` (or `POST /api/v1/costing/calculate`)
- **Action:** Calculate production cost for the 500 brackets.
- **What to explain:**
  - **Zero-Hallucination Rule:** Calculations use Python `Decimal`.
  - Computes 14 distinct line items:
    1. Raw Material base + Scrap allowance
    2. Direct Operator Labor ($120\text{ hrs} \times ₹180/\text{hr} = ₹21,600$)
    3. Machine Operating Amortization ($45\text{ hrs} \times ₹350/\text{hr} = ₹15,750$)
    4. Electricity Tariffs ($650\text{ kWh} \times ₹8.50 = ₹5,525$)
    5. Passivation & Surface Finishing ($₹18,000$)
    6. Packaging & Inbound Freight ($₹11,000$)
    7. Factory Overhead ($12\%$ of direct prime cost)
  - **Total Cost per Bracket (Break-Even):** **₹637.00**

### Step 8: Customer Quotation Generation & Commercial PDF
- **URL:** `http://localhost:3000/customer-quotes` (or `POST /api/v1/customer-quotes/generate`)
- **Action:** Generate commercial quotation for Larsen Heavy Machinery with a target gross margin of 25%.
- **What to explain:**
  - Selling Price per Bracket: **₹850.00** (Margin: 25.1%, Gross Profit: ₹1.06 Lakh).
  - The system tests against break-even ($₹850 > ₹637$). If an operator inputs an under-costed price (e.g. ₹600), the system displays a high-visibility **Loss-Making Contract Warning** and blocks dispatch.
  - Download and open the professional industrial PDF quotation ready for corporate client delivery.

### Step 9: Multilingual Conversational AI Copilot (Hindi & Hinglish)
- **URL:** `http://localhost:3000/copilot` (or `POST /api/v1/copilot/chat`)
- **Action:** Test natural-language queries:
  - English: *"Compare supplier quotations for stainless steel 304"*
  - Hinglish: *"500 brackets ke liye material shortage check karo aur batao kitna stock chahiye"*
- **What to explain:**
  - Shows that Indian MSME workshop managers and supervisors can interact in their everyday business language while the backend executes strict deterministic calculations.

---

## 4. Key Questions & Rebuttals for Judges

| Likely Judge Question | IndusPilot Answer |
| :--- | :--- |
| **"Why not just use an Excel spreadsheet or ERP?"** | Excel files are static, siloed, and don't read vendor quotation PDFs automatically, nor do they run multi-supplier mathematical integer optimization or autonomous negotiation counter-offers. Traditional ERPs (SAP/Oracle) are too complex and expensive for small factory owners. |
| **"How do you ensure the AI doesn't hallucinate numbers?"** | **The Separation Principle:** LLMs are strictly prohibited from performing arithmetic. All landed costs, BOM scrap, scoring, factory overheads, and selling prices execute in tested Python services using `Decimal` precision. |
| **"What if the supplier sends a messy handwritten quote?"** | Our multi-stage pipeline combines PyMuPDF, pdfplumber, and openpyxl with a strict **Quality Gate**. If OCR confidence is low or fields are missing, it quarantines the document for human confirmation rather than making up numbers. |
| **"Does the agent place orders automatically without owner approval?"** | Never. Every purchasing commitment, counteroffer dispatch, and customer quote requires explicit human approval via our Approval Centre. |
| **"What if the user has no OpenAI or Gemini API key?"** | The system features a **Zero-Key Deterministic Fallback**: every service, parser, scoring engine, and template generator operates completely offline without external API dependencies. |

