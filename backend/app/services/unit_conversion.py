"""
IndusPilot Safe Unit Conversion Engine
Implements deterministic unit conversions using arbitrary-precision Python Decimal.
Strictly guards against arbitrary cross-dimensional conversions unless required physical properties
(such as material density or sheet thickness) are explicitly supplied.
"""

from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional, Dict, Any, Tuple


class UnitDimension(str, Enum):
    MASS = "MASS"
    LENGTH = "LENGTH"
    AREA = "AREA"
    VOLUME = "VOLUME"
    COUNT = "COUNT"
    UNKNOWN = "UNKNOWN"


# Canonical Unit Aliases and their factor relative to base unit of dimension
# Base units:
# MASS: kg
# LENGTH: metre
# AREA: sq_metre
# VOLUME: litre
# COUNT: pcs

MASS_CONVERSIONS: Dict[str, Decimal] = {
    "kg": Decimal("1.0"),
    "kilogram": Decimal("1.0"),
    "kilograms": Decimal("1.0"),
    "gram": Decimal("0.001"),
    "grams": Decimal("0.001"),
    "g": Decimal("0.001"),
    "tonne": Decimal("1000.0"),
    "tonnes": Decimal("1000.0"),
    "metric_tonne": Decimal("1000.0"),
    "mt": Decimal("1000.0"),
    "ton": Decimal("1000.0"),
}

LENGTH_CONVERSIONS: Dict[str, Decimal] = {
    "metre": Decimal("1.0"),
    "metres": Decimal("1.0"),
    "meter": Decimal("1.0"),
    "meters": Decimal("1.0"),
    "m": Decimal("1.0"),
    "cm": Decimal("0.01"),
    "centimetre": Decimal("0.01"),
    "centimeter": Decimal("0.01"),
    "mm": Decimal("0.001"),
    "millimetre": Decimal("0.001"),
    "millimeter": Decimal("0.001"),
}

AREA_CONVERSIONS: Dict[str, Decimal] = {
    "sq_metre": Decimal("1.0"),
    "sq_metres": Decimal("1.0"),
    "sqm": Decimal("1.0"),
    "m2": Decimal("1.0"),
    "sq_cm": Decimal("0.0001"),
    "cm2": Decimal("0.0001"),
    "sq_mm": Decimal("0.000001"),
    "mm2": Decimal("0.000001"),
}

VOLUME_CONVERSIONS: Dict[str, Decimal] = {
    "litre": Decimal("1.0"),
    "litres": Decimal("1.0"),
    "liter": Decimal("1.0"),
    "liters": Decimal("1.0"),
    "l": Decimal("1.0"),
    "ml": Decimal("0.001"),
    "millilitre": Decimal("0.001"),
    "milliliter": Decimal("0.001"),
}

COUNT_CONVERSIONS: Dict[str, Decimal] = {
    "pcs": Decimal("1.0"),
    "pieces": Decimal("1.0"),
    "piece": Decimal("1.0"),
    "units": Decimal("1.0"),
    "unit": Decimal("1.0"),
    "nos": Decimal("1.0"),
    "ea": Decimal("1.0"),
    "each": Decimal("1.0"),
}


def normalize_unit_str(unit: str) -> str:
    """Normalizes unit string: lower-cased, trimmed, symbols standard."""
    if not unit:
        return ""
    u = unit.strip().lower().replace("-", "_").replace(" ", "_")
    if u in ["m²", "sq.m", "sq_m"]:
        return "sq_metre"
    if u in ["cm²", "sq.cm"]:
        return "sq_cm"
    if u in ["mm²", "sq.mm"]:
        return "sq_mm"
    return u


def get_unit_dimension(unit: str) -> UnitDimension:
    """Identifies the physical dimension of a unit."""
    u = normalize_unit_str(unit)
    if u in MASS_CONVERSIONS:
        return UnitDimension.MASS
    if u in LENGTH_CONVERSIONS:
        return UnitDimension.LENGTH
    if u in AREA_CONVERSIONS:
        return UnitDimension.AREA
    if u in VOLUME_CONVERSIONS:
        return UnitDimension.VOLUME
    if u in COUNT_CONVERSIONS:
        return UnitDimension.COUNT
    return UnitDimension.UNKNOWN


def convert_unit(
    quantity: float | int | Decimal | str,
    from_unit: str,
    to_unit: str,
    density_g_cm3: Optional[float | Decimal] = None,
    thickness_mm: Optional[float | Decimal] = None,
) -> Decimal:
    """
    Safely converts a quantity between units using exact Decimal arithmetic.
    
    If converting within the same dimension:
      Calculates via base unit factor.
      
    If converting between Area (e.g. sq_metre) and Mass (e.g. kg):
      Requires both thickness_mm and density_g_cm3.
      Formula:
        Volume (m³) = Area (m²) * (thickness_mm / 1000)
        Mass (kg) = Volume (m³) * (density_g_cm3 * 1000)
        
    If converting between Volume (e.g. litre) and Mass (e.g. kg):
      Requires density_g_cm3.
      Formula:
        Volume (m³) = Litres / 1000
        Mass (kg) = Volume (m³) * (density_g_cm3 * 1000) = Litres * density_g_cm3
    """
    qty = Decimal(str(quantity))
    if qty < 0:
        raise ValueError("Quantity to convert cannot be negative.")

    u_from = normalize_unit_str(from_unit)
    u_to = normalize_unit_str(to_unit)

    if u_from == u_to:
        return qty

    dim_from = get_unit_dimension(u_from)
    dim_to = get_unit_dimension(u_to)

    if dim_from == UnitDimension.UNKNOWN:
        raise ValueError(f"Unrecognized or unsupported source unit: '{from_unit}'")
    if dim_to == UnitDimension.UNKNOWN:
        raise ValueError(f"Unrecognized or unsupported target unit: '{to_unit}'")

    # 1. Intra-dimensional conversions
    if dim_from == dim_to:
        if dim_from == UnitDimension.MASS:
            base_qty = qty * MASS_CONVERSIONS[u_from]
            result = base_qty / MASS_CONVERSIONS[u_to]
            return result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        elif dim_from == UnitDimension.LENGTH:
            base_qty = qty * LENGTH_CONVERSIONS[u_from]
            result = base_qty / LENGTH_CONVERSIONS[u_to]
            return result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        elif dim_from == UnitDimension.AREA:
            base_qty = qty * AREA_CONVERSIONS[u_from]
            result = base_qty / AREA_CONVERSIONS[u_to]
            return result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        elif dim_from == UnitDimension.VOLUME:
            base_qty = qty * VOLUME_CONVERSIONS[u_from]
            result = base_qty / VOLUME_CONVERSIONS[u_to]
            return result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        elif dim_from == UnitDimension.COUNT:
            base_qty = qty * COUNT_CONVERSIONS[u_from]
            result = base_qty / COUNT_CONVERSIONS[u_to]
            return result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    # 2. Inter-dimensional conversions (require physical parameters)
    # Area <-> Mass (e.g. Sheet Metal: sq metres to kg)
    if (dim_from == UnitDimension.AREA and dim_to == UnitDimension.MASS) or (
        dim_from == UnitDimension.MASS and dim_to == UnitDimension.AREA
    ):
        if density_g_cm3 is None or thickness_mm is None:
            raise ValueError(
                f"Cross-dimensional conversion between {dim_from.value} ('{from_unit}') "
                f"and {dim_to.value} ('{to_unit}') requires both 'density_g_cm3' and 'thickness_mm'."
            )
        density = Decimal(str(density_g_cm3))
        thickness = Decimal(str(thickness_mm))
        if density <= 0 or thickness <= 0:
            raise ValueError("Density and thickness must be strictly positive for physical conversion.")

        # Density in kg/m³ = density_g_cm3 * 1000
        # Thickness in m = thickness_mm / 1000
        # Weight per sq metre (kg/m²) = (thickness_mm / 1000) * (density_g_cm3 * 1000) = thickness_mm * density_g_cm3
        kg_per_sqm = thickness * density

        if dim_from == UnitDimension.AREA and dim_to == UnitDimension.MASS:
            # Convert area to sq_metre
            sqm = qty * AREA_CONVERSIONS[u_from]
            kg = sqm * kg_per_sqm
            # Convert kg to target mass unit
            result = kg / MASS_CONVERSIONS[u_to]
            return result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        else:
            # Convert mass to kg
            kg = qty * MASS_CONVERSIONS[u_from]
            sqm = kg / kg_per_sqm
            # Convert sqm to target area unit
            result = sqm / AREA_CONVERSIONS[u_to]
            return result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    # Volume <-> Mass (e.g. Liquid coatings: Litres to kg)
    if (dim_from == UnitDimension.VOLUME and dim_to == UnitDimension.MASS) or (
        dim_from == UnitDimension.MASS and dim_to == UnitDimension.VOLUME
    ):
        if density_g_cm3 is None:
            raise ValueError(
                f"Cross-dimensional conversion between {dim_from.value} ('{from_unit}') "
                f"and {dim_to.value} ('{to_unit}') requires 'density_g_cm3'."
            )
        density = Decimal(str(density_g_cm3))
        if density <= 0:
            raise ValueError("Density must be strictly positive for volume-to-mass conversion.")

        # 1 litre of water (density 1.0 g/cm³) = 1.0 kg
        # Mass (kg) = Litres * density_g_cm3
        if dim_from == UnitDimension.VOLUME and dim_to == UnitDimension.MASS:
            litres = qty * VOLUME_CONVERSIONS[u_from]
            kg = litres * density
            result = kg / MASS_CONVERSIONS[u_to]
            return result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        else:
            kg = qty * MASS_CONVERSIONS[u_from]
            litres = kg / density
            result = litres / VOLUME_CONVERSIONS[u_to]
            return result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    # Any other dimension combination is physically unsupported without extra structural data
    raise ValueError(
        f"Arbitrary conversion between {dim_from.value} ('{from_unit}') and "
        f"{dim_to.value} ('{to_unit}') is not supported."
    )

