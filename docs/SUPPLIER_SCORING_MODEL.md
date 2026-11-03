# IndusPilot Explainable 5-Factor Supplier Scoring Model

## 1. Overview & Business Rationale

Traditional procurement decisions often suffer from the "Cheapest Vendor Fallacy" — awarding orders to the lowest quoted price regardless of delivery unreliability, high rejection rates, or punitive credit terms. In manufacturing, a 2% cheaper raw material that arrives 14 days late or with a 5% dimensional defect rate will halt production lines, incurring losses that dwarf initial material savings.

IndusPilot implements a **multi-dimensional, explainable 5-factor scoring model** (`backend/app/calculations/scoring.py`). Every quotation is evaluated on a standardized scale from 0 to 100 points, decomposed across five core dimensions:

1. **Total Landed Cost (Default: 35%)**
2. **Quality Track Record (Default: 25%)**
3. **Delivery Reliability (Default: 15%)**
4. **Lead Time Performance (Default: 15%)**
5. **Commercial Payment Terms (Default: 10%)**

---

## 2. Mathematical Normalization & Factor Formulations

### 2.1 Factor 1: Landed Cost Score (\(S_{\text{cost}}\))
Cost is an inverse metric — lower landed cost is superior. We evaluate relative to the best (lowest) landed cost in the candidate batch:

$$S_{\text{cost}} = \max\left(0, 100 \times \left(1.0 - \dfrac{\text{Landed Cost} - \text{Min Landed Cost}}{\text{Min Landed Cost}}\right)\right)$$

- The lowest landed cost candidate receives a score of **100.0**.
- A vendor whose landed cost is 20% higher receives a score of **80.0**.
- A vendor whose landed cost is double (100% higher) receives **0.0**.

### 2.2 Factor 2: Quality Score (\(S_{\text{quality}}\))
Evaluates the supplier's historical rejection rate, ISO/BIS certifications, and Mill Test Certificate (MTC) compliance:

$$S_{\text{quality}} = \min(100, \text{Rating Base} + \text{Cert Bonus} - \text{Defect Penalty})$$

Where:
- Rating Base: Standard supplier quality rating (e.g. 92.0 / 100).
- Cert Bonus: +5 points for ISO 9001:2015 / AS9100 / IATF 16949 certification.
- Defect Penalty: 2 points deducted for each 0.1% historical rejection rate above zero.

### 2.3 Factor 3: Delivery Reliability Score (\(S_{\text{reliability}}\))
Derived from on-time delivery (OTD) percentage across verified historical shipments:

$$S_{\text{reliability}} = \text{Historical OTD \%} = \dfrac{N_{\text{on-time deliveries}}}{N_{\text{total deliveries}}} \times 100$$

Suppliers with consistent on-time fulfillment receive scores approaching 100. Unreliable suppliers are penalised directly.

### 2.4 Factor 4: Lead Time Score (\(S_{\text{lead\_time}}\))
Lead time is normalized against the requested delivery deadline or the fastest quoting supplier in the cohort:

$$S_{\text{lead\_time}} = \begin{cases}
100 & \text{if } \text{Lead Time} \le \text{Min Lead Time} \\
\max\left(0, 100 - \left( \dfrac{\text{Lead Time} - \text{Min Lead Time}}{\text{Max Allowed Lead Time} - \text{Min Lead Time}} \right) \times 100 \right) & \text{otherwise}
\end{cases}$$

If a supplier exceeds the factory's absolute deadline date, the **Supplier Eligibility Engine** marks the quotation as `INELIGIBLE` or `CONDITIONALLY_ELIGIBLE` before scoring.

### 2.5 Factor 5: Commercial Payment Terms Score (\(S_{\text{payment}}\))
Rewards suppliers offering generous credit terms that preserve working capital liquidity:

$$S_{\text{payment}} = \min\left(100, \dfrac{\text{Credit Days}}{90} \times 100\right)$$

- 90 Days Credit \(\rightarrow\) 100 points
- 60 Days Credit \(\rightarrow\) 66.7 points
- 30 Days Credit \(\rightarrow\) 33.3 points
- 100% Advance / Net 0 \(\rightarrow\) 0 points

---

## 3. Dynamic Weight Renormalization for Missing Data

A critical flaw in standard multi-criteria scoring is that a new or unrated supplier is penalised unfairly with a score of 0 for missing historical metrics (e.g., no past deliveries to compute OTD).

IndusPilot implements **Dynamic Weight Renormalization**:
If metric \(k\) is unavailable (missing data), its weight \(w_k\) is zeroed out, and the remaining active weights are dynamically rescaled to sum to 1.0 (100%):

$$w'_i = \dfrac{w_i}{\sum_{j \in \text{Available}} w_j} \quad \forall i \in \text{Available}$$

$$\text{Composite Score} = \sum_{i \in \text{Available}} w'_i \times S_i$$

### Example:
- Default weights: Cost 35%, Quality 25%, Reliability 15%, Lead Time 15%, Payment 10%.
- A new supplier has no reliability track record (\(S_{\text{reliability}}\) is `None`).
- Active sum: \(35 + 25 + 15 + 10 = 85\).
- Renormalized weights:
  - Cost: \(35 / 85 \approx 41.18\%\)
  - Quality: \(25 / 85 \approx 29.41\%\)
  - Lead Time: \(15 / 85 \approx 17.65\%\)
  - Payment: \(10 / 85 \approx 11.76\%\)
- Total weight remains exactly 100%.

---

## 4. Evidence Completeness Index & Provisional Scoring

To protect procurement officers from relying heavily on vendors with sparse documentation, IndusPilot computes an **Evidence Completeness Score** (\(0.0 - 1.0\)):

$$\text{Evidence Completeness} = \dfrac{N_{\text{verified criteria}}}{N_{\text{total criteria}}}$$

When the evidence completeness index falls below **0.70 (70%)**, the candidate is explicitly tagged as:
$$\textbf{[PROVISIONAL — LOW EVIDENCE]}$$

This flags to human approvers that the vendor's score is based on limited historical observations and requires manual verification before high-value purchase order issuance.

---

## 5. Decision Bands & Recommendation Hierarchy

Composite scores map deterministically to 4 actionable decision bands:

| Score Range | Decision Band | Procurement Action |
|---|---|---|
| **85.0 – 100.0** | `STRONGLY_RECOMMENDED` | Direct award or fast-track requisition. Meets all technical, quality, and commercial benchmarks. |
| **70.0 – 84.9** | `VIABLE_ALTERNATIVE` | Secondary backup supplier or counter-negotiation candidate. |
| **50.0 – 69.9** | `HIGH_RISK_CONSIDERATION` | Viable only if primary suppliers have stockouts; requires supervisor approval. |
| **< 50.0** | `NOT_RECOMMENDED` | Rejected due to poor economics, long lead times, or low reliability. |

---

## 6. Audit Trail & Verification

All score calculations and weight renormalizations are verified by unit tests in `backend/tests/test_phase4_supplier_comparison.py`:
- `test_scoring_cheapest_supplier_gets_top_cost_score`: Tests cost curve normalization.
- `test_scoring_missing_data_weight_renormalization`: Verifies mathematical weight rescaling.
- `test_scoring_low_evidence_provisional_tag`: Validates provisional flagging on incomplete vendor profiles.
- `test_decision_explanation_generation`: Confirms natural language rationale generation matches mathematical scores.

