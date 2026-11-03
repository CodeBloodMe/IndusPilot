import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

from app.services.material_matcher import resolve_grade, extract_thickness, extract_form, GRADE_ALIASES

class EligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    CONDITIONALLY_ELIGIBLE = "CONDITIONALLY_ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


def evaluate_supplier_eligibility(
    requirement: Dict[str, Any],
    quotation: Dict[str, Any],
    supplier: Optional[Dict[str, Any]] = None,
    allow_split_purchasing: bool = False
) -> Dict[str, Any]:
    """
    Deterministic Supplier Eligibility Engine.
    Evaluates material compatibility, quantity & MOQ constraints, delivery feasibility,
    and commercial validity before allowing quotations into the scoring/ranking engine.
    """
    ineligibility_reasons: List[str] = []
    warnings: List[str] = []
    conditions: List[str] = []

    # 0. Quarantine & Quality Gate Exclusion
    is_quarantined = quotation.get("is_quarantined", False) or quotation.get("status") == "QUARANTINED"
    if is_quarantined:
        quarantine_reasons = quotation.get("quarantine_reasons") or ["Quotation is quarantined by Quality Gate."]
        ineligibility_reasons.extend(quarantine_reasons)
        return {
            "status": EligibilityStatus.INELIGIBLE,
            "is_eligible": False,
            "ineligibility_reasons": ineligibility_reasons,
            "warnings": warnings,
            "conditions": conditions,
            "constraint_checks": {
                "quality_gate_passed": False,
                "material_compatible": False,
                "quantity_eligible": False,
                "delivery_eligible": False,
                "commercial_eligible": False
            }
        }

    # Extract target requirement parameters
    req_material_name = (requirement.get("material_name") or requirement.get("name") or "").strip()
    req_grade = (requirement.get("grade") or resolve_grade(req_material_name) or "").strip().upper()
    req_thickness = requirement.get("thickness_mm")
    if req_thickness is None and req_material_name:
        req_thickness = extract_thickness(req_material_name)

    req_quantity = float(requirement.get("quantity") or 0.0)
    req_unit = (requirement.get("unit") or "kg").strip().lower()
    req_deadline_str = requirement.get("delivery_deadline") or requirement.get("required_by_date")
    req_max_lead_time = requirement.get("max_lead_time_days")

    # Locate the matching line item in quotation
    items = quotation.get("items") or []
    if not items:
        ineligibility_reasons.append("Quotation contains zero line items.")
        return {
            "status": EligibilityStatus.INELIGIBLE,
            "is_eligible": False,
            "ineligibility_reasons": ineligibility_reasons,
            "warnings": warnings,
            "conditions": conditions,
            "constraint_checks": {
                "quality_gate_passed": True,
                "material_compatible": False,
                "quantity_eligible": False,
                "delivery_eligible": False,
                "commercial_eligible": False
            }
        }

    # Find candidate line item
    matched_item = None
    for it in items:
        it_name = it.get("material_name_raw") or it.get("material_name") or ""
        it_grade = (it.get("grade") or resolve_grade(it_name) or "").strip().upper()
        it_mat_id = it.get("material_id")
        req_mat_id = requirement.get("material_id")

        if req_mat_id and it_mat_id and req_mat_id == it_mat_id:
            matched_item = it
            break
        elif req_grade and (req_grade in it_grade or it_grade in req_grade):
            matched_item = it
            break

    if not matched_item:
        # Default to first item if no direct match found
        matched_item = items[0]

    # --- 1. Material Compatibility Check ---
    mat_compatible = True
    item_desc = matched_item.get("material_name_raw") or matched_item.get("material_name") or ""
    item_grade = (matched_item.get("grade") or resolve_grade(item_desc) or "").strip().upper()
    item_thickness = matched_item.get("thickness_mm")
    if item_thickness is None and item_desc:
        item_thickness = extract_thickness(item_desc)

    item_unit = (matched_item.get("unit") or quotation.get("unit") or "kg").strip().lower()

    # Grade matching rule: SS304 vs SS316 are NOT interchangeable
    if req_grade and item_grade:
        # Check canonical resolution via resolve_grade regex patterns and alias mapping
        canon_req = resolve_grade(req_grade) or GRADE_ALIASES.get(req_grade.lower(), req_grade)
        canon_item = resolve_grade(item_grade) or resolve_grade(item_desc) or GRADE_ALIASES.get(item_grade.lower(), item_grade)
        if canon_req != canon_item:
            # Check if one is SS304 and other is SS316
            if ("304" in canon_req and "316" in canon_item) or ("316" in canon_req and "304" in canon_item):
                ineligibility_reasons.append(
                    f"Fatal Grade Mismatch: Quoted material is {item_grade} ({canon_item}), but required specification strictly demands {req_grade} ({canon_req}). Grades are non-interchangeable."
                )
                mat_compatible = False
            elif canon_req not in canon_item and canon_item not in canon_req:
                ineligibility_reasons.append(
                    f"Material Grade Mismatch: Quoted {item_grade} does not match required {req_grade}."
                )
                mat_compatible = False

    # Thickness matching rule: e.g. 2.0 mm vs 5.0 mm
    if req_thickness is not None and item_thickness is not None:
        diff = abs(float(req_thickness) - float(item_thickness))
        if diff > 0.5: # Substantial dimensional mismatch
            ineligibility_reasons.append(
                f"Dimensional / Thickness Mismatch: Quoted {item_thickness:.1f} mm plate vs required {req_thickness:.1f} mm (difference of {diff:.1f} mm exceeds tolerance)."
            )
            mat_compatible = False
        elif diff > 0.05: # Minor thickness tolerance
            warnings.append(
                f"Minor thickness variance: Quoted {item_thickness:.2f} mm vs required {req_thickness:.2f} mm."
            )

    # Unit compatibility check
    if req_unit != item_unit:
        # Allow compatible mass units (kg, ton, mt)
        mass_units = {"kg", "ton", "mt", "metric ton"}
        count_units = {"nos", "pcs", "no", "pc"}
        if req_unit in mass_units and item_unit in mass_units:
            warnings.append(f"Unit conversion needed between {item_unit} and {req_unit}.")
        elif req_unit in count_units and item_unit in count_units:
            pass
        else:
            ineligibility_reasons.append(
                f"Incompatible Unit of Measurement: Quoted in '{item_unit}', but procurement specification requires '{req_unit}'."
            )
            mat_compatible = False

    # --- 2. Quantity & Capacity Eligibility Check ---
    qty_eligible = True
    quoted_moq = float(matched_item.get("moq") or quotation.get("moq") or 1.0)
    supplier_capacity = 0.0
    if supplier:
        supplier_capacity = float(supplier.get("capacity_monthly_tons", 0.0) * 1000.0) # convert tons to kg

    # Check MOQ
    if quoted_moq > req_quantity:
        if quoted_moq > req_quantity * 2.0:
            ineligibility_reasons.append(
                f"Minimum Order Quantity Exceeded: Vendor MOQ is {quoted_moq:,.0f} {req_unit}, which is more than double the required {req_quantity:,.0f} {req_unit}."
            )
            qty_eligible = False
        else:
            conditions.append(
                f"MOQ Exceeds Requirement: Vendor MOQ ({quoted_moq:,.0f} {req_unit}) exceeds order volume ({req_quantity:,.0f} {req_unit}). Factory must absorb surplus inventory."
            )

    # Check Supplier Capacity
    if supplier_capacity > 0 and req_quantity > supplier_capacity and not allow_split_purchasing:
        ineligibility_reasons.append(
            f"Insufficient Monthly Capacity: Vendor monthly capacity is {supplier_capacity:,.0f} {req_unit}, which cannot fulfill total demand of {req_quantity:,.0f} {req_unit} without order splitting."
        )
        qty_eligible = False

    # --- 3. Delivery Eligibility Check ---
    delivery_eligible = True
    quoted_lead_time = int(matched_item.get("lead_time_days") or quotation.get("lead_time_days") or 7)

    # If max lead time constraint is given
    if req_max_lead_time is not None:
        if quoted_lead_time > int(req_max_lead_time):
            ineligibility_reasons.append(
                f"Delivery Lead Time Exceeded: Vendor quotes {quoted_lead_time} days, which exceeds the required production deadline threshold of {req_max_lead_time} days."
            )
            delivery_eligible = False

    # If explicit delivery deadline date is given
    if req_deadline_str:
        try:
            if isinstance(req_deadline_str, str):
                deadline_dt = datetime.fromisoformat(req_deadline_str.replace("Z", "+00:00"))
            else:
                deadline_dt = req_deadline_str

            # Compare lead time days against available days until deadline
            now_dt = datetime.utcnow()
            # If naive, make compatible
            if deadline_dt.tzinfo is not None:
                deadline_dt = deadline_dt.replace(tzinfo=None)
            available_days = (deadline_dt - now_dt).days

            if available_days > 0 and quoted_lead_time > available_days:
                ineligibility_reasons.append(
                    f"Production Deadline Failure: Quoted delivery ({quoted_lead_time} days) arrives after required manufacturing deadline (in {available_days} days)."
                )
                delivery_eligible = False
        except Exception:
            pass

    # --- 4. Commercial Eligibility Check ---
    comm_eligible = True

    # Validity date check
    valid_until_str = quotation.get("valid_until")
    if valid_until_str:
        try:
            if isinstance(valid_until_str, str):
                valid_dt = datetime.fromisoformat(valid_until_str.replace("Z", "+00:00"))
            else:
                valid_dt = valid_until_str
            if valid_dt.tzinfo is not None:
                valid_dt = valid_dt.replace(tzinfo=None)

            if valid_dt < datetime.utcnow():
                ineligibility_reasons.append(
                    f"Quotation Expired: Vendor commercial offer expired on {valid_dt.strftime('%d-%b-%Y')}. Updated rate confirmation required."
                )
                comm_eligible = False
        except Exception:
            pass

    # Tax treatment check: UNKNOWN tax must be flagged for review
    tax_treatment = quotation.get("tax_treatment")
    if tax_treatment == "UNKNOWN":
        warnings.append("Tax treatment is UNKNOWN; purchasing officer verification required.")
        conditions.append("Commercial Condition: Clarify GST inclusivity before finalizing Purchase Requisition.")

    # Price positivity
    unit_price = float(matched_item.get("unit_price") or 0.0)
    if unit_price <= 0:
        ineligibility_reasons.append("Quoted unit price is zero or negative.")
        comm_eligible = False

    # --- 5. Determine Overall Classification ---
    if len(ineligibility_reasons) > 0:
        status = EligibilityStatus.INELIGIBLE
        is_eligible = False
    elif len(conditions) > 0:
        status = EligibilityStatus.CONDITIONALLY_ELIGIBLE
        is_eligible = True
    elif len(warnings) > 0 or tax_treatment == "UNKNOWN":
        status = EligibilityStatus.NEEDS_REVIEW
        is_eligible = True
    else:
        status = EligibilityStatus.ELIGIBLE
        is_eligible = True

    return {
        "status": status,
        "is_eligible": is_eligible,
        "ineligibility_reasons": ineligibility_reasons,
        "warnings": warnings,
        "conditions": conditions,
        "matched_item": {
            "material_name": item_desc,
            "grade": item_grade,
            "thickness_mm": item_thickness,
            "unit": item_unit,
            "quoted_unit_price": unit_price,
            "quoted_moq": quoted_moq,
            "lead_time_days": quoted_lead_time
        },
        "constraint_checks": {
            "quality_gate_passed": True,
            "material_compatible": mat_compatible,
            "quantity_eligible": qty_eligible,
            "delivery_eligible": delivery_eligible,
            "commercial_eligible": comm_eligible
        }
    }
