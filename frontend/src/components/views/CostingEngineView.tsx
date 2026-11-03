"use client";

import React, { useState, useEffect } from "react";
import {
  Calculator,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Percent,
  Sliders,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import { calculateCosting } from "@/lib/api";

export default function CostingEngineView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  const [quantity, setQuantity] = useState<number>(500);
  const [rawUnitCost, setRawUnitCost] = useState<number>(315);
  const [laborHours, setLaborHours] = useState<number>(120);
  const [laborRate, setLaborRate] = useState<number>(180);
  const [machineHours, setMachineHours] = useState<number>(45);
  const [machineRate, setMachineRate] = useState<number>(350);
  const [electricityKwh, setElectricityKwh] = useState<number>(650);
  const [tariff, setTariff] = useState<number>(8.5);
  const [finishingCost, setFinishingCost] = useState<number>(18000);
  const [overheadPct, setOverheadPct] = useState<number>(12);
  const [targetMarginPct, setTargetMarginPct] = useState<number>(25);
  const [customPrice, setCustomPrice] = useState<number>(850);

  const [costResult, setCostResult] = useState<any>(null);
  const [calculating, setCalculating] = useState<boolean>(false);

  useEffect(() => {
    runCostCalculation();
  }, [
    quantity,
    rawUnitCost,
    laborHours,
    laborRate,
    machineHours,
    machineRate,
    electricityKwh,
    tariff,
    finishingCost,
    overheadPct,
    targetMarginPct,
    customPrice,
  ]);

  const runCostCalculation = async () => {
    try {
      setCalculating(true);
      const grossMaterialQty = quantity * 2.1; // 2.0 kg net + 5% scrap
      const res = await calculateCosting({
        production_quantity: quantity,
        material_costs_breakdown: [
          {
            material_name: "Stainless Steel 304 Sheet Plate",
            unit_cost: rawUnitCost,
            gross_quantity: grossMaterialQty,
            net_quantity: quantity * 2.0,
          },
        ],
        direct_labor_hours: laborHours,
        labor_rate_per_hour: laborRate,
        machine_hours: machineHours,
        machine_rate_per_hour: machineRate,
        electricity_kwh: electricityKwh,
        electricity_tariff_per_kwh: tariff,
        secondary_processes_total: finishingCost,
        transportation_total: 6500,
        packaging_total: 4500,
        overhead_pct: overheadPct,
        target_gross_margin_pct: targetMarginPct,
        custom_selling_price_per_unit: customPrice,
      });
      setCostResult(res);
    } catch (err) {
      console.error("Cost calculation error:", err);
    } finally {
      setCalculating(false);
    }
  };

  const ue = costResult?.unit_economics;
  const cb = costResult?.cost_breakdown;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Calculator className="w-5 h-5 text-blue-600" />
            <span>Deterministic 14-Factor Manufacturing Cost Intelligence</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Uses Python Decimal arithmetic to establish exact unit production costs, break-even price,
            and protect against loss-making customer contracts.
          </p>
        </div>

        <button
          onClick={() => setActiveTab("customer-quotes")}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all self-start sm:self-auto"
        >
          <span>Generate Customer Quote</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Loss Making Safeguard Banner */}
      {ue?.is_loss_making && (
        <div className="p-4 rounded-xl bg-red-50 border-2 border-red-300 text-red-900 flex items-start gap-3">
          <ShieldAlert className="w-6 h-6 text-red-600 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-black uppercase tracking-wider text-red-700">
              CRITICAL WARNING: Loss-Making Customer Price Detected!
            </h4>
            <p className="text-xs text-red-700/90 mt-0.5">
              Your test price of <b>₹{ue.effective_unit_price.toFixed(2)}</b> is strictly below the
              break-even production cost of <b>₹{ue.break_even_price.toFixed(2)}</b>.
              Fulfilling this contract will result in a net factory loss of{" "}
              <b>₹{Math.abs(ue.projected_gross_profit).toLocaleString("en-IN")}</b>!
            </p>
          </div>
        </div>
      )}

      {/* Main Grid: Interactive Parameters Left, Financial Breakdown Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Cost Drivers Input Sliders */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
          <div className="border-b border-slate-200 pb-3 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-blue-600" />
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Shop Floor & Operational Assumptions
            </h3>
          </div>

          <div className="space-y-3.5 text-xs">
            <div>
              <div className="flex justify-between text-slate-700 font-semibold mb-1">
                <span>Production Batch Quantity:</span>
                <span className="font-mono text-blue-700 font-bold">{quantity} Units</span>
              </div>
              <input
                type="range"
                min="100"
                max="2000"
                step="50"
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
                className="w-full accent-blue-600"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-700 font-semibold mb-1">
                <span>Raw SS304 Unit Cost (₹/kg):</span>
                <span className="font-mono text-blue-700 font-bold">₹{rawUnitCost}/kg</span>
              </div>
              <input
                type="range"
                min="250"
                max="450"
                step="5"
                value={rawUnitCost}
                onChange={(e) => setRawUnitCost(Number(e.target.value))}
                className="w-full accent-blue-600"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-700 font-semibold mb-1">
                <span>Direct Operator Labor:</span>
                <span className="font-mono text-slate-800">
                  {laborHours} hrs @ ₹{laborRate}/hr
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 mt-1">
                <input
                  type="number"
                  value={laborHours}
                  onChange={(e) => setLaborHours(Number(e.target.value))}
                  className="bg-slate-50 border border-slate-200 rounded px-2.5 py-1 text-xs text-slate-900"
                  placeholder="Hours"
                />
                <input
                  type="number"
                  value={laborRate}
                  onChange={(e) => setLaborRate(Number(e.target.value))}
                  className="bg-slate-50 border border-slate-200 rounded px-2.5 py-1 text-xs text-slate-900"
                  placeholder="Rate ₹/hr"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-slate-700 font-semibold mb-1">
                <span>Machine Center Hours:</span>
                <span className="font-mono text-slate-800">
                  {machineHours} hrs @ ₹{machineRate}/hr
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 mt-1">
                <input
                  type="number"
                  value={machineHours}
                  onChange={(e) => setMachineHours(Number(e.target.value))}
                  className="bg-slate-50 border border-slate-200 rounded px-2.5 py-1 text-xs text-slate-900"
                />
                <input
                  type="number"
                  value={machineRate}
                  onChange={(e) => setMachineRate(Number(e.target.value))}
                  className="bg-slate-50 border border-slate-200 rounded px-2.5 py-1 text-xs text-slate-900"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-slate-700 font-semibold mb-1">
                <span>Factory Overhead Percentage:</span>
                <span className="font-mono text-blue-700 font-bold">{overheadPct}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="25"
                step="1"
                value={overheadPct}
                onChange={(e) => setOverheadPct(Number(e.target.value))}
                className="w-full accent-blue-600"
              />
            </div>

            <div className="pt-2 border-t border-slate-200">
              <div className="flex justify-between text-slate-800 font-bold mb-1">
                <span>Test Selling Price per Bracket:</span>
                <span className="font-mono text-blue-700 font-bold text-sm">₹{customPrice}</span>
              </div>
              <input
                type="range"
                min="500"
                max="1500"
                step="25"
                value={customPrice}
                onChange={(e) => setCustomPrice(Number(e.target.value))}
                className="w-full accent-blue-600"
              />
            </div>
          </div>
        </div>

        {/* Right Column: 14-Factor Results Table & Commercial Unit Economics */}
        <div className="lg:col-span-2 space-y-4">
          {/* Unit Economics Highlight Cards */}
          {ue && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-xs">
                <span className="text-slate-500 block text-[10px] uppercase font-bold">
                  Unit Cost (Break-even)
                </span>
                <span className="text-lg font-black text-slate-900 mt-1 block font-mono">
                  ₹{ue.break_even_price.toFixed(2)}
                </span>
                <span className="text-[10px] text-slate-400 mt-0.5 block">Zero Profit Floor</span>
              </div>

              <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-xs">
                <span className="text-slate-500 block text-[10px] uppercase font-bold">
                  Suggested Price (25% Mgn)
                </span>
                <span className="text-lg font-black text-blue-700 mt-1 block font-mono">
                  ₹{ue.suggested_unit_price.toFixed(2)}
                </span>
                <span className="text-[10px] text-slate-400 mt-0.5 block">Recommended</span>
              </div>

              <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-xs">
                <span className="text-slate-500 block text-[10px] uppercase font-bold">
                  Active Selling Price
                </span>
                <span
                  className={`text-lg font-black mt-1 block font-mono ${
                    ue.is_loss_making ? "text-red-600" : "text-emerald-600"
                  }`}
                >
                  ₹{ue.effective_unit_price.toFixed(2)}
                </span>
                <span className="text-[10px] text-slate-500 mt-0.5 block">
                  Margin: {ue.effective_margin_pct.toFixed(1)}%
                </span>
              </div>

              <div
                className={`p-3.5 rounded-xl border shadow-xs ${
                  ue.is_loss_making
                    ? "bg-red-50 border-red-200 text-red-700"
                    : "bg-emerald-50 border-emerald-200 text-emerald-800"
                }`}
              >
                <span className="text-slate-500 block text-[10px] uppercase font-bold">
                  Projected Gross Profit
                </span>
                <span
                  className={`text-lg font-black mt-1 block font-mono ${
                    ue.is_loss_making ? "text-red-700" : "text-emerald-700"
                  }`}
                >
                  ₹{ue.projected_gross_profit.toLocaleString("en-IN")}
                </span>
                <span className="text-[10px] text-slate-600 mt-0.5 block">
                  Batch Revenue: ₹{ue.total_revenue.toLocaleString("en-IN")}
                </span>
              </div>
            </div>
          )}

          {/* 14 Line Item Cost Audit Table */}
          {cb && (
            <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider border-b border-slate-200 pb-2">
                14-Factor Cost Item Audit (Strict Decimal Precision)
              </h4>

              <div className="space-y-1.5 text-xs divide-y divide-slate-100 font-mono">
                <div className="flex justify-between py-1">
                  <span className="text-slate-600">1. Net Raw Material Sourcing:</span>
                  <span className="text-slate-900 font-bold">₹{cb.net_raw_material_cost?.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-600">2. Scrap & Cutting Loss Allowance:</span>
                  <span className="text-amber-700 font-bold">₹{cb.scrap_wastage_cost?.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-600">3. Direct Shop Operator Labor:</span>
                  <span className="text-slate-900 font-bold">₹{cb.direct_labor_cost?.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-600">4. CNC Machine Center Operating:</span>
                  <span className="text-slate-900 font-bold">₹{cb.machine_operating_cost?.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-600">5. Industrial Electricity Tariffs:</span>
                  <span className="text-slate-900 font-bold">₹{cb.electricity_cost?.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-600">6. Passivation & Surface Treatment:</span>
                  <span className="text-slate-900 font-bold">₹{cb.secondary_processes_cost?.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-600">7. Inbound Transport & Crating:</span>
                  <span className="text-slate-900 font-bold">
                    ₹{(cb.transportation_cost + cb.packaging_cost)?.toLocaleString("en-IN")}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-600">8. Allocated Factory Overheads ({overheadPct}%):</span>
                  <span className="text-slate-900 font-bold">₹{cb.allocated_overhead_cost?.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between py-2.5 text-sm font-bold border-t border-slate-200 bg-slate-50 px-3 rounded-lg">
                  <span className="text-blue-900">TOTAL PRODUCTION COST:</span>
                  <span className="text-blue-950 font-black">
                    ₹{cb.total_production_cost?.toLocaleString("en-IN")}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

