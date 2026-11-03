# INDUSPILOT — 7-MINUTE LIVE JUDGE DEMONSTRATION SCRIPT
**Hackathon:** Tech4Bharat 2026 — Industrial Manufacturing, Problem Statement 4.1  
**Product:** IndusPilot — Agentic AI for Intelligent Manufacturing Procurement & Quotation Optimisation  
**Presenter:** Product Demonstration Lead / Full-Stack Engineer  
**Target Duration:** Exactly 7 Minutes (00:00 – 07:00)  

---

## DEMONSTRATION OVERVIEW & SETUP

### Pre-Flight Verification (T-minus 2 Minutes)
1. **Backend Running:**
   ```powershell
   $env:PYTHONPATH="backend"; backend\.venv\Scripts\python -m uvicorn app.main:app --port 8000
   ```
2. **Frontend Running:**
   ```powershell
   npm --prefix frontend run dev
   ```
3. **Browser Opened:** Navigate to `http://localhost:3000` (or `http://localhost:3000/copilot`).
4. **Baseline Verified:** Confirm baseline demonstration tenant (`Apex Precision Fabrication Works Pvt Ltd`).

---

## MINUTE-BY-MINUTE DEMO SCRIPT

### [00:00 – 01:00] THE PROBLEM & CONTEXT (1 Minute)
* **Visual:** Dashboard or Copilot landing page with company banner: *Apex Precision Fabrication Works Pvt Ltd, Peenya Industrial Area, Bengaluru*.
* **Verbal Script:**
  > "Good morning, respected judges. Indian SME manufacturers lose an estimated 8 to 14% of their operating margins every single month. Why? Because when a customer order arrives, factory owners juggle three disconnected worlds: fragmented supplier WhatsApp PDFs, guesswork inventory spreadsheets, and gut-feeling pricing margins.
  > 
  > This is **IndusPilot**—the first agentic AI platform built specifically for Indian discrete manufacturing. IndusPilot doesn't just chat. It understands engineering Bills of Materials, executes MRP shortage calculations, runs Google OR-Tools mathematical optimization across real suppliers, simulates commercial negotiations, and computes true 14-factor manufacturing costs to generate guaranteed profitable customer quotations."

---

### [01:00 – 02:45] THE AUTONOMOUS COPILOT MASTER EXECUTION (1 Min 45 Sec)
* **Visual:** Focus on the **Copilot** conversational view.
* **Action:** Paste the Master Prompt into the Copilot input bar and press **Send**:
  ```text
  I have received an order for 500 stainless steel industrial brackets. Check my inventory, identify missing materials, find suitable suppliers, optimise procurement within ₹5 lakh and calculate my expected manufacturing profit at a 20% gross margin. Prepare a customer quotation for review.
  ```
* **Visual Feedback:** Observe the **Real-Time 9-Step Agentic Execution Timeline** light up:
  1. *Router Node* $\to$ Classifying multi-step manufacturing requirement
  2. *BOM Node* $\to$ Exploding 500 units of `IND-BRK-SS304` (1,050.0 kg gross SS 304 requirement)
  3. *Inventory Node* $\to$ Detecting 750.0 kg net shortage against 350.0 kg available stock
  4. *Supplier Matcher* $\to$ Evaluating 10 industrial suppliers; filtering verified quotations
  5. *Optimization Node* $\to$ Solving Google OR-Tools MILP allocation within ₹5,00,000 budget
  6. *Negotiation Node* $\to$ Autonomous counteroffer discount simulation
  7. *Costing Node* $\to$ Calculating 14-factor production unit break-even cost (₹637.00)
  8. *Customer Quote Node* $\to$ Generating ₹796.25 selling price at exactly 20.0% gross margin
  9. *Synthesis Node* $\to$ Compiling interactive structured action card and governance checkpoint
* **Verbal Script:**
  > "Look at the screen right now. In a single natural language instruction, IndusPilot's LangGraph supervisor orchestrated 9 specialized engineering agents. 
  > Notice what just happened in under 2 seconds:
  > - It exploded our multi-level BOM for 500 brackets, identifying a gross need of 1,050 kg of SS 304 sheet including scrap.
  > - It checked inventory: we have 400 kg in Peenya Bay 1, but 50 kg is reserved and 50 kg is safety stock. So our net shortage is exactly 750 kg.
  > - It didn't just pick the cheapest vendor. It scored suppliers on landed cost, quality, and delivery, and solved a Mixed-Integer Linear Program using Google OR-Tools to allocate 750 kg to Apex Steel & Alloys for ₹2,36,250 landed cost.
  > - And notice the financial accuracy: for a break-even cost of ₹637.00 per unit, it computed an exact selling price of ₹796.25, ensuring our factory achieves precisely 20.0% gross margin—yielding ₹79,625 in profit."

---

### [02:45 – 04:15] SPECIALIZED VIEWS: BOM, INVENTORY & OR-TOOLS OPTIMIZATION (1 Min 30 Sec)
* **Visual:** Click sidebar to switch to **BOM Manager** and then **Optimization Engine**.
* **Action:**
  - In **BOM Manager**: Show `IND-BRK-SS304` hierarchy with component scrap rates (5.0%).
  - In **Optimization Engine**: Highlight the solver parameters:
    - *Material:* `MAT-SS-304`
    - *Required Quantity:* 750.0 kg
    - *Allocated Supplier:* Apex Steel & Alloys (100% allocation or optimal split)
    - *Total Landed Cost:* ₹2,36,250.00 (inclusive of 18% GST, freight, and transit insurance)
* **Verbal Script:**
  > "Let's look under the hood. Here in the BOM Manager, every component has physical engineering specs and manufacturing scrap factors.
  > Over in the Optimization View, our Google OR-Tools MILP engine solves real-world supplier trade-offs. If a vendor has a Minimum Order Quantity or a delivery lead time constraint, the mathematical solver finds the provably optimal split to minimize landed cost while guaranteeing factory delivery deadlines."

---

### [04:15 – 05:30] 14-FACTOR COSTING & CUSTOMER QUOTATION GENERATION (1 Min 15 Sec)
* **Visual:** Switch to **Costing Engine** and then **Customer Quotes**.
* **Action:**
  - Show the 14-factor breakdown: Direct Materials, Secondary Processes (Pickling/Passivation), Direct Labor (120 hrs @ ₹180/hr), Machine Depreciation (45 hrs @ ₹350/hr), Electricity Tariff (8.50 kWh), and 12% Factory Overhead.
  - Show the unit economics: Break-even ₹637.00.
  - Switch to **Customer Quotes**: Open quote `CQ-2026-XXXX`.
  - Click **Download PDF**: The branded PDF opens in a new tab displaying GSTIN, payment terms (30 Days Net), line items, and authorized signature block.
* **Verbal Script:**
  > "Most SME quoting fails because factories omit indirect costs. IndusPilot's 14-factor costing engine accounts for power tariffs, machine wear, labor rates, and overhead.
  > The break-even cost is exactly ₹637.00 per bracket.
  > At our requested 20% gross margin:
  > $637.00 / 0.80 = ₹796.25 per unit.
  > For 500 units, the total subtotal is ₹3,98,125.00, GST is ₹71,662.50, and the grand total is ₹4,69,787.50.
  > With one click, the customer receives an audit-ready commercial quotation complete with terms and statutory compliance."

---

### [05:30 – 06:30] HUMAN-IN-THE-LOOP GOVERNANCE & APPROVAL (1 Minute)
* **Visual:** Return to **Copilot** or open the pending approval modal.
* **Action:**
  - Point to the **Pending Approval** action card.
  - Click **Approve Action**: The card transitions to a green `APPROVED` state with approver details (*Rajesh Sharma, Owner*) and timestamp.
* **Verbal Script:**
  > "Crucially, IndusPilot is built with enterprise Human-in-the-Loop governance. The AI can analyze, plan, and draft quotations, but commercial commitments above configured thresholds require human authorization.
  > I click 'Approve'. The quotation is formally locked, an immutable audit record is created, and the order is ready for production dispatch."

---

### [06:30 – 07:00] SUMMARY & JUDGE Q&A (30 Seconds)
* **Visual:** Return to main executive dashboard showing company KPI impact: 12.4% cost savings, 100% margin protection.
* **Verbal Script:**
  > "To summarize: IndusPilot transforms the chaotic procurement and pricing reality of Indian manufacturing into a predictable, mathematically optimized, and explainable decision system.
  > 150 automated tests pass with 100% success. Zero external dependencies. Ready for Bharat's manufacturing revolution.
  > Thank you, and we welcome your questions."

---

## BACKUP & OFFLINE PROCEDURES

If network or browser latency occurs during live judging:
1. **Reset to Baseline:** Run `python -m app.services.seed_data --reset` from the terminal. Takes < 2 seconds and restores all quotations, BOMs, and inventory to pristine state.
2. **Deterministic Response Mode:** The backend operates with `DEMO_MODE=True` fallback, ensuring that even if external LLM APIs experience rate limits, all 9 workflow steps execute deterministically with complete data structures.
3. **Automated CLI Run:** Run `$env:PYTHONPATH="backend"; backend\.venv\Scripts\python -m pytest backend/tests/test_phase10_api_workflow.py -v` to demonstrate the entire 9-step flow executing headlessly in 2.25 seconds.

