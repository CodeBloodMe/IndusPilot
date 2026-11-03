# IndusPilot — Deterministic 14-Factor Manufacturing Cost Engine

## 1. Executive Summary

A critical reason small and medium manufacturing enterprises (SMEs) face financial distress is inaccurate product costing. Many fabricators compute cost simply as **"Material + Labor + 10% Margin"**, completely overlooking:
- Scrap and offcut losses
- Machine setup and changeover times
- Electricity and peak industrial power tariffs
- Tooling wear and consumables (cutting gases, welding wire, powder coatings)
- Secondary subcontracted processes (zinc plating, heat treatment)
- Non-Destructive Testing (NDT) and CMM quality inspections
- Packaging, crating, and outward transit logistics
- Factory and administrative SG&A overhead allocations

IndusPilot eliminates this vulnerability with an **agentic, deterministic 14-factor manufacturing cost engine**. All financial math is executed in pure Python `Decimal` (`ROUND_HALF_UP`) with zero floating-point imprecision.

---

## 2. The 14 Operational Cost Factors

The manufacturing cost structure is systematically divided into **Prime Costs**, **Direct Conversion Costs**, and **Overheads**:

### I. Prime Costs
1. **Direct Raw Material Cost**: Gross material quantity required multiplied by verified supplier landed unit prices.
2. **Less: Recoverable Scrap Credit**: Offcuts, stamping skeletons, and machining turnings can be salvaged to scrap dealers. IndusPilot credits this value back:
   $$\text{Scrap Credit} = \text{Scrap Mass (kg)} \times \text{Salvage Rate (₹/kg)}$$
3. **Direct Labor Cost**: Direct operator running hours multiplied by shopfloor labor rates:
   $$\text{Direct Labor} = \text{Run Hours} \times \text{Labor Hourly Rate}$$
4. **Direct Machine Operating Cost**: CNC laser cutting, press brake, and welding machine hours multiplied by machine hourly operating rates (power, preventive maintenance, gas).
5. **Setup & Changeover Cost**: Tool calibration, CAD program loading, and trial test piece production:
   $$\text{Setup Cost} = \text{Setup Hours} \times \text{Setup Hourly Rate}$$

### II. Secondary Conversion & Direct Operating Costs
6. **Consumables Cost**: Welding wire, shielding gases (argon, CO₂), powder coating pigments, and cutting nozzles.
7. **Tooling & Fixtures Wear**: Amortization of stamping dies, press brake tooling, drill bits, and custom welding jigs.
8. **Electricity & Utility Cost**: Peak industrial tariff multiplied by kilowatt-hour consumption:
   $$\text{Electricity Cost} = \text{Total kWh} \times \text{Industrial Tariff (₹/kWh)}$$
9. **Secondary Processes & Subcontracting**: Heat treatment, stress relieving, electroplating, anodizing, or hot-dip galvanizing.
10. **Quality Control & Testing**: CMM dimensional inspection, ultrasonic weld testing, dye penetrant tests, and mill test certificates.
11. **Packaging & Preservation**: Anti-corrosion VCI paper, wooden export crates, heavy-duty cartons, and pallet strapping.
12. **Outward Freight & Logistics**: Transportation from factory dispatch bay to customer delivery site.

### III. Overheads & Indirect Loading
13. **Factory Overheads**: Plant supervision, factory lease, crane maintenance, and factory insurance.
14. **Administrative & SG&A Overheads**: Engineering office salaries, software licenses, enterprise insurance, and corporate administrative expenses.

---

## 3. Configurable Overhead Allocation Methods

Manufacturing cost accounting requires allocating indirect costs fairly to individual batches. IndusPilot supports five industry-standard allocation methods:

| Method Code | Description | Standard Formula | Best Suited For |
| :--- | :--- | :--- | :--- |
| `PERCENTAGE_PRIME_COST` | Overheads loaded as a percentage of Prime Cost | $\text{Prime Cost} \times \frac{\text{Rate}}{100}$ | Material-intensive fabrication |
| `PERCENTAGE_DIRECT_LABOR` | Overheads loaded as a percentage of Direct Labor | $\text{Direct Labor Cost} \times \frac{\text{Rate}}{100}$ | Labor-intensive assembly shops |
| `MACHINE_HOURS` | Overheads loaded per machine operating hour | $\text{Machine Hours} \times \text{Hourly Machine Rate}$ | Heavy CNC & automated machining |
| `FIXED_PER_BATCH` | Fixed monetary sum assigned per batch run | $\text{Fixed Amount (₹)}$ | Custom one-off prototypes |
| `FIXED_PER_UNIT` | Fixed monetary sum per finished piece | $\text{Batch Size} \times \text{Unit Amount (₹)}$ | High-volume serial production |

---

## 4. Break-Even Analysis & Margin Protection

IndusPilot establishes exact commercial boundaries for customer quotes:

- **Total Manufacturing Cost ($C_{\text{batch}}$)**: Sum of all 14 factors.
- **Unit Manufacturing Cost ($C_{\text{unit}}$)**:
  $$C_{\text{unit}} = \frac{C_{\text{batch}}}{\text{Batch Quantity}}$$
- **Break-Even Selling Price ($P_{\text{breakeven}}$)**:
  $$P_{\text{breakeven}} = C_{\text{unit}}$$
  Selling below this price results in immediate cash operating losses.
- **Target Selling Price Based on Gross Margin ($M_{\text{target}}\%$)**:
  $$P_{\text{target}} = \frac{C_{\text{unit}}}{1 - \frac{M_{\text{target}}}{100}}$$
  *(Note: A true gross margin requires dividing by $1 - M$, not multiplying by $1 + M$, which is markup!)*
- **Equivalent Markup on Cost ($\text{Markup}\%$)**:
  $$\text{Markup}\% = \left(\frac{P_{\text{target}} - C_{\text{unit}}}{C_{\text{unit}}}\right) \times 100$$
- **Loss-Making Contract Interception**: If a proposed customer quote price $P_{\text{quote}} < P_{\text{breakeven}}$, IndusPilot flags the quotation as `LOSS_MAKING`, alerts the executive team, and requires formal management approval before the quote can be dispatched.

---

## 5. What-If Cost Sensitivity Simulation

IndusPilot allows manufacturing estimators to test variations before committing to customer bids:
1. **Raw Material Price Fluctuation**: Simulates impact of supplier price increases or volume negotiation discounts ($\pm 5\%$, $\pm 10\%$, $\pm 20\%$).
2. **Batch Size Economies of Scale**: Spreads fixed setup hours and batch tooling costs over larger volumes (e.g. 100 vs. 500 vs. 2,000 units).
3. **Scrap Reduction (Lean Engineering)**: Simulates the financial benefit of tighter CNC nesting or optimized shearing layouts.
4. **Labor & Energy Inflation**: Tests resilience against wage hikes or industrial electricity tariff increases.

