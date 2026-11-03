"use client";

import React from "react";
import { BarChart3, TrendingUp, PieChart, ShieldCheck } from "lucide-react";

export default function AnalyticsView({ metrics }: { metrics: any }) {
  const spend = metrics?.procurement_spend_total || 903692;
  const savings = metrics?.total_savings_generated || 16000;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-600" />
          <span>Procurement Spending & Sourcing Analytics</span>
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Audited metrics on material expenditure, supplier performance distribution, and landed savings.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            Category Spend Share
          </span>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between font-mono">
              <span className="text-slate-600">Stainless Steel Sheets (SS304/316):</span>
              <span className="font-bold text-blue-700">68%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5">
              <div className="bg-blue-600 h-1.5 rounded-full w-[68%]" />
            </div>

            <div className="flex justify-between font-mono pt-2">
              <span className="text-slate-600">Structural Carbon Steel (IS 2062):</span>
              <span className="font-bold text-teal-700">18%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5">
              <div className="bg-teal-600 h-1.5 rounded-full w-[18%]" />
            </div>

            <div className="flex justify-between font-mono pt-2">
              <span className="text-slate-600">Fasteners & Consumables:</span>
              <span className="font-bold text-indigo-700">14%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5">
              <div className="bg-indigo-600 h-1.5 rounded-full w-[14%]" />
            </div>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            Vendor Quality Distribution
          </span>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between font-mono">
              <span className="text-slate-600">Tier 1 (&gt; 90% Reliability):</span>
              <span className="font-bold text-emerald-700">5 Vendors</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5">
              <div className="bg-emerald-600 h-1.5 rounded-full w-[50%]" />
            </div>

            <div className="flex justify-between font-mono pt-2">
              <span className="text-slate-600">Tier 2 (80-90% Reliability):</span>
              <span className="font-bold text-blue-700">3 Vendors</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5">
              <div className="bg-blue-600 h-1.5 rounded-full w-[30%]" />
            </div>

            <div className="flex justify-between font-mono pt-2">
              <span className="text-slate-600">Tier 3 (&lt; 80% High Risk):</span>
              <span className="font-bold text-amber-700">2 Vendors</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5">
              <div className="bg-amber-500 h-1.5 rounded-full w-[20%]" />
            </div>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            Landed Savings Rate
          </span>
          <div className="text-3xl font-black text-slate-900 font-mono mt-1">
            ₹{savings.toLocaleString("en-IN")}
          </div>
          <p className="text-xs text-slate-600">
            Average <b className="text-slate-900">5.8%</b> landed price discount achieved through evidence-backed negotiation
            counteroffers citing volume and competitor benchmarks.
          </p>
        </div>
      </div>
    </div>
  );
}
