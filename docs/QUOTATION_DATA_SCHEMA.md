# IndusPilot — Quotation Data & Audit Schema Specification

## 1. Overview & Immutability Philosophy

In commercial industrial manufacturing, preserving an unalterable audit trail between what a vendor originally quoted and what the human estimator subsequently confirmed is essential for dispute resolution, ISO 9001 compliance, and training AI models.

IndusPilot implements a **Dual-Snapshot Architecture**:
- **`original_extracted_json`**: Immutable machine extraction payload captured directly by the document parsing engine.
- **`user_corrected_json`**: Final verified state with estimator overrides, catalogue bindings, and notes.

---

## 2. Document Processing Schema (`UploadedDocument`)

Database Table: `uploaded_documents`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR | Primary Key, UUID | Unique document identifier |
| `organization_id` | VARCHAR | FK `organisations.id` | Multi-tenant organizational partition |
| `supplier_id` | VARCHAR | FK `suppliers.id`, Nullable | Linked supplier if recognized |
| `filename` | VARCHAR(255) | Not Null | Sanitized original filename |
| `file_path` | VARCHAR(512) | Not Null | Secure path inside `data/uploads/` |
| `file_type` | VARCHAR(50) | Not Null | `PDF`, `XLSX`, `CSV`, `PNG`, `JPG` |
| `file_size` | INTEGER | Not Null | File size in bytes |
| `processing_status` | VARCHAR(50) | Default: `PENDING` | `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` |
| `validation_status` | VARCHAR(50) | Default: `PENDING` | `READY_FOR_REVIEW`, `NEEDS_CORRECTION`, `QUARANTINED`, `VERIFIED` |
| `confidence_score` | FLOAT | Default: `0.0` | Overall extraction confidence (0.0 to 1.0) |
| `error_message` | TEXT | Nullable | Parser error details if extraction failed |
| `extraction_result_json` | JSON | Nullable | Full raw machine extraction snapshot |
| `raw_text` | TEXT | Nullable | Extracted raw text preview |
| `created_at` | DATETIME | Default: `UTC Now` | Ingestion timestamp |

---

## 3. Verified Supplier Quotation Schema (`SupplierQuotation`)

Database Table: `supplier_quotations`

| Column | Type | Description |
|---|---|---|
| `id` | VARCHAR | Primary Key, UUID |
| `organization_id` | VARCHAR | Organization FK |
| `document_id` | VARCHAR | Linked uploaded document FK (if ingested from file) |
| `supplier_id` | VARCHAR | Supplier FK |
| `quotation_number` | VARCHAR(100) | Commercial quotation reference code |
| `quotation_date` | DATETIME | Quotation issuance date |
| `valid_until` | DATETIME | Expiration timestamp |
| `subtotal` | FLOAT | Base materials subtotal before tax and freight |
| `tax_amount` | FLOAT | Calculated GST amount |
| `tax_pct` | FLOAT | GST percentage (e.g. 18.0) |
| `freight_cost` | FLOAT | Quoted transportation charges |
| `other_charges` | FLOAT | Packaging, insurance, cutting, or test certificate charges |
| `is_tax_inclusive` | BOOLEAN | Whether quoted unit prices already include GST |
| `total_amount` | FLOAT | Total landed invoice payable amount |
| `currency` | VARCHAR(10) | Standard currency code (`INR`) |
| `status` | VARCHAR(50) | `DRAFT`, `READY_FOR_REVIEW`, `NEEDS_CORRECTION`, `VERIFIED`, `QUARANTINED`, `ARCHIVED` |
| `review_notes` | TEXT | Auditor notes and remarks |
| `original_extracted_json` | JSON | Raw machine extraction snapshot |
| `user_corrected_json` | JSON | Post-human review snapshot |
| `verified_at` | DATETIME | Verification timestamp |
| `verified_by` | VARCHAR(100) | User identifier who signed off |

---

## 4. Line Item Schema (`QuotationItem`)

Database Table: `quotation_items`

| Column | Type | Description |
|---|---|---|
| `id` | VARCHAR | Primary Key, UUID |
| `quotation_id` | VARCHAR | FK `supplier_quotations.id` |
| `material_id` | VARCHAR | FK `materials.id` (Linked catalogue material) |
| `material_name_raw` | VARCHAR(255) | Raw description as printed on quotation |
| `grade` | VARCHAR(100) | Extracted/declared material grade (e.g. `SS304 2B`) |
| `thickness_mm` | FLOAT | Extracted sheet/plate thickness in mm |
| `dimensions` | VARCHAR(100) | Dimensional tolerances (e.g. `1250 x 2500 mm`) |
| `quantity` | FLOAT | Quoted purchase volume |
| `unit` | VARCHAR(50) | Standard unit (`kg`, `nos`, `ton`, `meter`, `sqm`) |
| `unit_price` | FLOAT | Unit price before tax |
| `moq` | FLOAT | Minimum order quantity for this item |
| `lead_time_days` | INTEGER | Item fulfillment timeline |
| `line_total` | FLOAT | Arithmetic line total ($\text{Quantity} \times \text{Unit Price}$) |
| `tax_pct` | FLOAT | Applicable GST rate |
| `match_confidence` | FLOAT | AI catalogue match similarity score (0.0 to 1.0) |
| `is_quarantined` | BOOLEAN | Flagged if pricing or specification is invalid |
| `quarantine_reason` | VARCHAR(255) | Diagnostic explanation for quarantine |

---

## 5. Machine Extraction JSON Payload Example

```json
{
  "success": true,
  "filename": "apex_steel_quotation_ss304.pdf",
  "confidence_score": 0.96,
  "field_confidences": {
    "supplier_name": 0.98,
    "quotation_number": 0.95,
    "line_items": 0.95,
    "tax_pct": 0.95,
    "freight_cost": 0.95,
    "payment_terms": 0.90
  },
  "validation_status": "READY_FOR_REVIEW",
  "supplier_name": "Apex Steel & Alloys Pvt Ltd",
  "quotation_number": "APX-2026-QTN-8821",
  "quotation_date": "2026-10-30",
  "valid_until": "2026-11-29",
  "subtotal": 252000.00,
  "tax_pct": 18.0,
  "tax_amount": 45360.00,
  "is_tax_inclusive": false,
  "freight_cost": 4500.00,
  "other_charges": 0.00,
  "total_amount": 301860.00,
  "currency": "INR",
  "payment_terms": "30 Days Net Credit",
  "items": [
    {
      "material_name": "Stainless Steel 304 Sheet Plate (2B Finish)",
      "grade": "SS304",
      "thickness_mm": 2.0,
      "quantity": 800.0,
      "unit": "kg",
      "unit_price": 315.00,
      "moq": 200.0,
      "lead_time_days": 6,
      "line_total": 252000.00,
      "match_confidence": 0.95,
      "auto_matched": true,
      "material_id": "MAT-SS-304",
      "suggested_candidates": [
        {
          "material_id": "MAT-SS-304",
          "code": "MAT-SS-304",
          "name": "Stainless Steel 304 Sheet Plate",
          "similarity_score": 0.95,
          "confidence_band": "EXACT"
        }
      ],
      "is_quarantined": false,
      "quarantine_reason": null
    }
  ]
}
```

