# IndusPilot — Bill of Materials (BOM) Management Engine

## Overview & Architecture

In manufacturing fabrication and assembly, a **Bill of Materials (BOM)** is the authoritative engineering blueprint detailing every raw material component, sub-assembly, consumable, scrap allowance, and routing stage required to manufacture a finished industrial product.

IndusPilot implements a deterministic, multi-version BOM management engine tailored for small and medium manufacturing enterprises (SMEs).

---

## 1. Product Structure & Hierarchy

IndusPilot distinguishes between **Finished Products** and **Raw Materials**:
- **Finished Product (`Product`)**: The salable manufactured assembly (e.g. `SS304-BRK-500` — Stainless Steel Industrial Bracket). It specifies the manufacturing process, default batch sizes, production units, and standard lead times.
- **Raw Material (`Material`)**: The raw stock, hardware item, or consumable procured from suppliers (e.g. `MAT-SS-304` — Stainless Steel Sheet, `MAT-FAST-M8` — Fasteners, `MAT-WELD-308L` — TIG Filler Wire).
- **BOM Items (`BOMItem`)**: Connects products to materials with unit quantities, process stages, and scrap allowances.

---

## 2. Scrap Allowance Models: Additive Scrap vs. Yield-Based

Industrial manufacturing processes introduce unavoidable material losses through CNC laser kerf, stamping skeletons, end-clippings, machining chips, and setup trial pieces.

IndusPilot implements two mathematically distinct scrap models using Python `Decimal` (`ROUND_HALF_UP`):

### Model A: Additive Scrap Allowance (`ADDITIVE_SCRAP`)
Common in standard sheet metal cutting, stamping, and shearing where scrap is calculated as a percentage addition to the net part requirement:
$$\text{Gross Required} = \text{Net Required} \times \left(1 + \frac{\text{Wastage \%}}{100}\right)$$

*Example:*
- Net requirement per bracket: $2.0\text{ kg}$
- Additive scrap: $5.0\%$
- Gross requirement per unit: $2.0 \times (1 + 0.05) = 2.10\text{ kg}$
- For a batch of 500 units: $500 \times 2.10 = 1,050.0\text{ kg}$

### Model B: Yield-Based Allowance (`YIELD_BASED`)
Standard in precision casting, chemical processing, powder coating, and foundries where yield represents the fraction of input material surviving as acceptable product:
$$\text{Gross Required} = \frac{\text{Net Required}}{\frac{\text{Yield \%}}{100}}$$

*Example:*
- Net requirement per unit: $2.0\text{ kg}$
- Expected yield: $95.0\%$
- Gross requirement per unit: $\frac{2.0}{0.95} = 2.10526\text{ kg}$
- For a batch of 500 units: $500 \times 2.10526 = 1,052.63\text{ kg}$

IndusPilot calculates both per-component allowances and BOM-level expected yields with zero rounding drift.

---

## 3. BOM Revision Control & Version Comparison

Engineering changes occur frequently due to sheet nesting optimizations, supplier availability, and design tolerances.

1. **Version Immutability**:
   - Released BOMs (`ACTIVE`, `SUPERSEDED`, `ARCHIVED`) are immutable.
   - When engineering makes changes, IndusPilot creates a new revision (e.g., `v1.0` -> `v1.1` or `v2.0`).
   - Activating a new revision automatically marks previous revisions as `SUPERSEDED`, preventing historical production record corruption.
2. **Side-by-Side Revision Comparison**:
   - Computes exact differences across components: `ADDED`, `REMOVED`, `MODIFIED`.
   - Tracks changes in unit quantities, scrap allowances, process stages, and total gross requirements.
3. **Engineering Validation Gate**:
   - Automated checks before activation:
     - No orphan or uncatalogued materials.
     - No duplicate material references in the same BOM.
     - Unit quantities strictly $> 0$.
     - Scrap percentages within reasonable physical bounds ($0\% \le \text{scrap} \le 100\%$).
     - High scrap warning triggered if scrap $> 25\%$.

---

## 4. Multi-Order Aggregation & BOM Explosion

When multiple customer orders or production jobs are scheduled concurrently, IndusPilot aggregates common material requirements across jobs:
1. Explodes each product's active BOM by the planned batch quantity.
2. Applies component-level scrap methods.
3. Sums requirements by `material_id`.
4. Nets against warehouse unreserved stock.
5. Identifies critical shortages and generates consolidated purchase requisitions.

