# IndusPilot Negotiation Impact Analysis & Concession Modeling

## 1. Mathematical Formulation of Negotiation Impact

A supplier's unit price concession does not equal the final landed cost saving due to non-linear tax and freight interactions. IndusPilot recalculates landed cost across all 9 deterministic components:

$$\text{Gross Material Cost} = Q \times P_{\text{unit}}$$
$$\text{Discounted Material Cost} = \text{Gross Material Cost} \times (1 - d)$$
$$\text{Assessable Freight Cost} = \text{Freight}_{\text{fixed}} + (\text{Freight}_{\text{per\_unit}} \times Q)$$
$$\text{Loading / Packaging / Insurance Cost} = \text{Packaging} + \text{Transit Insurance} + \text{Loading Charges}$$
$$\text{Net Taxable Base} = \text{Discounted Material Cost} + \text{Freight} + \text{Loading} + \text{Packaging} + \text{Insurance}$$
$$\text{GST Amount} = \text{Net Taxable Base} \times \frac{\text{GST \%}}{100}$$
$$\text{Gross Invoice Total} = \text{Net Taxable Base} + \text{GST Amount}$$
$$\text{Net Landed Cost} = \text{Gross Invoice Total} - \text{Eligible GST Input Tax Credit (ITC)}$$

When a supplier concedes on $P_{\text{unit}}$:
$$\Delta P = P_{\text{original}} - P_{\text{negotiated}}$$
$$\Delta \text{Material Base} = Q \times \Delta P$$
$$\Delta \text{GST Cash Outflow} = \Delta \text{Material Base} \times \frac{\text{GST \%}}{100}$$

Because GST is claimable via ITC for registered manufacturing entities, the net cost reduction reflects the pre-tax base savings:
$$\text{Net Landed Savings} = Q \times \Delta P \times (1 - d)$$
$$\text{Savings \%} = \frac{\text{Original Landed Cost} - \text{Revised Landed Cost}}{\text{Original Landed Cost}} \times 100$$

---

## 2. Supplier Concession Curve Simulation Model

In simulation mode, IndusPilot models realistic industrial concession behavior using a decaying exponential concession curve:

$$P_{\text{round}}(t) = P_{\text{original}} - \kappa(S) \cdot (P_{\text{original}} - P_{\text{target}}) \cdot (1 - e^{-\lambda t})$$

Where:
- $t$: Current negotiation round number ($t \in \{1, 2, 3, 4\}$).
- $P_{\text{original}}$: Opening supplier quoted unit price.
- $P_{\text{target}}$: Buyer target unit price.
- $\kappa(S)$: Supplier flexibility coefficient conditioned on strategy $S$:
  - $\kappa(\text{VOLUME\_COMMITMENT}) = 0.85$ (highest concession rate)
  - $\kappa(\text{BENCHMARK\_PARITY}) = 0.75$
  - $\kappa(\text{PAYMENT\_ACCELERATION}) = 0.70$
  - $\kappa(\text{LONG\_TERM\_CONTRACT}) = 0.80$
  - $\kappa(\text{SPOT\_CLEARANCE}) = 0.65$
- $\lambda$: Convergence speed factor ($\lambda \approx 0.75$).

### Concession Curve Progression (Example: Apex Steel SS304):
- **Opening Quote ($t=0$):** ₹315.00/kg
- **Round 1 Counter ($t=1$):** ₹308.20/kg (₹6.80 concession)
- **Round 2 Counter ($t=2$):** ₹303.40/kg (₹11.60 concession)
- **Round 3 Final Split ($t=3$):** ₹299.80/kg (₹15.20 concession)

---

## 3. Revised Quotation Creation Without Mutation

When `finalize_negotiation_agreement` is executed:
1. The original quotation record (`id=QUOT-001`, `version=1`) remains completely immutable.
2. A new revision record is inserted:
   - `id`: newly generated UUID (`QUOT-001-REV2`)
   - `quotation_number`: `APX-2026-QTN-8821-R1`
   - `version`: `2`
   - `replaces_quotation_id`: `QUOT-001`
   - `status`: `VERIFIED`
   - `unit_price`: negotiated unit price (e.g. ₹303.40)
   - `total_landed_cost`: updated 9-component landed cost
3. The parent quotation status is marked `SUPERSEDED`.
4. Downstream comparison and optimization engines automatically pick the active `version=2` quotation for linear programming allocation!

