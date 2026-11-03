# IndusPilot Quotation PDF Generation Specification

## 1. Overview & Tooling

Customer quotations in industrial manufacturing must be delivered as clean, tamper-evident, professional PDF documents. IndusPilot incorporates an automated PDF generator built on ReportLab.

---

## 2. ReportLab Architecture & Document Layout

The generated PDF adheres to industrial standard engineering quote layouts:

```
+-------------------------------------------------------------------------+
| [LOGO / INDUSPILOT HEADER]                          DATE: 2026-10-31    |
| IndusPilot Industrial Precision Technologies        QUOTE NO: CQ-2026-0001|
| GSTIN: 27AABCI1234F1Z8 | Peenya Industrial Area    REV: v1              |
+-------------------------------------------------------------------------+
| ISSUED TO:                                  COMMERCIAL TERMS:           |
| Larsen Heavy Machinery Corp                 Payment: 50% Adv, 50% Disp  |
| L&H Industrial Equipment Division           Delivery: 3 Weeks           |
| orders@larsen.com                           Validity: 30 Days           |
+-------------------------------------------------------------------------+
| # | ITEM DESCRIPTION       | CODE    | QTY | UNIT RATE | AMOUNT (Rs.)   |
| 1 | Industrial Bracket SS304| IND-PRD | 500 | Rs. 850.00| Rs. 4,25,000.00|
+-------------------------------------------------------------------------+
|                                             SUBTOTAL:    Rs. 4,25,000.00|
|                                             GST (18%):   Rs.   76,500.00|
|                                             GRAND TOTAL: Rs. 5,01,500.00|
+-------------------------------------------------------------------------+
| NOTES & CONDITIONS:                                                     |
| 1. Inspection certificate provided as per EN 10204 3.1.                 |
| 2. Rates valid for 30 calendar days from issue date.                    |
|                                             AUTHORIZED SIGNATORY:       |
|                                             Commercial Director         |
+-------------------------------------------------------------------------+
```

---

## 3. Font Handling & The Indian Rupee Glyph Safeguard

### Critical Production Fix:
Standard PDF core fonts (`Helvetica`, `Helvetica-Bold`, `Times-Roman`, `Courier`) do not include the Unicode Indian Rupee symbol `₹` (`\u20b9`). In standard ReportLab setups without embedded TTF fonts, printing `\u20b9` causes rendering crashes (`UnicodeEncodeError: 'latin-1' codec can't encode character '\u20b9'`).

IndusPilot strictly enforces:
- **`Rs.` Glyph Protocol:** All monetary formatting utilities utilize `Rs.` (e.g. `Rs. 4,25,000.00`) instead of raw Unicode `₹`.
- **Indian Number Formatting:** Numbers are formatted with Indian commas (thousands, lakhs, crores) using deterministic formatting routines.

---

## 4. PDF Storage & Endpoint Streaming

1. **Storage Path:** Generated PDFs are persisted in `backend/data/uploads/customer_quotes/` as `Customer_Quote_CQ-2026-XXXX.pdf`.
2. **Streaming Endpoint:** Available at both `/api/v1/customer-quotes/{quote_id}/pdf` and `/api/v1/customer-quotes/{quote_id}/download-pdf`.
3. **MIME Type:** `application/pdf` with `Content-Disposition: inline; filename="..."` allowing both in-browser preview and direct download.

