"use client";

import React, { useState } from "react";
import {
  Factory,
  Cpu,
  RefreshCw,
  Bell,
  CheckCircle2,
  AlertTriangle,
  Globe2,
} from "lucide-react";
import { seedDemo } from "@/lib/api";

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingApprovalsCount: number;
  onRefresh: () => void;
}

export default function Header({
  activeTab,
  setActiveTab,
  pendingApprovalsCount,
  onRefresh,
}: HeaderProps) {
  const [seeding, setSeeding] = useState(false);
  const [seedSuccess, setSeedSuccess] = useState(false);

  const handleSeed = async () => {
    try {
      setSeeding(true);
      await seedDemo(true);
      setSeedSuccess(true);
      setTimeout(() => setSeedSuccess(false), 3000);
      onRefresh();
    } catch (err) {
      console.error("Seeding failed", err);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <header className="h-16 bg-white/95 border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30 backdrop-blur-md shadow-sm">
      {/* Factory and Organization Banner */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
          <Factory className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-bold text-slate-900 tracking-wide">
              Apex Precision Fabrication Works
            </h1>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              Plant 1 — Bengaluru
            </span>
          </div>
          <p className="text-xs text-slate-500">
            GSTIN: 29AAACA1122K1Z9 • Category: Heavy Metal Fabrication • Currency: INR (₹)
          </p>
        </div>
      </div>

      {/* Right controls: Language, Approvals, Seed Demo */}
      <div className="flex items-center gap-3">
        {/* Language Indicator */}
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-md bg-slate-100 border border-slate-200 text-xs text-slate-700 font-medium">
          <Globe2 className="w-3.5 h-3.5 text-teal-600" />
          <span>EN • हिंदी • Hinglish</span>
        </div>

        {/* Simulation mode indicator */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 border border-emerald-200 text-xs text-emerald-700 font-medium">
          <Cpu className="w-3.5 h-3.5" />
          <span>Simulated Safe Mode</span>
        </div>

        {/* Pending Approvals Quick Pill */}
        <button
          onClick={() => setActiveTab("approvals")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
            pendingApprovalsCount > 0
              ? "bg-amber-50 border border-amber-300 text-amber-800 hover:bg-amber-100"
              : "bg-slate-100 border border-slate-200 text-slate-600 hover:text-slate-900"
          }`}
        >
          <Bell className="w-3.5 h-3.5 text-amber-600" />
          <span>Approvals</span>
          {pendingApprovalsCount > 0 && (
            <span className="w-4 h-4 rounded-full bg-amber-500 text-white font-bold flex items-center justify-center text-[10px]">
              {pendingApprovalsCount}
            </span>
          )}
        </button>

        {/* Demonstration Re-Seed Button */}
        <button
          onClick={handleSeed}
          disabled={seeding}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
          title="Reset deterministic synthetic demonstration testbed"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${seeding ? "animate-spin" : ""}`} />
          <span>{seeding ? "Seeding..." : seedSuccess ? "Seeded!" : "Seed Demo Data"}</span>
        </button>
      </div>
    </header>
  );
}

