"use client";

import React, { useState } from "react";
import { Settings, Factory, RefreshCw, CheckCircle2 } from "lucide-react";
import { seedDemo } from "@/lib/api";

export default function SettingsView({ onRefresh }: { onRefresh: () => void }) {
  const [seeding, setSeeding] = useState(false);
  const [seedSuccess, setSeedSuccess] = useState(false);

  const handleReset = async () => {
    try {
      setSeeding(true);
      await seedDemo(true);
      setSeedSuccess(true);
      setTimeout(() => setSeedSuccess(false), 3000);
      onRefresh();
    } catch (err) {
      console.error("Seed error:", err);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <Settings className="w-5 h-5 text-blue-600" />
          <span>Factory Organization & Sourcing Parameters</span>
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Enterprise configuration, shop floor labor benchmarks, electricity utility rates, and demonstration controls.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
            <Factory className="w-4 h-4 text-blue-600" />
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Plant Profile & Credentials
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="text-slate-600 block mb-1">Registered Enterprise Name:</label>
              <input
                type="text"
                readOnly
                value="Apex Precision Fabrication Works Pvt Ltd"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900 font-semibold"
              />
            </div>

            <div>
              <label className="text-slate-600 block mb-1">Plant Location:</label>
              <input
                type="text"
                readOnly
                value="Plot 42, 2nd Phase, Peenya Industrial Area, Bengaluru - 560058"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-700"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-slate-600 block mb-1">GSTIN Tax Identifier:</label>
                <input
                  type="text"
                  readOnly
                  value="29AAACA1122K1Z9"
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900 font-mono"
                />
              </div>
              <div>
                <label className="text-slate-600 block mb-1">Base Currency:</label>
                <input
                  type="text"
                  readOnly
                  value="INR (₹ Indian Rupee)"
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
          <div className="border-b border-slate-200 pb-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Cost Intelligence Benchmarks
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="text-slate-600 block mb-1">Default Factory Overhead:</label>
              <input
                type="text"
                readOnly
                value="12.0% of direct prime cost"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-blue-700 font-mono font-bold"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-slate-600 block mb-1">Electricity Tariff (kVA/kWh):</label>
                <input
                  type="text"
                  readOnly
                  value="₹8.50 / kWh (BESCOM HT-2a)"
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900 font-mono"
                />
              </div>
              <div>
                <label className="text-slate-600 block mb-1">Operator Standard Rate:</label>
                <input
                  type="text"
                  readOnly
                  value="₹180.00 / hour"
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900 font-mono"
                />
              </div>
            </div>

            {/* Demonstration Testbed Controls */}
            <div className="pt-3 border-t border-slate-200 space-y-2">
              <span className="text-xs font-bold text-slate-900 block">Demonstration Testbed</span>
              <p className="text-[11px] text-slate-500">
                Resets the database with 10 synthetic suppliers, 20 materials, active quotes,
                and the canonical 500 Industrial Brackets test scenario.
              </p>
              <button
                onClick={handleReset}
                disabled={seeding}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${seeding ? "animate-spin" : ""}`} />
                <span>{seeding ? "Resetting Database..." : seedSuccess ? "Demo Reset Successful!" : "Re-seed Demo Data"}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
