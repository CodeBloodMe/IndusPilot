"use client";

import React, { useState } from "react";
import {
  Compass,
  CheckCircle2,
  AlertTriangle,
  Play,
  Layers,
  ArrowRight,
  ShieldCheck,
  Split,
} from "lucide-react";
import { solveOptimization } from "@/lib/api";

export default function OptimizationView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  const [requiredQuantity, setRequiredQuantity] = useState<number>(800);
  const [budgetLimit, setBudgetLimit] = useState<number>(275000);
  const [maxLeadTime, setMaxLeadTime] = useState<number>(10);
  const [singleSupplier, setSingleSupplier] = useState<boolean>(false);

  const [solution, setSolution] = useState<any>(null);
  const [solving, setSolving] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSolve = async () => {
    try {
      setSolving(true);
      setErrorMsg(null);
      const res = await solveOptimization({
        required_quantity: requiredQuantity,
        budget_limit: budgetLimit > 0 ? budgetLimit : undefined,
        max_lead_time_days: maxLeadTime > 0 ? maxLeadTime : undefined,
        enforce_single_supplier: singleSupplier,
      });
      setSolution(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Optimization solver encountered an error.");
    } finally {
      setSolving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Compass className="w-5 h-5 text-blue-600" />
            <span>Google OR-Tools Mathematical Procurement Optimizer</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Mixed-Integer Linear Programming (MILP) solver that optimizes supplier quota allocation,
            respecting Minimum Order Quantities (MOQ), vendor capacities, and budget bounds.
          </p>
        </div>

        <button
          onClick={handleSolve}
          disabled={solving}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-50"
        >
          <Play className={`w-4 h-4 fill-white ${solving ? "animate-spin" : ""}`} />
          <span>{solving ? "Solving MILP Model..." : "Solve Optimal Allocation"}</span>
        </button>
      </div>

      {errorMsg && (
        <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
          {errorMsg}
        </div>
      )}

      {/* Constraints Setup Console */}
      <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider border-b border-slate-200 pb-2">
          Mathematical Optimization Parameters
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
          <div>
            <label className="text-slate-600 block text-[11px] font-semibold mb-1">
              Required Volume:
            </label>
            <input
              type="number"
              value={requiredQuantity}
              onChange={(e) => setRequiredQuantity(Number(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 font-mono text-xs"
            />
          </div>

          <div>
            <label className="text-slate-600 block text-[11px] font-semibold mb-1">
              Max Purchasing Budget (₹):
            </label>
            <input
              type="number"
              value={budgetLimit}
              onChange={(e) => setBudgetLimit(Number(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 font-mono text-xs"
            />
          </div>

          <div>
            <label className="text-slate-600 block text-[11px] font-semibold mb-1">
              Max Delivery Lead Time (Days):
            </label>
            <input
              type="number"
              value={maxLeadTime}
              onChange={(e) => setMaxLeadTime(Number(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 font-mono text-xs"
            />
          </div>

          <div className="flex flex-col justify-end">
            <label className="flex items-center gap-2 cursor-pointer pb-2 text-slate-700">
              <input
                type="checkbox"
                checked={singleSupplier}
                onChange={(e) => setSingleSupplier(e.target.checked)}
                className="rounded accent-blue-600"
              />
              <span className="font-semibold text-xs">Enforce Single Vendor</span>
            </label>
          </div>
        </div>
      </div>

      {/* Results View */}
      {solution && (
        <div className="space-y-6">
          {/* Solution Status Banner */}
          <div
            className={`p-5 rounded-xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-white ${
              solution.status === "OPTIMAL"
                ? "border-blue-300 shadow-sm"
                : "border-red-200 bg-red-50"
            }`}
          >
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    solution.status === "OPTIMAL"
                      ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                      : "bg-red-50 text-red-700 border-red-300"
                  }`}
                >
                  Solver: {solution.status}
                </span>
                <span className="text-xs text-slate-500 font-mono">SCIP MILP Solver Engine</span>
              </div>
              <h3 className="text-lg font-black text-slate-900 mt-1">
                Optimal Landed Expenditure: ₹{solution.total_cost?.toLocaleString("en-IN")}
              </h3>
              <p className="text-xs text-slate-600 mt-1 whitespace-pre-line max-w-2xl font-mono">
                {solution.explanation}
              </p>
            </div>

            {solution.budget_utilized_pct && (
              <div className="text-right shrink-0">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">
                  Budget Utilization
                </span>
                <span className="text-2xl font-black text-blue-700 font-mono">
                  {solution.budget_utilized_pct}%
                </span>
                <span className="text-[10px] text-slate-500 block">
                  Cap: ₹{budgetLimit.toLocaleString("en-IN")}
                </span>
              </div>
            )}
          </div>

          {/* Allocation Cards */}
          {solution.allocations && solution.allocations.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Recommended Purchasing Splits ({solution.allocations.length} Suppliers Selected)
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {solution.allocations.map((alloc: any, i: number) => (
                  <div
                    key={i}
                    className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h5 className="text-sm font-bold text-slate-900">{alloc.supplier_name}</h5>
                        <span className="text-[11px] text-slate-500">
                          Lead Time: {alloc.lead_time_days} Days • MOQ: {alloc.moq} kg
                        </span>
                      </div>
                      <span className="px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-bold font-mono">
                        {alloc.allocated_quantity} kg
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex justify-between text-xs">
                      <span className="text-slate-600">Unit Landed: ₹{alloc.unit_landed_cost}/kg</span>
                      <span className="font-bold text-slate-900 font-mono">
                        Subtotal: ₹{alloc.supplier_subtotal?.toLocaleString("en-IN")}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Constraints Satisfied */}
          {solution.constraints_satisfied && (
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs space-y-2">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
                Linear Optimization Constraints Verified:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-700">
                {solution.constraints_satisfied.map((cs: string, idx: number) => (
                  <div key={idx} className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    <span>{cs}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

