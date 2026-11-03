# Tech4Bharat 2026 — Official Hackathon Requirements & Problem Analysis

**Hackathon:** Tech4Bharat 2026 (The GAVS Hackathon)  
**Portal:** [https://thegavshackathon.com/challenges](https://thegavshackathon.com/challenges)  
**Selected Theme:** Industrial Manufacturing  
**Selected Problem Statement:** 4.1 — Raw Material Procurement and Manufacturing Quotation Optimisation  
**Target Solution:** IndusPilot  

---

## 1. Explicit Organiser Requirements

The following requirements and evaluation criteria are drawn directly from the official Tech4Bharat 2026 challenge specification:

### 1.1 Problem Focus
- **Theme:** Industrial Manufacturing.
- **Problem Statement 4.1:** Raw material procurement and manufacturing quotation optimisation for industrial MSMEs.
- **Core Challenge:** Indian manufacturing small and medium enterprises (MSMEs) struggle with fragmented raw material purchasing processes, volatile spot market prices, manual comparison of unstructured vendor quotes, and inaccurate customer quotation generation that leads to loss-making orders.

### 1.2 Target Audience
- Small and medium-scale manufacturing business owners, plant heads, procurement managers, and commercial cost estimators in sectors such as:
  - Metal fabrication and laser cutting
  - Industrial machinery components and fasteners
  - Plastic injection molding and polymers
  - Electrical equipment and panel manufacturing
  - General industrial subcontracting

### 1.3 Expected Solution Capabilities
1. **Raw Material Procurement Optimisation:** Assist factories in identifying competitive suppliers, processing unstructured quotations, factoring in Minimum Order Quantities (MOQ), landed transportation costs, and delivery lead times.
2. **Manufacturing Quotation Optimisation:** Accurately estimate production costs based on raw material requirements, scrap/wastage allowances, labor, machine operating amortizations, and electricity tariffs to generate profitable customer quotations.
3. **Usability & Accessibility:** A practical software system that can be deployed and operated by factory owners without requiring enterprise ERP complexity.

### 1.4 Official Evaluation Criteria
- **Relevance & Problem Fit:** How accurately the solution addresses MSME manufacturing procurement and quotation friction.
- **Technical Rigor & Architecture:** Clean modular architecture, database design, deterministic financial precision, and algorithmic optimization.
- **Agentic AI Capabilities:** Practical coordination of specialized AI agents rather than a generic single-prompt chatbot.
- **Commercial Viability & Completeness:** A working, testable product with realistic industrial workflows and clear business value.

---

## 2. Our Interpretation of the Problem

1. **The Dual Squeeze in MSME Manufacturing:**
   - MSMEs operate on thin gross margins ($8\%$ to $25\%$).
   - A $4\%$ error in raw material procurement or an uncalculated $6\%$ scrap yield during laser cutting or stamping can completely wipe out the profit of an entire manufacturing run.
   
2. **The "Zero-Hallucination" Necessity:**
   - In financial and manufacturing operations, probabilistic AI hallucinations are catastrophic. If an LLM hallucinates a raw material price of ₹250/kg instead of ₹315/kg, the factory quotes ₹700 per finished unit instead of ₹850, winning an order that loses ₹75,000.
   - **IndusPilot Rule:** The LLM's role is strictly cognitive (understanding text, organizing drafts, coordinating workflows). All arithmetic, landed costs, and selling prices must be computed deterministically with Python `Decimal`.

3. **Multi-Format Document Chaos:**
   - Indian suppliers submit quotations over WhatsApp, scanned PDFs, handwritten chits, and Excel spreadsheets with inconsistent tax terms (GST included vs extra) and vague freight conditions. The system must standardize these through OCR with a strict Quality Gate quarantine.

4. **Human-in-the-Loop Safeguards:**
   - Autonomous purchasing without human oversight creates legal and financial risk. The system must prepare recommendations and counteroffers, but require explicit operator sign-off before any binding external action.

---

## 3. Additional Value-Added Features Implemented in IndusPilot

The following features were developed to strengthen the core problem statement without distracting from it:

1. **Google OR-Tools Mixed-Integer Linear Programming (MILP):**
   - Solves multi-vendor split allocations when a single supplier cannot fulfill the entire volume within the required deadline or when splitting volume across vendors with different MOQs minimizes total landed cost.
   
2. **Multi-Round Autonomous Negotiation State Machine:**
   - Implements a formal state machine (`DRAFT` $\to$ `READY_FOR_APPROVAL` $\to$ `APPROVED_TO_SEND` $\to$ `SENT` $\to$ `RESPONSE_RECEIVED` $\to$ `CLOSED`) that synthesizes order volumes and competitor benchmarks to draft counteroffers and simulate realistic vendor concessions.

3. **Deterministic 14-Factor Manufacturing Cost Engine:**
   - Models the full shop-floor conversion cost: raw material, scrap yield, direct labor, CNC machine center depreciation, electricity kilowatt-hour tariffs, surface finishing (passivation/powder coating), freight, packaging, and allocated factory overheads.

4. **Loss-Making Contract Safeguard:**
   - An automated mathematical check comparing quoted selling prices against break-even unit costs, triggering high-visibility alerts if an operator attempts to issue an underpriced quote.

5. **Client-Ready PDF Quotation Export:**
   - Automatic generation of professional commercial customer quotation PDFs with dimensional specifications, delivery schedules, payment terms, and an internal engineering margin audit.

6. **Multilingual SME Voice/Text Interface:**
   - Native support for English, Hindi, and Hinglish queries tailored to workshop supervisors (e.g., *"500 brackets ke liye material shortage check karo"*).

---

## 4. Features Requiring Validation with Actual Manufacturers

Before enterprise commercial rollout, the following advanced capabilities should be validated directly with manufacturing plant managers:

1. **Dynamic Scrap Recovery / Scrap Resale Credits:**
   - In heavy metal stamping, scrap metal (punching offcuts, turnings) is sold back to recyclers at 40-60% of prime raw material cost. Incorporating scrap salvage revenue into net production costs should be validated with scrap dealers and accountants.

2. **Multi-Tier Subcontractor Job-Work Tracking:**
   - When secondary processes (e.g., heat treatment, electroplating) are outsourced to external job-work vendors, tracking outward delivery challans (Annexure IV / Rule 55 under GST) will require ERP integration.

3. **Live WhatsApp Business API Integration:**
   - Direct parsing of inbound supplier WhatsApp messages and PDF attachments via the official WhatsApp Business Cloud API requires meta-verified business numbers and webhooks.

4. **Real-Time Commodity Exchange Feeds:**
   - Auto-updating base metal benchmark prices from MCX (Multi Commodity Exchange of India) and LME (London Metal Exchange) for continuous spot-price indexing.

