"use client";

import React, { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import DashboardView from "@/components/views/DashboardView";
import QuotationUploadView from "@/components/views/QuotationUploadView";
import SupplierCompareView from "@/components/views/SupplierCompareView";
import NegotiationView from "@/components/views/NegotiationView";
import OptimizationView from "@/components/views/OptimizationView";
import BOMManagerView from "@/components/views/BOMManagerView";
import InventoryView from "@/components/views/InventoryView";
import CostingEngineView from "@/components/views/CostingEngineView";
import CustomerQuotesView from "@/components/views/CustomerQuotesView";
import SuppliersView from "@/components/views/SuppliersView";
import CopilotView from "@/components/views/CopilotView";
import ApprovalCentreView from "@/components/views/ApprovalCentreView";
import AnalyticsView from "@/components/views/AnalyticsView";
import ScenarioView from "@/components/views/ScenarioView";
import SettingsView from "@/components/views/SettingsView";
import { getDashboardMetrics, getApprovals } from "@/lib/api";

export default function Home({ initialTab = "dashboard" }: { initialTab?: string }) {
  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const [metrics, setMetrics] = useState<any>(null);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshData = async () => {
    try {
      const m = await getDashboardMetrics();
      setMetrics(m);
      if (m && typeof m.pending_approvals_count === "number") {
        setPendingApprovalsCount(m.pending_approvals_count);
      }
    } catch (err) {
      console.error("Dashboard metrics error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      const path = window.location.pathname.replace(/^\//, "").split("/")[0];
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab") || (path ? path : null);
      const validTabs = [
        "copilot", "dashboard", "bom", "inventory", "compare",
        "optimizer", "costing", "customer-quotes", "negotiation",
        "approvals", "quotations", "suppliers", "analytics", "scenarios", "settings"
      ];
      if (tabParam && validTabs.includes(tabParam)) {
        setActiveTab(tabParam);
      }
    }
    refreshData();
  }, [initialTab]);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900 font-sans">
      {/* Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingApprovalsCount={pendingApprovalsCount}
        shortagesCount={metrics?.material_shortages_count || 1}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <Header
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          pendingApprovalsCount={pendingApprovalsCount}
          onRefresh={refreshData}
        />

        {/* Scrollable Workspace */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-slate-50">
          <div className="max-w-7xl mx-auto">
            {activeTab === "dashboard" && (
              <DashboardView metrics={metrics} setActiveTab={setActiveTab} />
            )}
            {activeTab === "quotations" && (
              <QuotationUploadView onQuotationConfirmed={refreshData} />
            )}
            {activeTab === "compare" && (
              <SupplierCompareView setActiveTab={setActiveTab} />
            )}
            {activeTab === "negotiation" && (
              <NegotiationView onApprovalNeeded={refreshData} />
            )}
            {activeTab === "optimizer" && (
              <OptimizationView setActiveTab={setActiveTab} />
            )}
            {activeTab === "bom" && (
              <BOMManagerView setActiveTab={setActiveTab} />
            )}
            {activeTab === "inventory" && (
              <InventoryView setActiveTab={setActiveTab} />
            )}
            {activeTab === "costing" && (
              <CostingEngineView setActiveTab={setActiveTab} />
            )}
            {activeTab === "customer-quotes" && <CustomerQuotesView />}
            {activeTab === "suppliers" && <SuppliersView />}
            {activeTab === "copilot" && (
              <CopilotView setActiveTab={setActiveTab} />
            )}
            {activeTab === "approvals" && (
              <ApprovalCentreView onApprovalProcessed={refreshData} />
            )}
            {activeTab === "analytics" && <AnalyticsView metrics={metrics} />}
            {activeTab === "scenario" && (
              <ScenarioView setActiveTab={setActiveTab} />
            )}
            {activeTab === "settings" && <SettingsView onRefresh={refreshData} />}
          </div>
        </main>
      </div>
    </div>
  );
}
