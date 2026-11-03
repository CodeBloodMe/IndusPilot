"use client";

import React, { useState, useEffect } from "react";
import {
  Scale,
  Award,
  CheckCircle2,
  TrendingUp,
  Clock,
  ShieldCheck,
  CreditCard,
  ArrowRight,
  Handshake,
} from "lucide-react";
import { getQuotations, evaluateComparison } from "@/lib/api";

export default function SupplierCompareView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  const [quotations, setQuotations] = useState<any[]>([]);
  const [targetQuantity, setTargetQuantity] = useState<number>(800);
  const [comparisonResult, setComparisonResult] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadData();
  }, [targetQuantity]);

  const loadData = async () => {
    try {
      setLoading(true);
      const quotes = await getQuotations();
      setQuotations(quotes);

      if (quotes.length > 0) {
        const quoteIds = quotes.map((q: any) => q.id);
        const comp = await evaluateComparison(quoteIds, targetQuantity);
        setComparisonResult(comp);
      }
    } catch (err) {
      console.error("Comparison load error:", err);
    } finally {
      setLoading(false);
    }
  };

  const getBadgeColor = (band: string) => {
    switch (band) {
      case "STRONGLY_RECOMMENDED":
        return "bg-emerald-50 text-emerald-700 border-emerald-300";
      case "VIABLE_ALTERNATIVE":
        return "bg-blue-50 text-blue-700 border-blue-300";
      case "HIGH_RISK_CONSIDERATION":
        return "bg-amber-50 text-amber-700 border-amber-300";
      default:
        return "bg-red-50 text-red-700 border-red-300";
    }
  };

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Scale className="w-5 h-5 text-blue-600" />
            <span>Explainable Supplier Comparison Engine</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Evaluates total landed cost and applies 5-factor weighted scoring. Explains why the top vendor is chosen.
          </p>
        </div>

        {/* Quantity selector */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-600 font-medium">Batch Volume:</span>
          <div className="flex items-center gap-1 bg-slate-100 border border-slate-200 rounded-lg p-1">
            {[500, 800, 1000].map((qty) => (
              <button
                key={qty}
                onClick={() => setTargetQuantity(qty)}
                className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${
                  targetQuantity === qty
                    ? "bg-blue-600 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {qty} kg
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
          Computing multi-dimensional landed cost scorecards...
        </div>
      ) : !comparisonResult || !comparisonResult.candidates ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
          No verified supplier quotations available to compare. Upload quotes or click "Seed Demo Data".
        </div>
      ) : (
        <div className="space-y-6">
          {/* Winner Showcase Banner */}
          {comparisonResult.recommended_candidate && (
            <div className="p-5 rounded-xl bg-gradient-to-r from-blue-50 via-teal-50 to-white border border-blue-200 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div className="w-11 h-11 rounded-xl bg-blue-100 border border-blue-200 flex items-center justify-center text-blue-600">
                  <Award className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase font-extrabold tracking-wider text-blue-700">
                      Rank #1 Recommendation
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getBadgeColor(
                        comparisonResult.recommended_candidate.decision_band
                      )}`}
                    >
                      {comparisonResult.recommended_candidate.decision_band.replace(/_/g, " ")}
                    </span>
                  </div>
                  <h3 className="text-lg font-black text-slate-900 mt-0.5">
                    {comparisonResult.recommended_candidate.supplier_name}
                  </h3>
                  <p className="text-xs text-slate-600 mt-1 max-w-2xl">
                    {comparisonResult.recommended_candidate.rationale}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 shrink-0">
                <div className="text-right">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Composite Score</span>
                  <span className="text-2xl font-black text-blue-700 font-mono">
                    {comparisonResult.recommended_candidate.composite_score}/100
                  </span>
                </div>
                <button
                  onClick={() => setActiveTab("negotiation")}
                  className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all"
                >
                  <Handshake className="w-4 h-4" />
                  <span>Negotiate Counteroffer</span>
                </button>
              </div>
            </div>
          )}

          {/* Comparative Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {comparisonResult.candidates.map((cand: any, idx: number) => {
              const isTop = idx === 0;
              return (
                <div
                  key={idx}
                  className={`p-5 rounded-xl border flex flex-col justify-between transition-all bg-white ${
                    isTop
                      ? "border-blue-400 shadow-md ring-1 ring-blue-300"
                      : "border-slate-200 shadow-xs hover:border-slate-300"
                  }`}
                >
                  <div>
                    {/* Top title bar */}
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono font-bold text-slate-400">
                        Rank #{idx + 1}
                      </span>
                      <span
                        className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${getBadgeColor(
                          cand.decision_band
                        )}`}
                      >
                        {cand.decision_band.replace(/_/g, " ")}
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-slate-900 leading-snug">{cand.supplier_name}</h4>
                    <span className="text-[11px] text-slate-500 block mb-3">
                      Quote: {cand.quotation_number} • {cand.city}
                    </span>

                    {/* Cost block */}
                    <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 mb-4 space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-500">Quoted Face Price:</span>
                        <span className="font-mono font-semibold text-slate-800">
                          ₹{cand.quoted_unit_price.toFixed(2)} / kg
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-500">Freight & Logistics:</span>
                        <span className="font-mono text-slate-800">
                          ₹{cand.landed_cost_breakdown.freight_cost?.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs pt-1 border-t border-slate-200">
                        <span className="text-slate-700 font-semibold">Effective Landed:</span>
                        <span className="font-mono font-bold text-blue-700 text-sm">
                          ₹{cand.effective_unit_landed_cost.toFixed(2)} / kg
                        </span>
                      </div>
                      <div className="flex justify-between text-[11px] text-slate-500">
                        <span>Total Landed ({targetQuantity} kg):</span>
                        <span className="font-mono font-bold text-slate-900">
                          ₹{cand.total_landed_cost.toLocaleString("en-IN")}
                        </span>
                      </div>
                    </div>

                    {/* Operational metrics */}
                    <div className="space-y-1.5 text-xs text-slate-700 mb-4">
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-1.5 text-slate-500">
                          <Clock className="w-3.5 h-3.5 text-blue-600" /> Lead Time
                        </span>
                        <span className="font-mono font-semibold">{cand.lead_time_days} Days</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-1.5 text-slate-500">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" /> Reliability
                        </span>
                        <span className="font-mono font-semibold">{cand.reliability_score}%</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-1.5 text-slate-500">
                          <CreditCard className="w-3.5 h-3.5 text-indigo-600" /> Credit Terms
                        </span>
                        <span className="font-mono font-semibold">{cand.payment_terms_days} Days</span>
                      </div>
                    </div>

                    {/* 5-Factor Score breakdown */}
                    <div className="border-t border-slate-200 pt-3">
                      <div className="flex justify-between items-center text-xs mb-1.5 font-bold">
                        <span className="text-slate-500">Composite Score</span>
                        <span className="text-blue-700 font-mono text-sm">{cand.composite_score}/100</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-blue-600 h-1.5 rounded-full"
                          style={{ width: `${cand.composite_score}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => setActiveTab("negotiation")}
                    className="w-full mt-4 py-2 rounded-lg bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-xs font-semibold text-slate-700 transition-colors flex items-center justify-center gap-1.5 border border-slate-200"
                  >
                    <span>Start Negotiation</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

