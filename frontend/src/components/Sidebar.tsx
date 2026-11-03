"use client";

import React from "react";
import {
  LayoutDashboard,
  FileSpreadsheet,
  Scale,
  Handshake,
  Compass,
  Boxes,
  Layers,
  Calculator,
  FileCheck2,
  Users2,
  Bot,
  ShieldCheck,
  BarChart3,
  Settings,
  BookOpenCheck,
  Zap,
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingApprovalsCount: number;
  shortagesCount: number;
}

export default function Sidebar({
  activeTab,
  setActiveTab,
  pendingApprovalsCount,
  shortagesCount,
}: SidebarProps) {
  const navSections = [
    {
      title: "PROCUREMENT INTELLIGENCE",
      items: [
        { id: "dashboard", label: "Executive Dashboard", icon: LayoutDashboard },
        { id: "quotations", label: "Quotation Ingestion", icon: FileSpreadsheet },
        { id: "compare", label: "Supplier Comparison", icon: Scale },
        { id: "negotiation", label: "Autonomous Negotiation", icon: Handshake },
        { id: "optimizer", label: "OR-Tools Optimizer", icon: Compass, badge: "MILP" },
      ],
    },
    {
      title: "MANUFACTURING & COSTING",
      items: [
        { id: "bom", label: "Bill of Materials (BOM)", icon: Layers },
        {
          id: "inventory",
          label: "Inventory & Shortages",
          icon: Boxes,
          badgeCount: shortagesCount > 0 ? shortagesCount : undefined,
          badgeColor: "bg-red-500",
        },
        { id: "costing", label: "14-Factor Cost Engine", icon: Calculator },
        { id: "customer-quotes", label: "Customer Quotations", icon: FileCheck2 },
      ],
    },
    {
      title: "ENTERPRISE & COPILOT",
      items: [
        { id: "suppliers", label: "Supplier Directory", icon: Users2 },
        { id: "copilot", label: "AI Manufacturing Copilot", icon: Bot, badge: "Hindi/EN" },
        {
          id: "approvals",
          label: "Approval Centre",
          icon: ShieldCheck,
          badgeCount: pendingApprovalsCount > 0 ? pendingApprovalsCount : undefined,
          badgeColor: "bg-amber-500",
        },
        { id: "analytics", label: "Spend Analytics", icon: BarChart3 },
        { id: "scenario", label: "Hackathon Demo Guide", icon: BookOpenCheck, badge: "500 Brackets" },
        { id: "settings", label: "Factory Settings", icon: Settings },
      ],
    },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col h-screen select-none shrink-0 shadow-xs">
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-slate-200 bg-slate-50/50">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black shadow-sm">
          <Zap className="w-5 h-5 fill-white text-white" />
        </div>
        <div>
          <span className="font-extrabold text-base tracking-wider text-slate-900">
            INDUS<span className="text-blue-600">PILOT</span>
          </span>
          <span className="block text-[9px] uppercase tracking-widest text-slate-500 font-semibold">
            Tech4Bharat 2026 • PS 4.1
          </span>
        </div>
      </div>

      {/* Navigation Sections */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {navSections.map((sec, idx) => (
          <div key={idx}>
            <div className="px-3 mb-2 text-[10px] font-bold tracking-wider text-slate-400 uppercase">
              {sec.title}
            </div>
            <div className="space-y-1">
              {sec.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                      isActive
                        ? "bg-blue-50 text-blue-700 font-semibold border border-blue-200 shadow-xs"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon
                        className={`w-4 h-4 ${
                          isActive ? "text-blue-600" : "text-slate-400"
                        }`}
                      />
                      <span>{item.label}</span>
                    </div>

                    {item.badge && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-600 font-mono">
                        {item.badge}
                      </span>
                    )}

                    {item.badgeCount !== undefined && (
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full text-white ${item.badgeColor}`}
                      >
                        {item.badgeCount}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Footer System Status */}
      <div className="p-3 border-t border-slate-200 bg-slate-50/50 text-[11px] text-slate-500">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 text-slate-700 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Backend API Online
          </span>
          <span className="font-mono text-[10px] text-slate-400">v1.0.0</span>
        </div>
      </div>
    </aside>
  );
}

