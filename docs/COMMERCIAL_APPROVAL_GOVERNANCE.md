# IndusPilot Commercial Approval Governance & Policy Matrix

## 1. Governance Principles

Industrial manufacturing involves high financial exposure and legally binding commercial contracts. IndusPilot institutes a dual-threshold commercial approval matrix that ensures no automated agent or individual user can unilaterally transmit unapproved supplier commitments or generate loss-making customer quotes.

---

## 2. Dual-Threshold Commercial Governance Matrix

| Domain | Action / Trigger | Authority Tier | Required Approval Role | Governance Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Supplier Negotiation** | Counteroffer draft generation | Tier 1 | Procurement Officer | Mandatory approval before message transmission (`AWAITING_APPROVAL`). |
| **Supplier Negotiation** | Concluding agreement (Total commitment < ₹2,00,000) | Tier 1 | Procurement Officer | Revision quotation (v2) created upon finalization. |
| **Supplier Negotiation** | Concluding agreement (Total commitment $\ge$ ₹2,00,000) | Tier 2 | Procurement Manager / Director | Escalated to executive review (`ESCALATED_TO_HUMAN`). |
| **Customer Quotation** | Healthy margin ($\ge 15.0\%$) | Tier 1 | Commercial Executive | Approved for client transmission. |
| **Customer Quotation** | Low margin ($0\% \le \text{Margin} < 15.0\%$) | Tier 2 | Commercial Manager | Yellow alert; requires review of secondary costs and plant capacity. |
| **Customer Quotation** | Loss-making ($\text{Margin} < 0\%$) | Tier 3 | Managing Director / CFO | Hard blocked; requires formal executive override record. |

---

## 3. Audit Trail & Immutability

Every approval decision is recorded with:
1. `approved_by` (Username / Authorized Role).
2. `approved_at` (UTC timestamp).
3. `reason` (Explicit business justification).
4. `version` (Tracked revision number).

Historical quotation revisions and draft messages are preserved without mutation to provide 100% compliance with ISO 9001 and automotive IATF 16949 audit requirements.

