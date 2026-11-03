# IndusPilot Customer Quotation Engine & Commercial Margin Guard

## 1. Executive Summary & Objective

The IndusPilot Customer Quotation Engine translates audited factory production costs into profitable, defensible, professional customer quotations.

By linking directly to the Phase 5 Manufacturing Costing Engine (which aggregates raw material shortages, direct labor, CNC machine depreciation, electricity tariffs, secondary processes, and packaging), the customer quotation module guarantees:
1. Complete mathematical distinction between **Gross Margin %** and **Markup %**.
2. Automated detection and blocking of **loss-making orders**.
3. Deterministic calculation using Python's `Decimal` type with `ROUND_HALF_UP` precision.
4. Flexible discount and GST schedules.
5. Instant generation of customer-facing ReportLab PDF quotations with zero missing fonts or glyph glitches.

---

## 2. Mathematical Precision: Gross Margin vs. Markup

A frequent failure mode in industrial quoting is confusing margin on revenue with markup on cost. IndusPilot enforces exact definitions:

### Definitions:
- **Unit Production Cost ($C$):** Audited cost to manufacture one finished unit (₹/unit).
- **Unit Selling Price ($P$):** Quoted price billed to the customer (₹/unit).
- **Unit Gross Profit ($G$):** $G = P - C$.

### Gross Margin % (Profit relative to Selling Price):
$$\text{Gross Margin \%} = \frac{P - C}{P} \times 100$$
$$P = \frac{C}{1 - \frac{\text{Margin \%}}{100}}$$

### Markup % (Profit relative to Production Cost):
$$\text{Markup \%} = \frac{P - C}{C} \times 100$$
$$P = C \times \left(1 + \frac{\text{Markup \%}}{100}\right)$$

### Conversion Equivalence Table:
| Production Cost ($C$) | Quoted Price ($P$) | Gross Margin % | Markup % | Profitability Status |
| :--- | :--- | :--- | :--- | :--- |
| ₹637.00 | ₹850.00 | **25.06%** | **33.44%** | `PROFITABLE` |
| ₹637.00 | ₹750.00 | **15.07%** | **17.74%** | `PROFITABLE` (Min Margin) |
| ₹637.00 | ₹700.00 | **9.00%** | **9.89%** | `BELOW_TARGET_MARGIN` |
| ₹637.00 | ₹637.00 | **0.00%** | **0.00%** | `BREAK_EVEN` |
| ₹637.00 | ₹600.00 | **-6.17%** | **-5.81%** | `LOSS_MAKING` (BLOCKED) |

---

## 3. Commercial Discount & GST Schedule

IndusPilot handles invoice subtotaling, multi-tier volume discounts, and Indian Goods and Services Tax (GST) schedules deterministically:

1. **Gross Revenue:**
   $$\text{Gross Revenue} = Q \times P$$
2. **Volume Discount:**
   $$\text{Discount Amount} = \text{Gross Revenue} \times \frac{\text{Discount \%}}{100}$$
3. **Discounted Subtotal:**
   $$\text{Subtotal} = \text{Gross Revenue} - \text{Discount Amount}$$
4. **GST Tax Schedule:**
   $$\text{Tax Amount} = \text{Subtotal} \times \frac{\text{Tax \%}}{100}$$
   *(Supported GST brackets: 0% Exempt, 5%, 12%, 18% Standard Industrial, 28% Luxury/Automotive)*
5. **Gross Total (Invoice Value):**
   $$\text{Total Invoice Amount} = \text{Subtotal} + \text{Tax Amount}$$

---

## 4. Python Decimal Implementation

To eliminate floating-point imprecision (e.g., `0.1 + 0.2 = 0.30000000000000004`), every monetary quantity is quantized to two decimal places using Python's `Decimal` module:

```python
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
cost = Decimal(str(unit_cost)).quantize(CENT, rounding=ROUND_HALF_UP)
price = Decimal(str(unit_selling_price)).quantize(CENT, rounding=ROUND_HALF_UP)
subtotal = (price * Decimal(str(quantity))).quantize(CENT, rounding=ROUND_HALF_UP)
tax = (subtotal * (Decimal(str(tax_pct)) / Decimal("100"))).quantize(CENT, rounding=ROUND_HALF_UP)
total = (subtotal + tax).quantize(CENT, rounding=ROUND_HALF_UP)
```

---

## 5. Loss-Making Contract Protection

Whenever $P < C$ or $\text{Gross Margin \%} < 0$:
1. The quote is marked `is_loss_making = True` and `profitability_status = "LOSS_MAKING"`.
2. Initial lifecycle status is automatically forced to `NEEDS_REVIEW` and `approval_status = "REJECTED"`.
3. Standard dispatch and sending to client are blocked.
4. A mandatory Commercial Director override is required to approve below-cost quotations (e.g. strategic entry into new automotive accounts).

