# IndusPilot Landed Cost Calculation Engine

## 1. Architectural Principles

In industrial manufacturing procurement, evaluating quotations based solely on the supplier's quoted "face price" is one of the most common causes of manufacturing margin erosion. Freight charges, GST tax treatments, packaging overhead, payment terms, and transit insurance regularly distort the true economic cost by 5% to 22%.

IndusPilot implements a **deterministic financial calculation engine** (`backend/app/calculations/landed_cost.py`) governed by three strict architectural principles:

1. **Deterministic Precision:** All monetary amounts, quantities, and rates are represented and computed using Python's arbitrary-precision `Decimal` type with `ROUND_HALF_UP` rounding to two decimal places (`Decimal("0.01")`). Floating-point arithmetic is strictly prohibited in financial paths.
2. **Deterministic Code Ownership:** Large Language Models (LLMs) are strictly prohibited from performing financial arithmetic. Code owns the numbers; models only own narrative synthesis.
3. **Audit Completeness & Defensibility:** Every line item in the calculation must be traceable to the original vendor quotation, contract terms, or benchmark transport tables. If the tax status is unknown, the engine halts evaluation and flags an audit exception rather than guessing.

---

## 2. Mathematical Formulation

The Total Landed Cost (\(TLC\)) and Effective Unit Landed Cost (\(ULC\)) for an order of quantity \(Q\) of raw material at base price \(P_{\text{unit}}\) are defined as:

$$\text{Gross Material Cost} = P_{\text{unit}} \times Q$$

$$\text{Net Material Cost} = \max(0, \text{Gross Material Cost} - \text{Discounts})$$

$$\text{Tax Base} = \begin{cases} 
\text{Net Material Cost} & \text{if Tax Treatment is } \texttt{TAX\_EXCLUDED} \\
\dfrac{\text{Net Material Cost}}{1 + \frac{r_{\text{GST}}}{100}} & \text{if Tax Treatment is } \texttt{TAX\_INCLUDED} \\
\text{Net Material Cost} & \text{if Tax Treatment is } \texttt{NO\_TAX}
\end{cases}$$

$$\text{GST Amount} = \begin{cases}
\text{Tax Base} \times \dfrac{r_{\text{GST}}}{100} & \text{if } \texttt{TAX\_EXCLUDED} \\
\text{Net Material Cost} - \text{Tax Base} & \text{if } \texttt{TAX\_INCLUDED} \\
0 & \text{if } \texttt{NO\_TAX}
\end{cases}$$

$$\text{Total Landed Cost} = (\text{Tax Base} + \text{GST Amount}) + C_{\text{freight}} + C_{\text{packaging}} + C_{\text{insurance}} + C_{\text{customs}} + C_{\text{other}}$$

$$\text{Effective Unit Landed Cost} = \dfrac{\text{Total Landed Cost}}{Q}$$

---

## 3. Tax Treatments (`TaxTreatment` Enum)

Indian industrial procurement operates under the Goods and Services Tax (GST) regime. Suppliers quote prices under different conventions:

| Mode | Enum Value | Description | Mathematical Handling |
|---|---|---|---|
| **Tax Excluded** | `TAX_EXCLUDED` | Quoted price is ex-factory, basic rate. GST is added on top. | \(\text{GST} = \text{Net} \times (r / 100)\). Total includes Net + GST. |
| **Tax Included** | `TAX_INCLUDED` | Quoted price is inclusive of GST. | Reverse calculated: \(\text{Base} = \text{Net} / (1 + r / 100)\). Prevents double-counting. |
| **Zero Tax / Exempt** | `NO_TAX` | Nil-rated, SEZ supply, or exempt under GST. | \(\text{GST} = 0\). Base = Net. |
| **Unknown** | `UNKNOWN` | Quotation does not declare tax status. | **Execution Blocker:** Engine raises `ValueError` and flags `NEEDS_REVIEW`. Prevents unverified purchases. |

---

## 4. Multi-Item Freight Allocation (`FreightAllocationMethod`)

When a supplier delivers a consolidated shipment containing multiple raw materials or components, freight charges must be allocated accurately across items without skewing individual product unit costs.

IndusPilot supports three deterministic allocation strategies:

### 4.1 Pro-Rata by Value (`PRO_RATA_VALUE`)
Standard for general cargo where transport risk and insurance scale with invoice value:
$$\text{Allocated Freight}_i = C_{\text{total freight}} \times \left( \dfrac{\text{Item Value}_i}{\sum_{j} \text{Item Value}_j} \right)$$

### 4.2 Pro-Rata by Weight (`PRO_RATA_WEIGHT`)
Standard for heavy industrial raw materials (e.g. steel sheets, copper ingots, aluminum bars) where haulage costs are driven by gross payload weight:
$$\text{Allocated Freight}_i = C_{\text{total freight}} \times \left( \dfrac{\text{Item Weight}_i}{\sum_{j} \text{Item Weight}_j} \right)$$

### 4.3 Equal Split (`EQUAL_SPLIT`)
Used for fixed-fee container or trip rates divided equally across standard lots:
$$\text{Allocated Freight}_i = \dfrac{C_{\text{total freight}}}{N}$$

---

## 5. Working Capital & Opportunity Cost of Payment Terms

Credit terms offered by suppliers (e.g., Advance, Immediate Net 0, Net 30, Net 60, Net 90) represent a significant working capital differential.

IndusPilot models the **Cost of Capital Credit Adjustment**:
$$\text{Working Capital Financing Cost} = \text{Invoice Total} \times \left( \dfrac{r_{\text{capital}}}{365} \right) \times \max(0, \text{Days}_{\text{benchmark}} - \text{Days}_{\text{supplier}})$$

Where:
- \(r_{\text{capital}}\) is the factory's annual cost of working capital borrowing (default: 12.0% p.a.).
- When a supplier offers 60 days credit vs an advance payment vendor (0 days), the factory saves:
  $$\text{Savings} = \text{Invoice Total} \times \left( \dfrac{0.12}{365} \right) \times 60 \approx 1.97\% \text{ of invoice}$$
- This differential is integrated into the commercial scoring factor to provide a true financial comparison.

---

## 6. Currency & Foreign Exchange (FX) Conversion

For imported raw materials quoted in foreign currencies (e.g. USD, EUR, SGD):
1. Quoted unit prices and non-INR charges are converted to INR using the certified daily exchange rate (`fx_rate_to_inr`).
2. Customs duty, basic customs cess, and port clearance handling charges are computed on the INR tariff value.
3. GST (IGST) is computed on the post-customs assessable value as per Indian customs regulations.

---

## 7. Verification & Test Evidence

The landed cost engine is verified by comprehensive unit tests in `backend/tests/test_phase4_supplier_comparison.py`:
- `test_landed_cost_tax_exclusive`: Verifies ex-factory addition of 18% GST and auxiliary freight.
- `test_landed_cost_tax_inclusive_no_double_counting`: Verifies reverse tax extraction without double-counting.
- `test_landed_cost_zero_tax_and_discounts`: Verifies volume discount deductions under 0% tax.
- `test_landed_cost_unknown_tax_blocked`: Confirms that quotes with unstated tax trigger audit halts.
- `test_landed_cost_multi_item_freight_allocation`: Tests value-pro-rata and weight-pro-rata allocations across 3 lines.
- `test_landed_cost_currency_conversion`: Validates foreign currency conversion to INR with customs duty.

