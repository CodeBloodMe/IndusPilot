# IndusPilot — Manufacturing Procurement & Costing Architecture Analysis

**Project:** IndusPilot (Agentic AI for Intelligent Manufacturing Procurement & Quotation Optimisation)  
**Hackathon:** Tech4Bharat 2026 (The GAVS Hackathon)  
**Theme:** Industrial Manufacturing  
**Problem Statement:** 4.1 — Raw Material Procurement and Manufacturing Quotation Optimisation  
**Author:** IndusPilot Core Engineering Team  

---

## 1. Industry Landscape & Comparative Technology Matrix

Indian MSME factories in precision engineering and metal fabrication frequently struggle with fragmented tooling. The matrix below contrasts conventional industry approaches with the unified **IndusPilot** architecture:

| Architectural Dimension | Manual MSME Practice (WhatsApp / Excel) | Legacy Enterprise ERP (SAP Ariba / Oracle) | Generic Generative AI (ChatGPT / Copilots) | IndusPilot Proprietary Platform |
| :--- | :--- | :--- | :--- | :--- |
| **Procurement Workflow** | Unstructured email threads, phone calls, unindexed paper printouts. | Heavy procurement portals requiring extensive supplier training and license fees. | Isolated text prompting without ERP integration or operational awareness. | **End-to-end closed loop:** Requirement $\to$ BOM explosion & scrap yields $\to$ Inventory netting & shortage $\to$ OCR quote ingestion $\to$ 5-factor scoring $\to$ OR-Tools MILP optimization $\to$ Autonomous negotiation $\to$ 14-factor manufacturing costing $\to$ Customer quotation. |
| **AI Agents & Intelligence** | None (manual estimator cognitive load). | Static decision trees and rules engines without autonomous agents. | Single-prompt chatbots prone to mathematical hallucination. | **9 Specialized Autonomous Agents in LangGraph:** Requirement Agent, Document Intelligence Agent, Supplier Intelligence Agent, Procurement Planning Agent, Negotiation Agent, Cost Intelligence Agent, Optimization Agent, Customer Quotation Agent, Supervisor Agent. |
| **Supplier Evaluation** | Evaluates only sticker rate, ignoring freight, tax, and credit terms. | Vendor scorecards based primarily on volume spend, slow to update. | Subjective qualitative opinions without numerical grounded benchmarks. | **Explainable 5-Factor Weighted Scorecard:** Cost Competitiveness (35%), Quality (25%), Delivery Reliability (15%), Lead Time (15%), Payment Terms (10%) with transparent decision bands and neutral imputation for missing data. |
| **Quotation Negotiation** | Ad-hoc phone bargaining without reservation bounds or data backing. | Rigid reverse auctions hostile to MSME vendor relationships. | Generic drafted text without concession curve models or reservation ceilings. | **Formal State Machine:** (`DRAFT` $\to$ `READY_FOR_APPROVAL` $\to$ `APPROVED_TO_SEND` $\to$ `SENT` $\to$ `RESPONSE_RECEIVED` $\to$ `CLOSED`) with simulated vendor concession curves and mandatory human approval. |
| **Document Processing** | Manual retyping of WhatsApp PDFs and Excel rows into spreadsheets. | EDI and strict XML format mandates which small Indian vendors cannot produce. | OCR without domain quality gate; parses text but misses manufacturing grades. | **Multi-Format Ingestion & Quality Gate:** Native PyMuPDF, pdfplumber, and openpyxl OCR parsing for PDF, Excel, and scans; flags confidence scores and quarantines incomplete records for human review. |
| **Procurement Optimisation** | Single-vendor heuristic ("we always buy from dealer X"). | Linear single-winner auctions without real-time shop-floor capacity bounds. | None (cannot solve linear integer programming constraints). | **Google OR-Tools MILP Solver:** Multi-supplier split optimization under Minimum Order Quantity (MOQ), monthly vendor capacity, delivery deadlines, and budget ceilings. |
| **Database & Audit Trail** | Lost in personal chat histories and corrupted local `.xlsx` files. | Monolithic proprietary schemas with costly cloud lock-in. | Stateless memory caches lost after conversational session ends. | **Relational PostgreSQL / SQLAlchemy:** 20 tables with multi-tenant foreign keys (`organization_id`), strict `NUMERIC(14,2)` monetary types, and audit logging. |
| **Manufacturing Costing** | Rule-of-thumb guestimates (e.g., "$2.5 \times \text{material weight}$") resulting in loss-making quotes. | Generic standard costing detached from dynamic daily raw metal prices. | None (treats purchasing as finished retail items without conversion costs). | **Deterministic 14-Factor Engine:** Strict Python `Decimal` arithmetic calculating raw material, scrap yields, direct labor, machine depreciation, electricity tariffs, and factory overheads with loss-making contract alerts. |

---

## 2. Core Architectural Pillars

### 2.1 Deterministic Engineering Guarantee
IndusPilot operates under a strict principle: **AI never does the financial arithmetic.**
- Every unit price calculation, GST addition, freight distribution, and currency sum is executed using deterministic Python `Decimal` operations.
- Google OR-Tools executes Mixed-Integer Linear Programming (MILP) mathematically, guaranteeing exact optimal solutions without floating-point error.

### 2.2 Ingestion Resilience & Quality Gate
Raw material quotations arrive in unstructured PDF tables, Excel sheets, and smartphone photos. IndusPilot's Multi-Format Ingestion Engine parses these formats deterministically, extracting:
- Material Grade & Specifications (ASTM/IS standards)
- Material Thickness & Physical Form (Sheet, Plate, Bar, Coil)
- Minimum Order Quantities & Delivery Lead Times
- True Landed Cost Structure (Base price + Tax + Freight + Handling)

Records failing validation are immediately isolated in a **Quarantine State**, safeguarding downstream costing engines from corrupt estimates.

### 2.3 Shop-Floor Grounded Costing
Unlike commercial trading platforms that treat items as discrete commodities, IndusPilot recognizes that manufacturing involves physical conversion:
- Sheet metal laser cutting incurs scrap wastage percentages.
- Press brakes and CNC machines consume kilowatt-hour electricity and operator labor.
- Surface treatments (powder coating, passivation) add secondary processing costs.

IndusPilot bridges supplier procurement directly into the final customer quotation, guaranteeing that manufacturers never bid at a loss.

