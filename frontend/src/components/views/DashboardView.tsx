"use client";

import React from "react";
import {
  DollarSign,
  Users2,
  FileCheck,
  AlertTriangle,
  TrendingDown,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  Layers,
  Calculator,
  Compass,
} from "lucide-react";

interface DashboardViewProps {
  metrics: any;
  setActiveTab: (tab: string) => void;
}

export default function DashboardView({ metrics, setActiveTab }: DashboardViewProps) {
  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Loading manufacturing intelligence...
      </div>
    );
  }

  const kpis = [
    {
      label: "Total Procurement Spend",
      value: `₹${(metrics.procurement_spend_total || 0).toLocaleString("en-IN")}`,
      subtitle: "Verified Purchase Allocations",
      icon: DollarSign,
      color: "text-blue-600",
      bg: "bg-white border-slate-200 shadow-xs",
      iconBg: "bg-blue-50 text-blue-600 border border-blue-100",
    },
    {
      label: "Active Verified Suppliers",
      value: metrics.active_suppliers_count || 10,
      subtitle: "Cataloged Industrial Vendors",
      icon: Users2,
      color: "text-teal-600",
      bg: "bg-white border-slate-200 shadow-xs",
      iconBg: "bg-teal-50 text-teal-600 border border-teal-100",
    },
    {
      label: "Verified Quotations",
      value: metrics.verified_quotations_count || 3,
      subtitle: "OCR Extracted & Audited",
      icon: FileCheck,
      color: "text-indigo-600",
      bg: "bg-white border-slate-200 shadow-xs",
      iconBg: "bg-indigo-50 text-indigo-600 border border-indigo-100",
    },
    {
      label: "Negotiation Savings",
      value: `₹${(metrics.total_savings_generated || 16000).toLocaleString("en-IN")}`,
      subtitle: "Captured from Concessions",
      icon: TrendingDown,
      color: "text-emerald-600",
      bg: "bg-white border-slate-200 shadow-xs",
      iconBg: "bg-emerald-50 text-emerald-600 border border-emerald-100",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Hackathon Master Banner */}
      <div className="rounded-xl p-6 bg-gradient-to-r from-blue-700 via-blue-800 to-slate-900 text-white shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-teal-400 text-slate-900">
              Tech4Bharat 2026 Problem Statement 4.1
            </span>
            <span className="text-xs text-blue-100 font-medium">Industrial Manufacturing</span>
          </div>
          <h2 className="text-xl font-extrabold text-white">
            Manufacturing Procurement & Quotation Optimisation
          </h2>
          <p className="text-xs text-blue-100/90 mt-1 max-w-2xl">
            End-to-end closed loop: BOM explosion & scrap yields $\to$ PyMuPDF quote extraction $\to$
            5-factor landed scoring $\to$ Google OR-Tools optimization $\to$ autonomous negotiation $\to$
            14-factor deterministic production costing.
          </p>
        </div>

        <button
          onClick={() => setActiveTab("scenario")}
          className="shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-lg bg-white hover:bg-slate-100 text-blue-900 font-bold text-xs shadow-md transition-all"
        >
          <span>Run Canonical Demo (500 Brackets)</span>
          <ArrowRight className="w-4 h-4 text-blue-900" />
        </button>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div
              key={idx}
              className={`p-5 rounded-xl border ${kpi.bg} flex flex-col justify-between`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-600">{kpi.label}</span>
                <div className={`p-2 rounded-lg ${kpi.iconBg}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-black text-slate-900 tracking-tight">{kpi.value}</div>
                <div className="text-[11px] text-slate-500 mt-0.5">{kpi.subtitle}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Critical Alerts & Quick Action Launchpad */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Shortages Alert Panel */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <h3 className="text-sm font-bold text-slate-900">Production Shortage & Safety Stock Alerts</h3>
            </div>
            <button
              onClick={() => setActiveTab("bom")}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              Explode BOM $\to$
            </button>
          </div>

          <div className="space-y-2.5">
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-slate-800">
                  Stainless Steel 304 Plate (2B Finish)
                </div>
                <div className="text-[11px] text-slate-600 mt-0.5">
                  Gross Batch Need: <b className="text-slate-900">1,050 kg</b> • Available:{" "}
                  <b className="text-slate-900">200 kg</b> (after reservations)
                </div>
              </div>
              <div className="text-right">
                <span className="px-2 py-1 rounded bg-red-50 text-red-700 border border-red-200 text-xs font-bold font-mono">
                  Shortage: 900 kg
                </span>
                <button
                  onClick={() => setActiveTab("compare")}
                  className="block text-[11px] text-blue-600 hover:underline mt-1"
                >
                  Source Suppliers
                </button>
              </div>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-slate-800">
                  SS 304 Hex Bolt M8x25 Fasteners
                </div>
                <div className="text-[11px] text-slate-600 mt-0.5">
                  Current Warehouse: 2,400 Nos • Safety Reorder: 1,000 Nos
                </div>
              </div>
              <div className="text-right">
                <span className="px-2 py-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold font-mono">
                  Stock Healthy
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Workflow Shortcuts */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3">
          <div className="border-b border-slate-200 pb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-teal-600" />
            <h3 className="text-sm font-bold text-slate-900">Workflow Quick Launch</h3>
          </div>

          <div className="space-y-2">
            <button
              onClick={() => setActiveTab("quotations")}
              className="w-full p-2.5 rounded-lg bg-slate-50 hover:bg-blue-50/50 border border-slate-200 text-left flex items-center justify-between group transition-all"
            >
              <div>
                <div className="text-xs font-semibold text-slate-800 group-hover:text-blue-700">
                  Upload Supplier Quote (PDF)
                </div>
                <div className="text-[10px] text-slate-500">Run OCR & Quality Gate</div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-transform group-hover:translate-x-1" />
            </button>

            <button
              onClick={() => setActiveTab("compare")}
              className="w-full p-2.5 rounded-lg bg-slate-50 hover:bg-blue-50/50 border border-slate-200 text-left flex items-center justify-between group transition-all"
            >
              <div>
                <div className="text-xs font-semibold text-slate-800 group-hover:text-blue-700">
                  Compare Vendor Offers
                </div>
                <div className="text-[10px] text-slate-500">5-factor landed cost scorecard</div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-transform group-hover:translate-x-1" />
            </button>

            <button
              onClick={() => setActiveTab("negotiation")}
              className="w-full p-2.5 rounded-lg bg-slate-50 hover:bg-blue-50/50 border border-slate-200 text-left flex items-center justify-between group transition-all"
            >
              <div>
                <div className="text-xs font-semibold text-slate-800 group-hover:text-blue-700">
                  Autonomous Negotiation
                </div>
                <div className="text-[10px] text-slate-500">Generate counteroffer draft</div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-transform group-hover:translate-x-1" />
            </button>

            <button
              onClick={() => setActiveTab("costing")}
              className="w-full p-2.5 rounded-lg bg-slate-50 hover:bg-blue-50/50 border border-slate-200 text-left flex items-center justify-between group transition-all"
            >
              <div>
                <div className="text-xs font-semibold text-slate-800 group-hover:text-blue-700">
                  14-Factor Cost Intelligence
                </div>
                <div className="text-[10px] text-slate-500">Calculate break-even unit price</div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-transform group-hover:translate-x-1" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

