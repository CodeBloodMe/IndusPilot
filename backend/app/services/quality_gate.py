from typing import Dict, Any, List, Optional

VALID_UNITS = {"kg", "nos", "pcs", "meter", "m", "ton", "mt", "sheet", "set", "liter", "ltr"}


def evaluate_quotation_quality_gate(
    quotation_data: Dict[str, Any],
    existing_quotation_numbers: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Deterministic Quality Gate validation for extracted quotations.
    Protects downstream procurement and costing engines from corrupt, partial, or fraudulent data.
    
    Classifies documents into:
    - READY_FOR_REVIEW: Clean extraction, ready for human sign-off.
    - NEEDS_CORRECTION: Minor ambiguities (e.g. date missing, unverified unit) requiring manual correction.
    - QUARANTINED: Fatal flaws (missing supplier, invalid prices, duplicate quote, zero items) - blocked from procurement recommendations.
    """
    quarantine_reasons: List[str] = []
    warnings: List[str] = []
    missing_fields: List[str] = []

    # 1. Supplier Identification Check
    supplier_name = (quotation_data.get("supplier_name") or "").strip()
    if not supplier_name or supplier_name.lower() in ["unknown", "n/a", "vendor"]:
        quarantine_reasons.append("Missing or unidentifiable supplier organization name.")
        missing_fields.append("supplier_name")

    # 2. Quotation Identifier Check
    quote_number = (quotation_data.get("quotation_number") or "").strip()
    if not quote_number or quote_number.lower() in ["unknown", "n/a", "none"]:
        quarantine_reasons.append("Missing mandatory quotation reference identifier / number.")
        missing_fields.append("quotation_number")
    elif existing_quotation_numbers and quote_number in existing_quotation_numbers:
        warnings.append(f"Potential duplicate/revision: Quotation '{quote_number}' has already been processed.")

    # 3. Currency Check
    currency = quotation_data.get("currency")
    if not currency:
        warnings.append("Currency missing; defaulting to INR (₹).")
        missing_fields.append("currency")

    # 4. Line Items Check
    items = quotation_data.get("items") or []
    if len(items) == 0:
        quarantine_reasons.append("No line items or pricing tables could be extracted from document.")
    else:
        valid_items_count = 0
        for idx, it in enumerate(items, start=1):
            price = it.get("unit_price")
            qty = it.get("quantity")
            unit = (it.get("unit") or "").lower().strip()
            mat_desc = (it.get("material_name") or it.get("material_description") or "").strip()

            if not mat_desc:
                warnings.append(f"Item #{idx}: Description is empty.")

            if price is None or price <= 0:
                quarantine_reasons.append(f"Item #{idx} ({mat_desc or 'Item'}): Invalid or zero unit price (₹{price}).")
            else:
                valid_items_count += 1

            if qty is None or qty <= 0:
                warnings.append(f"Item #{idx}: Quantity is non-positive ({qty}).")

            if unit not in VALID_UNITS and not any(u in unit for u in ["kg", "pc", "no", "ton"]):
                warnings.append(f"Item #{idx}: Non-standard industrial unit '{unit}'. Verify unit of measurement.")

        if valid_items_count == 0:
            quarantine_reasons.append("All line items contain invalid or zero prices.")

    # 5. Financial Arithmetic & Total Consistency Check
    subtotal = quotation_data.get("subtotal") or 0.0
    tax_amt = quotation_data.get("tax_amount") or 0.0
    freight = quotation_data.get("freight_cost") or 0.0
    other = quotation_data.get("other_charges") or 0.0
    total = quotation_data.get("total_amount") or 0.0
    is_tax_inclusive = quotation_data.get("is_tax_inclusive", False)

    if total < 0 or subtotal < 0:
        quarantine_reasons.append("Negative financial totals detected.")

    if total > 0 and subtotal > 0:
        expected_total = subtotal + freight + other if is_tax_inclusive else (subtotal + tax_amt + freight + other)
        discrepancy = abs(total - expected_total)
        if discrepancy > 5.0: # Allow minor rounding variations
            warnings.append(
                f"Arithmetic discrepancy detected: Subtotal (₹{subtotal:,.2f}) + Tax (₹{tax_amt:,.2f}) + "
                f"Freight (₹{freight:,.2f}) does not match quoted total (₹{total:,.2f}). Difference: ₹{discrepancy:,.2f}."
            )

    # 6. Dates Check
    if not quotation_data.get("quotation_date"):
        warnings.append("Quotation issuance date is not specified; defaulted to current timestamp.")
        missing_fields.append("quotation_date")

    if not quotation_data.get("valid_until"):
        warnings.append("Quotation expiration / validity period is unstated; verification required.")
        missing_fields.append("valid_until")

    # 7. Confidence Score Check
    confidence = quotation_data.get("confidence_score", 0.0)
    if confidence < 0.40:
        quarantine_reasons.append(f"Overall OCR / extraction confidence is critically low ({confidence*100:.1f}%).")
    elif confidence < 0.70:
        warnings.append(f"Moderate extraction confidence ({confidence*100:.1f}%). Careful human audit advised.")

    # Determine Final Classification
    if len(quarantine_reasons) > 0:
        quality_status = "QUARANTINED"
        is_quarantined = True
    elif len(warnings) > 0:
        quality_status = "NEEDS_CORRECTION"
        is_quarantined = False
    else:
        quality_status = "READY_FOR_REVIEW"
        is_quarantined = False

    return {
        "status": quality_status,
        "is_quarantined": is_quarantined,
        "quarantine_reasons": quarantine_reasons,
        "validation_warnings": warnings,
        "missing_fields": missing_fields,
        "confidence_score": round(confidence, 2)
    }
