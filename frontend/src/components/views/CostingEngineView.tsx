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
  GitBranch,
  Layers,
  Save,
  RotateCcw,
  Sparkles,
  Info
} from "lucide-react";
import {
  calculateCosting,
  getProductsDetailed,
  getBOMs,
  estimateAndPersistCost,
  simulateWhatIfCost,
  saveCostingScenario
} from "@/lib/api";

export default function CostingEngineView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  // Product & Batch selection
  const [products, setProducts] = useState<any[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [quantity, setQuantity] = useState<number>(500);

  // 14-Factor Cost Inputs
  const [rawUnitCost, setRawUnitCost] = useState<number>(315);
  const [grossMaterialQty, setGrossMaterialQty] = useState<number>(1050);
  const [scrapRecoveryRate, setScrapRecoveryRate] = useState<number>(45); // ₹45/kg scrap credit
  const [laborHours, setLaborHours] = useState<number>(120);
  const [laborRate, setLaborRate] = useState<number>(180);
  const [setupHours, setSetupHours] = useState<number>(4);
  const [machineHours, setMachineHours] = useState<number>(45);
  const [machineRate, setMachineRate] = useState<number>(350);
  const [electricityKwh, setElectricityKwh] = useState<number>(650);
  const [tariff, setTariff] = useState<number>(8.5);
  const [consumablesCost, setConsumablesCost] = useState<number>(12500);
  const [toolingCost, setToolingCost] = useState<number>(4500);
  const [finishingCost, setFinishingCost] = useState<number>(18000);
  const [testingCost, setTestingCost] = useState<number>(3500);
  const [packagingCost, setPackagingCost] = useState<number>(4500);
  const [freightOutward, setFreightOutward] = useState<number>(6500);
  const [overheadMethod, setOverheadMethod] = useState<
    "PERCENTAGE_PRIME_COST" | "PERCENTAGE_DIRECT_LABOR" | "MACHINE_HOURS" | "FIXED_PER_BATCH" | "FIXED_PER_UNIT"
  >("PERCENTAGE_PRIME_COST");
  const [factoryOverheadRate, setFactoryOverheadRate] = useState<number>(12); // 12% prime cost
  const [adminOverheadRate, setAdminOverheadRate] = useState<number>(6); // 6%

  // Pricing & Profitability
  const [targetMarginPct, setTargetMarginPct] = useState<number>(25);
  const [customPrice, setCustomPrice] = useState<number>(850);

  // Calculation Results
  const [costResult, setCostResult] = useState<any>(null);
  const [calculating, setCalculating] = useState<boolean>(false);

  // What-If Simulation State
  const [simMode, setSimMode] = useState<boolean>(false);
  const [materialDeltaPct, setMaterialDeltaPct] = useState<number>(-5); // -5% material price via negotiation
  const [simBatchSize, setSimBatchSize] = useState<number>(500);
  const [laborRateDeltaPct, setLaborRateDeltaPct] = useState<number>(0);
  const [scrapReductionPct, setScrapReductionPct] = useState<number>(15); // 15% scrap reduction
  const [simResult, setSimResult] = useState<any>(null);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [savedScenarioSuccess, setSavedScenarioSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    runCostCalculation();
  }, [
    quantity,
    rawUnitCost,
    grossMaterialQty,
    scrapRecoveryRate,
    laborHours,
    laborRate,
    setupHours,
    machineHours,
    machineRate,
    electricityKwh,
    tariff,
    consumablesCost,
    toolingCost,
    finishingCost,
    testingCost,
    packagingCost,
    freightOutward,
    overheadMethod,
    factoryOverheadRate,
    adminOverheadRate,
    targetMarginPct,
    customPrice
  ]);

  const loadProducts = async () => {
    try {
      const data = await getProductsDetailed();
      setProducts(data);
      if (data && data.length > 0) {
        setSelectedProductId(data[0].id);
      }
    } catch (err) {
      console.error("Failed to load products:", err);
    }
  };

  const handleProductChange = (prodId: string) => {
    setSelectedProductId(prodId);
    const prod = products.find((p) => p.id === prodId);
    if (prod && prod.default_batch_size) {
      setQuantity(prod.default_batch_size);
      setGrossMaterialQty(prod.default_batch_size * 2.1);
    }
  };

  const runCostCalculation = async () => {
    try {
      setCalculating(true);
      const res = await calculateCosting({
        production_quantity: quantity,
        material_costs_breakdown: [
          {
            material_name: "Stainless Steel 304 Sheet Plate",
            unit_cost: rawUnitCost,
            gross_quantity: grossMaterialQty,
            net_quantity: quantity * 2.0,
            scrap_rate: 5.0,
            recoverable_scrap_value: scrapRecoveryRate
          }
        ],
        direct_labor_hours: laborHours,
        labor_rate_per_hour: laborRate,
        machine_hours: machineHours,
        machine_rate_per_hour: machineRate,
        setup_hours: setupHours,
        setup_hourly_rate: laborRate,
        consumables_cost: consumablesCost,
        tooling_cost: toolingCost,
        electricity_kwh: electricityKwh,
        electricity_tariff_per_kwh: tariff,
        secondary_processes_total: finishingCost,
        testing_inspection_cost: testingCost,
        packaging_total: packagingCost,
        transportation_total: freightOutward,
        overhead_pct: factoryOverheadRate,
        admin_overhead_rate: adminOverheadRate,
        overhead_allocation_method: overheadMethod,
        target_gross_margin_pct: targetMarginPct,
        custom_selling_price_per_unit: customPrice
      });
      setCostResult(res);
      if (simMode) {
        triggerSimulation(res);
      }
    } catch (err) {
      console.error("Cost calculation error:", err);
    } finally {
      setCalculating(false);
    }
  };

  const triggerSimulation = async (baseline: any) => {
    try {
      setSimulating(true);
      const sim = await simulateWhatIfCost({
        baseline_estimate: baseline,
        variations: {
          material_price_delta_pct: materialDeltaPct,
          batch_size: simBatchSize,
          labor_rate_delta_pct: laborRateDeltaPct,
          scrap_reduction_pct: scrapReductionPct
        }
      });
      setSimResult(sim);
    } catch (err) {
      console.error("Simulation error:", err);
    } finally {
      setSimulating(false);
    }
  };

  const handleSaveScenario = async () => {
    if (!simResult) return;
    try {
      await saveCostingScenario({
        name: `Scenario: Mat Delta ${materialDeltaPct}%, Scrap -${scrapReductionPct}%`,
        description: `What-If scenario on ${quantity} units bracket manufacturing.`,
        parameters_json: { materialDeltaPct, simBatchSize, scrapReductionPct },
        results_json: simResult
      });
      setSavedScenarioSuccess("Scenario snapshot saved successfully!");
      setTimeout(() => setSavedScenarioSuccess(null), 4000);
    } catch (err) {
      console.error("Failed to save scenario:", err);
    }
  };

  const ue = costResult?.unit_economics;
  const cb = costResult?.cost_breakdown;
  const isLossMaking = ue?.is_loss_making;

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
            Python Decimal arithmetic establishing exact prime costs, break-even price, and target gross margin protection.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setSimMode(!simMode);
              if (!simMode && costResult) {
                triggerSimulation(costResult);
              }
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-xs border ${
              simMode
                ? "bg-purple-600 text-white border-purple-600"
                : "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100"
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span>{simMode ? "Exit Simulation Mode" : "What-If Cost Simulation"}</span>
          </button>

          <button
            onClick={() => setActiveTab("quotation")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 transition-all shadow-xs"
          >
            <span>Generate Customer Quote</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Product Selection & Batch Bar */}
      <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div>
          <label className="block font-bold text-slate-700 uppercase text-[10px] mb-1">
            Manufactured Product
          </label>
          <select
            value={selectedProductId}
            onChange={(e) => handleProductChange(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold text-slate-900"
          >
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code} — {p.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block font-bold text-slate-700 uppercase text-[10px] mb-1">
            Production Batch Quantity
          </label>
          <div className="flex items-center gap-1.5">
            {[100, 250, 500, 1000].map((qty) => (
              <button
                key={qty}
                onClick={() => {
                  setQuantity(qty);
                  setGrossMaterialQty(qty * 2.1);
                  setSimBatchSize(qty);
                }}
                className={`flex-1 py-1.5 rounded-lg font-bold border transition-all ${
                  quantity === qty
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                }`}
              >
                {qty}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block font-bold text-slate-700 uppercase text-[10px] mb-1">
            Overhead Allocation Method
          </label>
          <select
            value={overheadMethod}
            onChange={(e) => setOverheadMethod(e.target.value as any)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold text-slate-900"
          >
            <option value="PERCENTAGE_PRIME_COST">Percentage of Prime Cost (12%)</option>
            <option value="PERCENTAGE_DIRECT_LABOR">Percentage of Direct Labor (45%)</option>
            <option value="MACHINE_HOURS">Machine Hour Rate (₹120/hr)</option>
            <option value="FIXED_PER_BATCH">Fixed Batch Allocation (₹15,000)</option>
            <option value="FIXED_PER_UNIT">Fixed Unit Allocation (₹30/unit)</option>
          </select>
        </div>
      </div>

      {/* Loss Making Alert Banner (if applicable) */}
      {isLossMaking && (
        <div className="p-4 rounded-xl bg-red-50 border-2 border-red-300 flex items-center justify-between text-xs text-red-900 shadow-xs">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-6 h-6 text-red-600 shrink-0" />
            <div>
              <span className="font-bold text-sm block">
                CRITICAL WARNING: Loss-Making Customer Contract Detected
              </span>
              <span>
                Your quoted price of ₹{customPrice.toFixed(2)}/unit is lower than the calculated break-even production cost of ₹
                {ue?.break_even_price?.toFixed(2)}/unit. Margin shortfall: ₹
                {Math.abs(ue?.profit_per_unit || 0).toFixed(2)} per unit (Batch Net Loss: ₹
                {Math.abs(ue?.total_profit || 0).toFixed(2)}).
              </span>
            </div>
          </div>
          <button
            onClick={() => setCustomPrice(Math.ceil(ue?.recommended_selling_price || 850))}
            className="px-3 py-1.5 bg-red-600 text-white font-bold rounded-lg hover:bg-red-700 shrink-0 shadow-xs"
          >
            Apply Target Price (₹{Math.ceil(ue?.recommended_selling_price || 850)})
          </button>
        </div>
      )}

      {/* Top Level Financial KPIs */}
      {ue && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">
              Total Manufacturing Cost (Batch)
            </span>
            <span className="text-xl font-black text-slate-900 mt-1 block font-mono">
              ₹{(cb?.total_production_cost ?? costResult?.total_manufacturing_cost ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </span>
            <span className="text-[10px] text-slate-500 mt-0.5 block">
              Direct Prime Cost: ₹{(cb?.direct_prime_cost ?? cb?.prime_cost ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">
              Break-Even Selling Price
            </span>
            <span className="text-xl font-black text-slate-900 mt-1 block font-mono">
              ₹{ue.break_even_price?.toFixed(2)} / unit
            </span>
            <span className="text-[10px] text-slate-500 mt-0.5 block">
              Unit Production Cost (0% Gross Margin)
            </span>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">
              Target Price ({targetMarginPct}% Margin)
            </span>
            <span className="text-xl font-black text-emerald-700 mt-1 block font-mono">
              ₹{(ue.suggested_unit_price ?? ue.recommended_selling_price ?? 0).toFixed(2)} / unit
            </span>
            <span className="text-[10px] text-slate-500 mt-0.5 block">
              Markup: {(ue.markup_pct ?? ue.recommended_markup_pct ?? 0).toFixed(1)}% on cost
            </span>
          </div>

          <div
            className={`p-4 rounded-xl border shadow-xs ${
              isLossMaking ? "bg-red-50 border-red-200" : "bg-emerald-50 border-emerald-200"
            }`}
          >
            <span className="text-slate-500 block text-[10px] uppercase font-bold">
              Actual Quoted Margin
            </span>
            <span
              className={`text-xl font-black mt-1 block font-mono ${
                isLossMaking ? "text-red-700" : "text-emerald-700"
              }`}
            >
              {(ue.effective_margin_pct ?? ue.effective_gross_margin_pct ?? 0).toFixed(2)}%
            </span>
            <span className="text-[10px] text-slate-600 mt-0.5 block">
              Net Profit: ₹{(ue.projected_gross_profit ?? ue.total_profit ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>
      )}

      {/* WHAT-IF SIMULATION PANEL (If Activated) */}
      {simMode && simResult && (
        <div className="p-5 bg-purple-50/50 border border-purple-200 rounded-xl space-y-4 text-xs shadow-xs">
          <div className="flex items-center justify-between border-b border-purple-200 pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-600" />
              <div>
                <h3 className="font-bold text-sm text-purple-950">
                  What-If Cost Sensitivity Simulation
                </h3>
                <p className="text-[11px] text-purple-700">
                  Simulate material price reductions via negotiation, batch scaling, and scrap minimization.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleSaveScenario}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-600 text-white font-bold hover:bg-purple-700 shadow-xs"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Scenario Snapshot</span>
              </button>
            </div>
          </div>

          {savedScenarioSuccess && (
            <div className="p-2.5 bg-emerald-100 border border-emerald-300 text-emerald-800 rounded-lg font-bold flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>{savedScenarioSuccess}</span>
            </div>
          )}

          {/* Simulation Sliders */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-white rounded-lg border border-purple-100">
            <div>
              <div className="flex justify-between font-bold text-slate-700 mb-1">
                <span>Material Price Change</span>
                <span className="font-mono text-purple-700">{materialDeltaPct}%</span>
              </div>
              <input
                type="range"
                min="-20"
                max="20"
                step="1"
                value={materialDeltaPct}
                onChange={(e) => {
                  setMaterialDeltaPct(parseInt(e.target.value));
                  if (costResult) triggerSimulation(costResult);
                }}
                className="w-full accent-purple-600"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>-20% (Negotiation)</span>
                <span>+20% (Inflation)</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between font-bold text-slate-700 mb-1">
                <span>Scrap Loss Reduction</span>
                <span className="font-mono text-purple-700">-{scrapReductionPct}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="50"
                step="5"
                value={scrapReductionPct}
                onChange={(e) => {
                  setScrapReductionPct(parseInt(e.target.value));
                  if (costResult) triggerSimulation(costResult);
                }}
                className="w-full accent-purple-600"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>0% (Status Quo)</span>
                <span>-50% (Lean tooling)</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between font-bold text-slate-700 mb-1">
                <span>Simulated Batch Size</span>
                <span className="font-mono text-purple-700">{simBatchSize} units</span>
              </div>
              <input
                type="range"
                min="100"
                max="2000"
                step="100"
                value={simBatchSize}
                onChange={(e) => {
                  setSimBatchSize(parseInt(e.target.value));
                  if (costResult) triggerSimulation(costResult);
                }}
                className="w-full accent-purple-600"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>100 units</span>
                <span>2000 units</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between font-bold text-slate-700 mb-1">
                <span>Labor Rate Delta</span>
                <span className="font-mono text-purple-700">{laborRateDeltaPct}%</span>
              </div>
              <input
                type="range"
                min="-15"
                max="25"
                step="5"
                value={laborRateDeltaPct}
                onChange={(e) => {
                  setLaborRateDeltaPct(parseInt(e.target.value));
                  if (costResult) triggerSimulation(costResult);
                }}
                className="w-full accent-purple-600"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>-15%</span>
                <span>+25%</span>
              </div>
            </div>
          </div>

          {/* Side-by-Side Comparison: Baseline vs Scenario */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-white border border-slate-200 rounded-lg space-y-2">
              <span className="font-bold text-slate-500 uppercase text-[10px] block">
                Current Baseline ({quantity} units)
              </span>
              <div className="text-base font-black text-slate-900 font-mono">
                ₹{simResult.baseline.unit_economics.break_even_price?.toFixed(2)} / unit
              </div>
              <div className="text-[11px] text-slate-600">
                Total Batch Cost: ₹{simResult.baseline.total_manufacturing_cost?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
              <div className="text-[11px] text-slate-600">
                Target Selling Price: ₹{simResult.baseline.unit_economics.recommended_selling_price?.toFixed(2)}
              </div>
            </div>

            <div className="p-4 bg-purple-100/60 border border-purple-200 rounded-lg space-y-2">
              <span className="font-bold text-purple-800 uppercase text-[10px] block">
                Simulated Scenario ({simBatchSize} units)
              </span>
              <div className="text-base font-black text-purple-950 font-mono">
                ₹{simResult.simulated.unit_economics.break_even_price?.toFixed(2)} / unit
              </div>
              <div className="text-[11px] text-purple-800">
                Total Batch Cost: ₹{simResult.simulated.total_manufacturing_cost?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
              <div className="text-[11px] text-purple-800">
                Target Selling Price: ₹{simResult.simulated.unit_economics.recommended_selling_price?.toFixed(2)}
              </div>
            </div>

            <div className="p-4 bg-white border border-slate-200 rounded-lg space-y-2">
              <span className="font-bold text-slate-500 uppercase text-[10px] block">
                Variance Impact
              </span>
              <div
                className={`text-base font-black font-mono ${
                  simResult.variance.delta_unit_cost <= 0 ? "text-emerald-700" : "text-red-700"
                }`}
              >
                {simResult.variance.delta_unit_cost <= 0 ? "Savings: " : "Increase: "}
                ₹{Math.abs(simResult.variance.delta_unit_cost).toFixed(2)} / unit ({simResult.variance.delta_unit_cost_pct?.toFixed(2)}%)
              </div>
              <div className="text-[11px] text-slate-600">
                Batch Variance: ₹{simResult.variance.delta_total_batch_cost?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
              <div className="text-[11px] font-bold text-emerald-700">
                {simResult.variance.delta_unit_cost <= 0 ? "Enhances gross margins" : "Eats into margins"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main 14-Factor Interactive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Cost Factors Controls */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4 text-xs">
            <h3 className="font-bold text-sm text-slate-900 border-b pb-2 flex items-center justify-between">
              <span>Operational Cost Centers (14-Factor Structure)</span>
              <span className="text-[10px] font-mono text-blue-600 uppercase">Deterministic Python Decimal</span>
            </h3>

            {/* Factor 1 & 2: Direct Materials & Scrap Credit */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-slate-50 rounded-lg">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  1. Raw Material Quoted Rate
                </label>
                <div className="relative">
                  <span className="absolute left-2.5 top-2 text-slate-400 font-mono">₹</span>
                  <input
                    type="number"
                    step="any"
                    value={rawUnitCost}
                    onChange={(e) => setRawUnitCost(parseFloat(e.target.value) || 0)}
                    className="w-full bg-white border border-slate-200 rounded-lg pl-7 pr-2 py-1.5 font-mono font-bold text-slate-900"
                  />
                </div>
                <span className="text-[10px] text-slate-500">From verified supplier quotes</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Gross Batch Consumption
                </label>
                <input
                  type="number"
                  step="any"
                  value={grossMaterialQty}
                  onChange={(e) => setGrossMaterialQty(parseFloat(e.target.value) || 0)}
                  className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                />
                <span className="text-[10px] text-slate-500">Includes 5% additive scrap</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  2. Recoverable Scrap Salvage Rate
                </label>
                <div className="relative">
                  <span className="absolute left-2.5 top-2 text-slate-400 font-mono">₹</span>
                  <input
                    type="number"
                    step="any"
                    value={scrapRecoveryRate}
                    onChange={(e) => setScrapRecoveryRate(parseFloat(e.target.value) || 0)}
                    className="w-full bg-white border border-slate-200 rounded-lg pl-7 pr-2 py-1.5 font-mono text-slate-900"
                  />
                </div>
                <span className="text-[10px] text-emerald-700 font-bold">Subtracted credit</span>
              </div>
            </div>

            {/* Factor 3, 4, 5: Labor, Setup & Machines */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-slate-50 rounded-lg">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  3. Direct Labor Run Hours
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={laborHours}
                    onChange={(e) => setLaborHours(parseFloat(e.target.value) || 0)}
                    className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                  />
                  <input
                    type="number"
                    value={laborRate}
                    title="Hourly Rate"
                    onChange={(e) => setLaborRate(parseFloat(e.target.value) || 0)}
                    className="w-24 bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                  />
                </div>
                <span className="text-[10px] text-slate-500">Hours @ ₹{laborRate}/hr</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  4. Setup & Changeover Hours
                </label>
                <input
                  type="number"
                  value={setupHours}
                  onChange={(e) => setSetupHours(parseFloat(e.target.value) || 0)}
                  className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                />
                <span className="text-[10px] text-slate-500">Tooling calibration hours</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  5. Machine Operating Hours
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={machineHours}
                    onChange={(e) => setMachineHours(parseFloat(e.target.value) || 0)}
                    className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                  />
                  <input
                    type="number"
                    value={machineRate}
                    title="Hourly Machine Rate"
                    onChange={(e) => setMachineRate(parseFloat(e.target.value) || 0)}
                    className="w-24 bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                  />
                </div>
                <span className="text-[10px] text-slate-500">CNC laser & brake @ ₹{machineRate}/hr</span>
              </div>
            </div>

            {/* Factor 6, 7, 8: Consumables, Tooling & Electricity */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-slate-50 rounded-lg">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  6. Consumables & Gases
                </label>
                <input
                  type="number"
                  value={consumablesCost}
                  onChange={(e) => setConsumablesCost(parseFloat(e.target.value) || 0)}
                  className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                />
                <span className="text-[10px] text-slate-500">TIG wire, argon gas, nozzle tips</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  7. Tooling Wear & Fixtures
                </label>
                <input
                  type="number"
                  value={toolingCost}
                  onChange={(e) => setToolingCost(parseFloat(e.target.value) || 0)}
                  className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                />
                <span className="text-[10px] text-slate-500">Press brake dies & jigs</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  8. Power / Electricity (kWh)
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={electricityKwh}
                    onChange={(e) => setElectricityKwh(parseFloat(e.target.value) || 0)}
                    className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                  />
                  <input
                    type="number"
                    value={tariff}
                    title="Tariff"
                    onChange={(e) => setTariff(parseFloat(e.target.value) || 0)}
                    className="w-20 bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                  />
                </div>
                <span className="text-[10px] text-slate-500">Industrial tariff ₹{tariff}/kWh</span>
              </div>
            </div>

            {/* Factor 9, 10, 11, 12: Secondary Processes, Testing, Packaging & Logistics */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 p-3 bg-slate-50 rounded-lg">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  9. Finishing / Subcontract
                </label>
                <input
                  type="number"
                  value={finishingCost}
                  onChange={(e) => setFinishingCost(parseFloat(e.target.value) || 0)}
                  className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                />
                <span className="text-[10px] text-slate-500">Powder coating / plating</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  10. QC & NDT Inspection
                </label>
                <input
                  type="number"
                  value={testingCost}
                  onChange={(e) => setTestingCost(parseFloat(e.target.value) || 0)}
                  className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                />
                <span className="text-[10px] text-slate-500">Dye penetrant & CMM</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  11. Packaging & Crating
                </label>
                <input
                  type="number"
                  value={packagingCost}
                  onChange={(e) => setPackagingCost(parseFloat(e.target.value) || 0)}
                  className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                />
                <span className="text-[10px] text-slate-500">Pallets & bubble wrap</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  12. Outward Freight
                </label>
                <input
                  type="number"
                  value={freightOutward}
                  onChange={(e) => setFreightOutward(parseFloat(e.target.value) || 0)}
                  className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                />
                <span className="text-[10px] text-slate-500">Dispatch delivery</span>
              </div>
            </div>

            {/* Factor 13 & 14: Factory & Admin Overheads */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 bg-slate-50 rounded-lg">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  13. Factory Overhead Rate (%)
                </label>
                <input
                  type="number"
                  step="any"
                  value={factoryOverheadRate}
                  onChange={(e) => setFactoryOverheadRate(parseFloat(e.target.value) || 0)}
                  className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                />
                <span className="text-[10px] text-slate-500">Supervision, depreciation, maintenance</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  14. Admin & SG&A Rate (%)
                </label>
                <input
                  type="number"
                  step="any"
                  value={adminOverheadRate}
                  onChange={(e) => setAdminOverheadRate(parseFloat(e.target.value) || 0)}
                  className="w-full bg-white border border-slate-200 rounded-lg p-1.5 font-mono text-slate-900"
                />
                <span className="text-[10px] text-slate-500">Corporate & administrative loading</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Cost Breakdown Waterfall & Margin Controls */}
        <div className="space-y-4">
          {/* Target Margin & Selling Price Control Card */}
          <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4 text-xs">
            <h3 className="font-bold text-sm text-slate-900 border-b pb-2">
              Pricing Strategy & Customer Quote
            </h3>

            <div>
              <div className="flex justify-between font-bold text-slate-700 mb-1">
                <span>Target Gross Margin:</span>
                <span className="text-blue-600 font-mono font-black">{targetMarginPct}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="50"
                step="1"
                value={targetMarginPct}
                onChange={(e) => setTargetMarginPct(parseInt(e.target.value))}
                className="w-full accent-blue-600"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>5% (Competitive)</span>
                <span>25% (Standard)</span>
                <span>50% (High Margin)</span>
              </div>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">
                Custom Customer Quoted Price (₹/unit)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-slate-400 font-mono font-bold">₹</span>
                <input
                  type="number"
                  step="any"
                  value={customPrice}
                  onChange={(e) => setCustomPrice(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-7 pr-3 py-1.5 font-mono font-bold text-slate-900"
                />
              </div>
              <span className="text-[10px] text-slate-500">Compare against break-even price</span>
            </div>

            {ue && (
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5">
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-600">Break-Even (0% Margin):</span>
                  <span className="font-mono font-bold text-slate-900">₹{ue.break_even_price?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-600">Target Selling Price ({targetMarginPct}%):</span>
                  <span className="font-mono font-bold text-emerald-700">₹{(ue.suggested_unit_price ?? ue.recommended_selling_price ?? 0).toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-600">Actual Margin at Quoted Rate:</span>
                  <span
                    className={`font-mono font-bold ${
                      isLossMaking ? "text-red-700" : "text-emerald-700"
                    }`}
                  >
                    {(ue.effective_margin_pct ?? ue.effective_gross_margin_pct ?? 0).toFixed(2)}%
                  </span>
                </div>
                <div className="flex justify-between text-[11px] border-t pt-1">
                  <span className="text-slate-600">Batch Net Profit:</span>
                  <span
                    className={`font-mono font-bold ${
                      isLossMaking ? "text-red-700" : "text-emerald-700"
                    }`}
                  >
                    ₹{(ue.projected_gross_profit ?? ue.total_profit ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* 14-Factor Itemized Cost Stack */}
          {cb && (
            <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3 text-xs">
              <h3 className="font-bold text-sm text-slate-900 border-b pb-2">
                Batch Cost Composition
              </h3>

              <div className="space-y-1.5 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-600">Direct Raw Material:</span>
                  <span className="font-mono font-bold text-slate-900">
                    ₹{(cb.effective_raw_material_cost ?? cb.direct_raw_material ?? cb.net_raw_material_cost ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex justify-between text-emerald-700 font-medium">
                  <span>Less: Scrap Salvage Credit:</span>
                  <span className="font-mono">
                    -₹{(cb.recoverable_scrap_credit || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-600">Direct Labor & Setup:</span>
                  <span className="font-mono font-bold text-slate-900">
                    ₹{((cb.direct_labor_cost ?? cb.direct_labor ?? 0) + (cb.setup_cost || 0)).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-600">Machine Operating Cost:</span>
                  <span className="font-mono font-bold text-slate-900">
                    ₹{(cb.machine_operating_cost ?? cb.machine_cost ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex justify-between font-bold border-t pt-1 text-slate-900">
                  <span>Total Prime Cost:</span>
                  <span className="font-mono">
                    ₹{(cb.direct_prime_cost ?? cb.prime_cost ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex justify-between text-slate-600">
                  <span>Electricity & Utilities:</span>
                  <span className="font-mono">
                    ₹{(cb.electricity_cost ?? cb.electricity ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex justify-between text-slate-600">
                  <span>Consumables & Tooling:</span>
                  <span className="font-mono">
                    ₹{((cb.consumables || 0) + (cb.tooling || 0)).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex justify-between text-slate-600">
                  <span>Finishing, QC & Logistics:</span>
                  <span className="font-mono">
                    ₹{(
                      (cb.secondary_processes_cost ?? cb.secondary_processes ?? 0) +
                      (cb.testing_inspection || 0) +
                      (cb.packaging_cost ?? cb.packaging ?? 0) +
                      (cb.transportation_cost ?? cb.transportation ?? 0)
                    ).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex justify-between text-slate-600">
                  <span>Factory & Admin Overheads:</span>
                  <span className="font-mono">
                    ₹{((cb.allocated_overhead_cost ?? cb.factory_overhead ?? 0) + (cb.admin_overhead || 0)).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex justify-between font-black text-sm border-t-2 pt-2 text-slate-950">
                  <span>Total Cost (Batch):</span>
                  <span className="font-mono">
                    ₹{(cb.total_production_cost ?? costResult.total_manufacturing_cost ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
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
