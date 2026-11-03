# IndusPilot — Document Processing & Quotation Extraction Pipeline

## 1. Overview & Objectives

In Indian industrial clusters (such as Peenya in Bengaluru, Bhosari in Pune, or Naroda in Ahmedabad), raw material quotations arrive through heterogeneous channels: scanned invoice PDFs, WhatsApp photos of paper printouts, Excel spreadsheets, and CSV price lists.

The **IndusPilot Quotation Document Processing Pipeline** provides a zero-key deterministic ingestion engine capable of extracting commercial terms, tabular line items, and financial totals without requiring external cloud LLM dependencies, while maintaining complete mathematical fidelity and human review auditability.

---

## 2. Ingestion Pipeline Architecture

```
[Raw Document: PDF / XLSX / CSV / PNG / JPG]
                        │
                        ▼
       [Multi-Format Ingestion Adapter]
        ├── PyMuPDF & pdfplumber (PDF)
        ├── openpyxl (Excel XLSX / XLS)
        ├── csv sniffer (CSV Delimited)
        └── PIL Image Heuristic Parser (Scanned Images)
                        │
                        ▼
       [Field & Tabular Extraction Engine]
        ├── Header Regex (Vendor Name, GSTIN, Qtn Ref, Dates)
        ├── Commercial Terms (Credit Terms, General MOQ, Lead Time)
        ├── Financial Terms (GST %, Freight Charges, Subtotal, Total)
        └── Line Item Table Parser (Material, Grade, Thk, Qty, Price)
                        │
                        ▼
      [Deterministic Material Matcher Engine]
        ├── Standardized Grade Alias Resolution
        ├── Form Detection (Sheet, Plate, Coil, Bar, Wire)
        ├── Thickness Extraction (e.g. 2mm, 2.5mm)
        ├── Token Overlap & SequenceMatcher Similarity
        └── Candidate Ranking (EXACT, HIGH_CONFIDENCE, SUGGESTED)
                        │
                        ▼
       [Deterministic Quality Gate Assessment]
        ├── Missing Mandatories Check
        ├── Duplicate Quotation Detection
        ├── Zero / Negative Price Isolation
        └── Financial Arithmetic Discrepancy Verification
                        │
                        ▼
       [Status: READY_FOR_REVIEW | NEEDS_CORRECTION | QUARANTINED]
                        │
                        ▼
       [Side-by-Side Human Review Interface]
        └── Estimator Corrections ──► Persist into DB (VERIFIED)
```

---

## 3. Supported File Formats & Extraction Strategies

### 3.1 Industrial PDF Documents
- **Tooling**: `pymupdf` (fitz) for rapid full-text stream processing + `pdfplumber` for precise table grid extraction.
- **Header Parsing**: Extracts vendor corporate headers, reference numbers (`QTN-xxx`, `Ref No`), issuance dates, and validity spans.
- **Table Detection**: Parses multi-column tables with headers (`Item Description`, `Grade`, `Quantity`, `Unit`, `Rate/Unit`, `Line Total`).

### 3.2 Excel Workbooks (`.xlsx`, `.xls`)
- **Tooling**: `openpyxl` with `data_only=True` to retrieve evaluated cell values and avoid formula corruption.
- **Sheet Processing**: Scans all worksheets, detecting tabular rows containing industrial material keywords (`Steel`, `Sheet`, `Aluminium`, `Copper`, `Brass`, `Fastener`, `Bolt`).

### 3.3 CSV Price Lists
- **Tooling**: Python standard `csv.reader` with dynamic dialect sniffing (`,\t;|`).
- **Sanitization**: Strips whitespace, removes non-numeric currency symbols, and validates decimal precision.

### 3.4 Scanned Images (`.png`, `.jpg`, `.jpeg`, `.tiff`)
- **Tooling**: `PIL` (Pillow) image inspection and heuristic pattern extraction.
- **OCR Confidence**: Evaluates image metadata, resolution, text density, and assigns conservative baseline confidence scores.

---

## 4. Deterministic Material Catalogue Matcher

The matching engine matches raw extracted text against the factory's standard material catalogue:

### 4.1 Grade Alias Dictionary
Standardizes 30+ manufacturing grade aliases into canonical tags:
- `SS304`: `ss304`, `ss 304`, `stainless steel 304`, `aisi 304`, `1.4301`, `sus 304`
- `SS316`: `ss316`, `ss316l`, `aisi 316`, `1.4401`, `1.4404`
- `MS IS2062`: `mild steel`, `is2062`, `is 2062`, `is2062 e250`, `carbon steel`, `a36`
- `AL6061`: `al6061`, `al 6061`, `6061-t6`, `aluminium 6061`
- `COPPER C11000`: `copper`, `ec grade copper`, `etp copper`, `c11000`

### 4.2 Scoring Formula
$$\text{Similarity Score} = 0.45 \cdot S_{\text{grade}} + 0.30 \cdot S_{\text{tokens}} + 0.15 \cdot S_{\text{form}} + 0.10 \cdot S_{\text{seq}}$$

- $S_{\text{grade}}$ ($0.45$): Canonical grade or alias match.
- $S_{\text{tokens}}$ ($0.30$): Token intersection between query and catalogue title.
- $S_{\text{form}}$ ($0.15$): Physical manufacturing form match (`Sheet`, `Plate`, `Bar`, `Pipe`, `Bolt`).
- $S_{\text{seq}}$ ($0.10$): Python `difflib.SequenceMatcher` string similarity ratio.

### 4.3 Confidence Bands
- $\ge 0.85$: **EXACT** (Eligible for automated one-click linking).
- $0.70 - 0.84$: **HIGH_CONFIDENCE** (Pre-selected as top candidate in review UI).
- $0.45 - 0.69$: **SUGGESTED** (Presented in dropdown for estimator selection).
- $< 0.45$: **UNMATCHED** (Requires estimator manual linkage).

---

## 5. Quality Gate Rules

Every extracted document is classified into one of three statuses:

1. **READY_FOR_REVIEW**:
   - Recognized supplier name and quotation number.
   - All extracted line items have unit prices $> 0$.
   - Financial arithmetic matches: $\text{Total} \approx \text{Subtotal} + \text{Tax} + \text{Freight} \pm ₹5.00$.
   - Overall confidence $\ge 70\%$.

2. **NEEDS_CORRECTION**:
   - Potential duplicate quotation number already in database (revision advisory).
   - Missing expiration / validity date or quotation issuance date.
   - Moderate confidence ($40\% \le \text{Confidence} < 70\%$).
   - Minor arithmetic rounding discrepancy.

3. **QUARANTINED**:
   - Missing or unidentifiable supplier organization.
   - Missing quotation reference identifier.
   - Zero extracted line items, or all line items contain ₹0.00 / negative unit prices.
   - Critical OCR confidence failure ($< 40\%$).
   - Negative financial totals.
   - **Isolation Guarantee**: Quarantined quotations are strictly excluded from downstream Google OR-Tools procurement optimization and customer costing estimates until resolved by an estimator.

