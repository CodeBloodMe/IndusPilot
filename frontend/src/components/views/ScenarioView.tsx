"use client";

import React from "react";
import {
  BookOpenCheck,
  CheckCircle2,
  ArrowRight,
  Layers,
  FileSpreadsheet,
  Scale,
  Handshake,
  Compass,
  Calculator,
  FileCheck2,
  Bot,
} from "lucide-react";

export default function ScenarioView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  const steps = [
    {
      step: 1,
      title: "Order Specification & BOM Explosion",
      desc: "Customer order for 500 Industrial Mounting Brackets (SS304-BRK-500). The BOM engine explodes components with 5% laser cutting scrap, calculating a gross requirement of 1,050 kg.",
      targetTab: "bom",
      btnText: "Inspect BOM Engine",
      icon: Layers,
    },
    {
      step: 2,
      title: "Warehouse Inventory Audit & Shortage Netting",
      desc: "Warehouse holds 250 kg on hand with 50 kg reserved for prior jobs (200 kg available). With a 50 kg safety buffer, the net shortage is calculated at exactly 900 kg.",
      targetTab: "inventory",
      btnText: "View Stock & Shortages",
      icon: Layers,
    },
    {
      step: 3,
      title: "Document Ingestion & Automated Quality Gate",
      desc: "Upload 3 vendor quotation PDFs (Apex Steel, Bharat Forgings, Deccan Precision). PyMuPDF and OCR extract unit rates, freight charges, MOQs, and GST terms with confidence scoring.",
      targetTab: "quotations",
      btnText: "Test PDF Ingestion",
      icon: FileSpreadsheet,
    },
    {
      step: 4,
      title: "Explainable 5-Factor Supplier Comparison",
      desc: "Evaluates true landed costs and scores vendors on Cost (35%), Quality (25%), Reliability (15%), Lead Time (15%), and Payment Terms (10%). Apex Steel earns Rank #1 (84.8/100).",
      targetTab: "compare",
      btnText: "Compare Landed Scorecards",
      icon: Scale,
    },
    {
      step: 5,
      title: "Autonomous Negotiation & Concession Curve",
      desc: "Negotiation Agent drafts an evidence-backed counteroffer proposing ₹295/kg with 15-day payment terms. Simulates realistic vendor concession to ₹305/kg, saving ₹8,000 on the batch.",
      targetTab: "negotiation",
      btnText: "Open Negotiation Centre",
      icon: Handshake,
    },
    {
      step: 6,
      title: "Google OR-Tools Mixed-Integer Linear Optimization",
      desc: "Mathematical optimization solver splits volumes across vendors under Minimum Order Quantities (MOQ), vendor capacity ceilings, and purchasing budget constraints.",
      targetTab: "optimizer",
      btnText: "Run OR-Tools Solver",
      icon: Compass,
    },
    {
      step: 7,
      title: "Deterministic 14-Factor Manufacturing Cost Engine",
      desc: "Uses Python Decimal to calculate raw material, scrap yields, operator labor, machine amortization, electricity kWh, finishing, and overheads. Computes break-even cost: ₹637.00.",
      targetTab: "costing",
      btnText: "Launch Cost Calculator",
      icon: Calculator,
    },
    {
      step: 8,
      title: "Commercial Customer Quotation & PDF Export",
      desc: "Generates client quote at ₹850/bracket (25.1% gross margin). Enforces zero-loss safeguard and exports an audited, client-ready industrial PDF document.",
      targetTab: "customer-quotes",
      btnText: "Generate Customer Quote",
      icon: FileCheck2,
    },
    {
      step: 9,
      title: "Multilingual AI Manufacturing Copilot",
      desc: "Allows workshop supervisors to interact in everyday Hindi and Hinglish ('500 brackets ka shortage check karo') with direct tool calls and deterministic backend math.",
      targetTab: "copilot",
      btnText: "Chat with Copilot",
      icon: Bot,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <BookOpenCheck className="w-5 h-5 text-blue-600" />
          <span>Tech4Bharat 2026 Judge Demonstration Guide</span>
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Follow the canonical 9-step industrial journey for 500 Stainless Steel Industrial Brackets.
          Click any step to jump directly to that live module.
        </p>
      </div>

      {/* Steps List */}
      <div className="space-y-4">
        {steps.map((st) => {
          const Icon = st.icon;
          return (
            <div
              key={st.step}
              className="p-5 rounded-xl bg-white border border-slate-200 hover:border-blue-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center font-black font-mono shrink-0">
                  {st.step}
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <span>{st.title}</span>
                  </h3>
                  <p className="text-xs text-slate-600 mt-1 max-w-3xl leading-relaxed">
                    {st.desc}
                  </p>
                </div>
              </div>

              <button
                onClick={() => setActiveTab(st.targetTab)}
                className="shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-100 hover:bg-blue-50 text-blue-700 font-bold text-xs border border-slate-200 hover:border-blue-300 transition-all self-start sm:self-auto"
              >
                <span>{st.btnText}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
