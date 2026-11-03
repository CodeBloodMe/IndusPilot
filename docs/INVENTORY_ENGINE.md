# IndusPilot — Real-Time Inventory & Material Reservation Engine

## 1. Overview & Architecture

Factory inventory is not merely a single "quantity in stock" number. In an active job shop or manufacturing facility, material on hand is constantly undergoing allocation, reservation, physical cutting, and staging.

IndusPilot implements a **Perpetual Inventory Ledger with Moving-Average Cost Valuation** and a strict **Double-Entry Transaction System**.

---

## 2. Inventory Quantity Definitions

For every raw material SKU, IndusPilot tracks three critical quantities:

$$\text{Available Stock} = \text{Current Physical Stock} - \text{Reserved Stock}$$

1. **Current Physical Stock (`current_stock`)**:
   - The verified quantity physically present in warehouse bays, racks, or storage yards.
   - Updated by physical receipts, physical issues to machines, and audit count reconciliations.
2. **Reserved Stock (`reserved_stock`)**:
   - Material promised and locked to planned production jobs (`JOB-2026-XXXX`).
   - Although still physically in the building, it **cannot** be allocated to new jobs or sold.
3. **Available Stock (`available_stock`)**:
   - The unencumbered stock free to be allocated to new manufacturing jobs or customer quotations.
   - **Crucial Rule**: IndusPilot prevents negative available stock by default. An issue or reservation will be rejected if $\text{Quantity} > \text{Available Stock}$.

---

## 3. Transaction Types & Double-Entry Ledger

Every inventory state change is recorded as an immutable `InventoryMovement` row containing:
- `movement_type`: `RECEIPT`, `ISSUE`, `RESERVATION`, `RELEASE`, `ADJUSTMENT`.
- `quantity`: Positive for receipts/reversals, negative for issues.
- `unit_cost`: Transactional cost valuation in INR (₹).
- `source` & `destination`: Storage bays, cutting stations, or job references.
- `idempotency_key`: Prevents duplicate double-posting from network retries or barcode rescans.

### Transaction Workflows:
1. **Receive Stock (`receive_stock`)**:
   - Increases physical stock: $Q_{\text{new}} = Q_{\text{old}} + Q_{\text{in}}$.
   - Recomputes moving-average unit cost:
     $$\bar{C}_{\text{new}} = \frac{(Q_{\text{old}} \times \bar{C}_{\text{old}}) + (Q_{\text{in}} \times C_{\text{in}})}{Q_{\text{old}} + Q_{\text{in}}}$$
2. **Issue Stock (`issue_stock`)**:
   - Decreases physical stock: $Q_{\text{new}} = Q_{\text{old}} - Q_{\text{out}}$.
   - Decreases reserved stock if issued against an existing job reservation.
3. **Reserve Stock (`reserve_stock`)**:
   - Locks material to a production job without physically removing it from the shelf.
   - Increases `reserved_stock`, decreasing `available_stock`.
   - Creates a tracked `StockReservation` with status `ACTIVE`.
4. **Release Reservation (`release_reservation`)**:
   - Unlocks reserved stock if a job is cancelled or rescheduled.
   - Decreases `reserved_stock`, restoring `available_stock`.
5. **Physical Audit Adjustment (`adjust_stock`)**:
   - Reconciles system stock to actual physical count following cycle counts.
   - Records audit adjustment delta and reason note in the movement ledger.

---

## 4. Reorder Levels & Automated Shortage Alerts

IndusPilot continuously monitors inventory thresholds:
- **Safety Stock (`safety_stock`)**: Minimum buffer to absorb unexpected supplier delivery delays or scrap spikes.
- **Reorder Level (`reorder_level`)**: Trigger threshold calculated as:
  $$\text{Reorder Level} = (\text{Daily Consumption Rate} \times \text{Lead Time Days}) + \text{Safety Stock}$$
- **Alert Types**:
  - `CRITICAL_SHORTAGE`: Available stock is $\le 0$ or below safety stock with pending jobs.
  - `REORDER_REQUIRED`: Physical stock is at or below the reorder point.
  - `OVERSTOCK_WARNING`: Stock exceeds 3x typical monthly consumption, locking up operating working capital.

