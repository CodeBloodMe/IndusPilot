# IndusPilot — Mathematical Specifications & Costing Formulas Reference

This document provides the exhaustive mathematical specifications for all calculations in the IndusPilot Manufacturing Intelligence Engine.

All calculations are implemented in pure Python using `decimal.Decimal` with explicit rounding mode `ROUND_HALF_UP` to prevent floating-point representation anomalies.

---

## 1. Unit Conversion Mathematics

### Standard Linear Conversion
For quantities within the same physical dimension (Mass, Length, Area, Volume, Count):
$$Q_{\text{target}} = Q_{\text{source}} \times \frac{F_{\text{source}}}{F_{\text{target}}}$$

Where $F$ represents the base multiplication factor relative to the SI standard unit.

- **Mass (Base: kg)**:
  - $\text{tonne} = 1000.0\text{ kg}$
  - $\text{gram} = 0.001\text{ kg}$
- **Length (Base: mm)**:
  - $\text{metre} = 1000.0\text{ mm}$
  - $\text{cm} = 10.0\text{ mm}$
- **Area (Base: sq_mm)**:
  - $\text{sq_metre} = 1,000,000.0\text{ sq_mm}$
  - $\text{sq_cm} = 100.0\text{ sq_mm}$
- **Volume (Base: ml)**:
  - $\text{litre} = 1000.0\text{ ml}$

### Physical Cross-Dimensional Conversion
1. **Area to Mass** (e.g. Sheet metal area in $\text{m}^2$ to mass in $\text{kg}$):
   $$\text{Mass (kg)} = \text{Area (sq\_mm)} \times \text{Thickness (mm)} \times \text{Density (g/cm}^3\text{)} \times 10^{-6}$$
2. **Volume to Mass** (e.g. Liquids in litres to $\text{kg}$):
   $$\text{Mass (kg)} = \text{Volume (litres)} \times \text{Specific Gravity}$$

*Unsupported cross-dimensional conversions (e.g. length to mass without density/profile) raise explicit `ValueError`.*

---

## 2. Bill of Materials (BOM) Calculations

### Additive Scrap Method (`ADDITIVE_SCRAP`)
$$\text{Gross Qty per Unit} = \text{Net Qty} \times \left(1 + \frac{\text{Scrap \%}}{100}\right)$$
$$\text{Total Gross Required} = \text{Batch Size} \times \text{Gross Qty per Unit}$$
$$\text{Scrap Mass} = \text{Total Gross Required} - (\text{Batch Size} \times \text{Net Qty})$$

### Yield-Based Method (`YIELD_BASED`)
$$\text{Gross Qty per Unit} = \frac{\text{Net Qty}}{\frac{\text{Yield \%}}{100}}$$
$$\text{Total Gross Required} = \text{Batch Size} \times \text{Gross Qty per Unit}$$
$$\text{Scrap Mass} = \text{Total Gross Required} - (\text{Batch Size} \times \text{Net Qty})$$

### Multi-Order Requirement Aggregation
For $M$ production jobs scheduled concurrently:
$$\text{Total Required Material}_k = \sum_{j=1}^{M} \text{Gross Required}_{j, k}$$

---

## 3. Perpetual Inventory Ledger & Moving-Average Cost

### Moving-Average Unit Cost on Receipt
When receiving quantity $Q_{\text{in}}$ at unit price $C_{\text{in}}$ into existing inventory of quantity $Q_{\text{curr}}$ with existing moving-average cost $C_{\text{curr}}$:
$$\bar{C}_{\text{new}} = \frac{(Q_{\text{curr}} \times C_{\text{curr}}) + (Q_{\text{in}} \times C_{\text{in}})}{Q_{\text{curr}} + Q_{\text{in}}}$$

If current physical stock $Q_{\text{curr}} \le 0$:
$$\bar{C}_{\text{new}} = C_{\text{in}}$$

### Available Stock & Netting
$$\text{Available Stock} = \max(0, \text{Physical Stock} - \text{Reserved Stock})$$
$$\text{Net Shortage} = \max(0, \text{Total Gross Required} - \text{Available Stock})$$
$$\text{Allocatable Reservation} = \min(\text{Available Stock}, \text{Total Gross Required})$$

---

## 4. Deterministic 14-Factor Manufacturing Cost Engine

Let $N$ be the production batch size.

### Factor 1: Direct Raw Materials ($C_{\text{mat}}$)
$$C_{\text{mat}} = \sum_{m \in \text{Materials}} (G_m \times P_m)$$
where $G_m$ is gross required quantity and $P_m$ is unit purchase landed price.

### Factor 2: Recoverable Scrap Credit ($C_{\text{scrap\_credit}}$)
$$C_{\text{scrap\_credit}} = \sum_{m \in \text{Materials}} (\text{Scrap Mass}_m \times \text{Salvage Rate}_m)$$

### Factor 3: Direct Labor ($C_{\text{labor}}$)
$$C_{\text{labor}} = \text{Direct Labor Hours} \times \text{Labor Hourly Rate}$$

### Factor 4: Setup & Changeover ($C_{\text{setup}}$)
$$C_{\text{setup}} = \text{Setup Hours} \times \text{Setup Hourly Rate}$$

### Factor 5: Direct Machine Operating Cost ($C_{\text{mach}}$)
$$C_{\text{mach}} = \text{Machine Operating Hours} \times \text{Machine Hourly Rate}$$

### Factor 6: Consumables & Gases ($C_{\text{cons}}$)
$$C_{\text{cons}} = \text{Consumables Cost (Input or Parametric)}$$

### Factor 7: Tooling Wear & Fixtures ($C_{\text{tool}}$)
$$C_{\text{tool}} = \text{Tooling Amortization Cost}$$

### Factor 8: Electricity & Utilities ($C_{\text{power}}$)
$$C_{\text{power}} = \text{Total Electricity Consumption (kWh)} \times \text{Industrial Tariff (₹/kWh)}$$

### Factor 9: Secondary Subcontracted Processes ($C_{\text{sec}}$)
$$C_{\text{sec}} = \text{Finishing, Heat Treatment, Plating Subcontract Sum}$$

### Factor 10: Quality Control & Testing ($C_{\text{qc}}$)
$$C_{\text{qc}} = \text{Inspection, NDT & Certification Cost}$$

### Factor 11: Packaging & Preservation ($C_{\text{pack}}$)
$$C_{\text{pack}} = \text{Packaging Materials Cost}$$

### Factor 12: Outward Freight & Logistics ($C_{\text{freight}}$)
$$C_{\text{freight}} = \text{Dispatch Freight & Handling}$$

### Prime Cost Definition
$$\text{Prime Cost} = (C_{\text{mat}} - C_{\text{scrap\_credit}}) + C_{\text{labor}} + C_{\text{setup}} + C_{\text{mach}}$$

### Factor 13: Factory Overhead ($C_{\text{fac\_ovh}}$)
Calculated according to the selected allocation method:
- **`PERCENTAGE_PRIME_COST`**:
  $$C_{\text{fac\_ovh}} = \text{Prime Cost} \times \frac{R_{\text{factory}}}{100}$$
- **`PERCENTAGE_DIRECT_LABOR`**:
  $$C_{\text{fac\_ovh}} = (C_{\text{labor}} + C_{\text{setup}}) \times \frac{R_{\text{factory}}}{100}$$
- **`MACHINE_HOURS`**:
  $$C_{\text{fac\_ovh}} = \text{Machine Hours} \times R_{\text{mach\_rate}}$$
- **`FIXED_PER_BATCH`**:
  $$C_{\text{fac\_ovh}} = \text{Fixed Overhead Amount}$$
- **`FIXED_PER_UNIT`**:
  $$C_{\text{fac\_ovh}} = N \times \text{Per Unit Overhead Amount}$$

### Factor 14: Administrative & SG&A Overhead ($C_{\text{admin\_ovh}}$)
$$C_{\text{admin\_ovh}} = \text{Prime Cost} \times \frac{R_{\text{admin}}}{100}$$

---

## 5. Total Cost, Break-Even & Commercial Pricing

### Total Batch Manufacturing Cost ($C_{\text{total}}$)
$$C_{\text{total}} = \text{Prime Cost} + C_{\text{cons}} + C_{\text{tool}} + C_{\text{power}} + C_{\text{sec}} + C_{\text{qc}} + C_{\text{pack}} + C_{\text{freight}} + C_{\text{fac\_ovh}} + C_{\text{admin\_ovh}}$$

### Unit Manufacturing Cost ($C_{\text{unit}}$)
$$C_{\text{unit}} = \frac{C_{\text{total}}}{N}$$

### Break-Even Selling Price ($P_{\text{breakeven}}$)
$$P_{\text{breakeven}} = C_{\text{unit}}$$

### Recommended Selling Price at Target Gross Margin ($M_{\text{target}}\%$)
$$P_{\text{target}} = \frac{C_{\text{unit}}}{1 - \frac{M_{\text{target}}}{100}}$$

### Recommended Selling Price at Target Markup ($K_{\text{target}}\%$)
$$P_{\text{target\_markup}} = C_{\text{unit}} \times \left(1 + \frac{K_{\text{target}}}{100}\right)$$

### Profit & Effective Margin on Actual Quoted Price ($P_{\text{quote}}$)
$$\text{Profit per Unit} = P_{\text{quote}} - C_{\text{unit}}$$
$$\text{Total Batch Profit} = N \times \text{Profit per Unit}$$
$$\text{Effective Gross Margin \%} = \left(\frac{P_{\text{quote}} - C_{\text{unit}}}{P_{\text{quote}}}\right) \times 100$$
$$\text{Effective Markup \%} = \left(\frac{P_{\text{quote}} - C_{\text{unit}}}{C_{\text{unit}}}\right) \times 100$$

### Loss-Making Condition
$$\text{Is Loss Making} = (P_{\text{quote}} < P_{\text{breakeven}})$$

---

## 6. What-If Simulation Variance Formulas

Comparing a Simulated Scenario ($S$) against a Baseline ($B$):

$$\Delta C_{\text{unit}} = C_{\text{unit}, S} - C_{\text{unit}, B}$$
$$\Delta C_{\text{unit}, \%} = \left(\frac{C_{\text{unit}, S} - C_{\text{unit}, B}}{C_{\text{unit}, B}}\right) \times 100$$
$$\Delta C_{\text{batch}} = C_{\text{total}, S} - C_{\text{total}, B}$$
$$\Delta \text{Profit} = \text{Total Profit}_S - \text{Total Profit}_B$$

