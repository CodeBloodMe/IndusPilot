import re
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

# Standardized aliases for manufacturing materials
GRADE_ALIASES = {
    # Stainless Steel 304
    "ss304": "SS304",
    "ss 304": "SS304",
    "stainless steel 304": "SS304",
    "stainless steel grade 304": "SS304",
    "aisi 304": "SS304",
    "sus 304": "SS304",
    "sus304": "SS304",
    "1.4301": "SS304",
    "x5crni18-10": "SS304",
    
    # Stainless Steel 316 / 316L
    "ss316": "SS316",
    "ss 316": "SS316",
    "ss316l": "SS316",
    "stainless steel 316": "SS316",
    "stainless steel 316l": "SS316",
    "aisi 316": "SS316",
    "1.4401": "SS316",
    "1.4404": "SS316",

    # Mild Steel / Carbon Steel
    "ms": "MS IS2062",
    "mild steel": "MS IS2062",
    "is2062": "MS IS2062",
    "is 2062": "MS IS2062",
    "is2062 e250": "MS IS2062",
    "carbon steel": "MS IS2062",
    "a36": "MS IS2062",
    "structural steel": "MS IS2062",

    # Aluminium 6061
    "al6061": "AL6061",
    "al 6061": "AL6061",
    "al 6061-t6": "AL6061",
    "6061-t6": "AL6061",
    "aluminium 6061": "AL6061",
    "aluminum 6061": "AL6061",

    # Aluminium 5052
    "al5052": "AL5052",
    "al 5052": "AL5052",
    "aluminium 5052": "AL5052",
    "aluminum 5052": "AL5052",

    # Copper & Brass
    "copper": "COPPER C11000",
    "ec grade copper": "COPPER C11000",
    "electrolytic copper": "COPPER C11000",
    "c11000": "COPPER C11000",
    "brass": "BRASS C26000",
    "yellow brass": "BRASS C26000",
    "is 319": "BRASS C26000",
    "c26000": "BRASS C26000",

    # Fasteners & Consumables
    "hex bolt": "SS304 FASTENER",
    "ss 304 hex bolt": "SS304 FASTENER",
    "fasteners": "SS304 FASTENER",
    "argon": "ARGON GAS",
    "argon gas": "ARGON GAS",
    "welding wire": "SS308L WIRE",
    "er308l": "SS308L WIRE"
}

FORMS = ["sheet", "plate", "coil", "bar", "rod", "pipe", "tube", "bolt", "nut", "washer", "wire", "fastener", "flange"]


def extract_thickness(text: str) -> Optional[float]:
    """Extracts thickness in mm, e.g. '2mm', '2.5 mm', '2.0 MM Thk'"""
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm|thk|thickness)', text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def extract_form(text: str) -> Optional[str]:
    """Identifies physical manufacturing form."""
    lowered = text.lower()
    for f in FORMS:
        if re.search(rf'\b{f}s?\b', lowered):
            return f.capitalize()
    return None


def resolve_grade(text: str) -> Optional[str]:
    """Resolves raw text into standardized grade tag."""
    lowered = text.lower().strip()
    for alias, canon in GRADE_ALIASES.items():
        if re.search(rf'\b{re.escape(alias)}\b', lowered):
            return canon
    return None


def match_material_specification(
    query_text: str,
    catalogue_materials: List[Dict[str, Any]],
    declared_grade: Optional[str] = None,
    thickness_mm: Optional[float] = None
) -> Dict[str, Any]:
    """
    Deterministic rule-based material matching engine.
    Matches extracted raw material string from quotation against the factory material catalogue.
    
    Returns ranked candidates, similarity score (0.0 - 1.0), and confidence band.
    """
    cleaned_query = query_text.strip().lower()
    detected_grade = declared_grade or resolve_grade(cleaned_query)
    detected_thickness = thickness_mm or extract_thickness(cleaned_query)
    detected_form = extract_form(cleaned_query)

    candidates = []

    for mat in catalogue_materials:
        score = 0.0
        reasons = []

        mat_name = mat.get("name", "").lower()
        mat_grade = (mat.get("grade") or "").lower()
        mat_code = mat.get("code", "").lower()
        mat_category = (mat.get("category") or "").lower()
        mat_forms = (mat.get("manufacturing_forms") or "").lower()

        # 1. Grade Match (0.45 weight)
        if detected_grade:
            canon_grade = detected_grade.lower()
            if canon_grade in mat_grade or canon_grade in mat_name:
                score += 0.45
                reasons.append(f"Grade match ({detected_grade})")
            elif any(alias in mat_name or alias in mat_grade for alias, canon in GRADE_ALIASES.items() if canon == detected_grade):
                score += 0.40
                reasons.append(f"Grade alias match ({detected_grade})")

        # 2. Material Name Token Overlap (0.30 weight)
        query_tokens = set(re.findall(r'\b[a-zA-Z0-9]+\b', cleaned_query))
        mat_tokens = set(re.findall(r'\b[a-zA-Z0-9]+\b', mat_name + " " + mat_grade))
        overlap = query_tokens.intersection(mat_tokens)
        if overlap:
            overlap_ratio = len(overlap) / max(len(query_tokens), 1)
            token_score = min(0.30, overlap_ratio * 0.30)
            score += token_score
            reasons.append(f"Tokens: {', '.join(list(overlap)[:3])}")

        # 3. Form Match (0.15 weight)
        if detected_form and (detected_form.lower() in mat_name or detected_form.lower() in mat_forms):
            score += 0.15
            reasons.append(f"Form ({detected_form})")

        # 4. SequenceMatcher String Similarity (0.10 weight)
        sim = SequenceMatcher(None, cleaned_query, mat_name).ratio()
        score += sim * 0.10

        # Cap score at 1.0
        score = min(1.0, round(score, 3))

        # Assign confidence band
        if score >= 0.85:
            band = "EXACT"
        elif score >= 0.70:
            band = "HIGH_CONFIDENCE"
        elif score >= 0.45:
            band = "SUGGESTED"
        else:
            band = "UNMATCHED"

        if score >= 0.35:
            candidates.append({
                "material_id": mat.get("id"),
                "code": mat.get("code"),
                "name": mat.get("name"),
                "grade": mat.get("grade"),
                "category": mat.get("category"),
                "standard_unit": mat.get("unit", "kg"),
                "standard_cost": mat.get("standard_cost", 0.0),
                "similarity_score": score,
                "confidence_band": band,
                "match_reason": " • ".join(reasons) if reasons else "String similarity"
            })

    # Sort descending by similarity score
    candidates.sort(key=lambda x: x["similarity_score"], reverse=True)

    best_match = candidates[0] if candidates else None
    auto_matched = bool(best_match and best_match["similarity_score"] >= 0.85)

    return {
        "query_text": query_text,
        "detected_grade": detected_grade,
        "detected_thickness_mm": detected_thickness,
        "detected_form": detected_form,
        "best_match": best_match,
        "candidates": candidates[:5], # Return top 5
        "auto_matched": auto_matched
    }

