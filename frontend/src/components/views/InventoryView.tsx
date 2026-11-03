"use client";

import React, { useState, useEffect } from "react";
import {
  Boxes,
  AlertTriangle,
  CheckCircle2,
  MapPin,
  Search,
  ArrowRight,
  ArrowDownLeft,
  ArrowUpRight,
  SlidersHorizontal,
  History,
  ShieldAlert,
  RefreshCw,
  Plus,
  Lock,
  Unlock,
  DollarSign,
  X
} from "lucide-react";
import {
  getInventoryLedger,
  getInventoryAlerts,
  getInventoryMovements,
  receiveStock,
  issueStock,
  reserveStock,
  releaseReservation,
  adjustStock,
  getMaterials
} from "@/lib/api";

export default function InventoryView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  const [inventory, setInventory] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [movements, setMovements] = useState<any[]>([]);
  const [materials, setMaterials] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [loading, setLoading] = useState(true);

  // Active drawers & modals
  const [activeTabSub, setActiveTabSub] = useState<"LEDGER" | "MOVEMENTS" | "ALERTS">("LEDGER");
  const [receiveModalOpen, setReceiveModalOpen] = useState(false);
  const [issueModalOpen, setIssueModalOpen] = useState(false);
  const [adjustModalOpen, setAdjustModalOpen] = useState(false);
  const [reserveModalOpen, setReserveModalOpen] = useState(false);

  // Form states
  const [selectedMaterialId, setSelectedMaterialId] = useState("");
  const [formQty, setFormQty] = useState<number>(100);
  const [formCost, setFormCost] = useState<number>(315);
  const [formRef, setFormRef] = useState("");
  const [formDest, setFormDest] = useState("CNC Laser Bay 1");
  const [formReason, setFormReason] = useState("Monthly Physical Audit Count");
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [invData, alertsData, movData, matsData] = await Promise.all([
        getInventoryLedger(),
        getInventoryAlerts().catch(() => ({ alerts: [] })),
        getInventoryMovements(undefined, 50).catch(() => []),
        getMaterials().catch(() => [])
      ]);
      setInventory(invData || []);
      setAlerts(alertsData?.alerts || []);
      setMovements(movData || []);
      setMaterials(matsData || []);
      if (matsData && matsData.length > 0) {
        setSelectedMaterialId(matsData[0].id);
      }
    } catch (err) {
      console.error("Failed to load inventory:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleReceiveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setActionError(null);
      await receiveStock({
        material_id: selectedMaterialId,
        quantity: formQty,
        unit_cost: formCost,
        reference_id: formRef || `PO-${Date.now().toString().slice(-6)}`,
        destination: formDest
      });
      setReceiveModalOpen(false);
      await loadData();
    } catch (err: any) {
      setActionError(err.message || "Failed to receive stock");
    } finally {
      setSubmitting(false);
    }
  };

  const handleIssueSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setActionError(null);
      await issueStock({
        material_id: selectedMaterialId,
        quantity: formQty,
        destination: formDest,
        allow_negative_stock: false
      });
      setIssueModalOpen(false);
      await loadData();
    } catch (err: any) {
      setActionError(err.message || "Insufficient unreserved stock");
    } finally {
      setSubmitting(false);
    }
  };

  const handleAdjustSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setActionError(null);
      await adjustStock({
        material_id: selectedMaterialId,
        new_physical_stock: formQty,
        reason: formReason
      });
      setAdjustModalOpen(false);
      await loadData();
    } catch (err: any) {
      setActionError(err.message || "Failed to adjust stock");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReserveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setActionError(null);
      await reserveStock({
        material_id: selectedMaterialId,
        quantity: formQty,
        production_job_id: formRef || "JOB-2026-0001"
      });
      setReserveModalOpen(false);
      await loadData();
    } catch (err: any) {
      setActionError(err.message || "Failed to reserve stock");
    } finally {
      setSubmitting(false);
    }
  };

  const categories = ["ALL", ...Array.from(new Set(inventory.map((i) => i.category).filter(Boolean)))];

  const filtered = inventory.filter((i) => {
    const matchesSearch =
      i.material_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      i.material_code.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCat = categoryFilter === "ALL" || i.category === categoryFilter;
    return matchesSearch && matchesCat;
  });

  const criticalShortagesCount = inventory.filter((i) => i.status === "CRITICAL_SHORTAGE").length;
  const reorderRequiredCount = inventory.filter((i) => i.status === "REORDER_REQUIRED").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Boxes className="w-5 h-5 text-blue-600" />
            <span>Warehouse Raw Material Stock & Perpetual Ledger</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Physical on-hand balances, job-allocated reservations, moving average unit costs, and automated shortage detection.
          </p>
        </div>

        {/* Operational Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setActionError(null);
              setReceiveModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 transition-all shadow-xs"
          >
            <ArrowDownLeft className="w-3.5 h-3.5" />
            <span>Receive Stock</span>
          </button>

          <button
            onClick={() => {
              setActionError(null);
              setIssueModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 transition-all shadow-xs"
          >
            <ArrowUpRight className="w-3.5 h-3.5" />
            <span>Issue Stock</span>
          </button>

          <button
            onClick={() => {
              setActionError(null);
              setReserveModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-bold hover:bg-indigo-100 transition-all shadow-xs"
          >
            <Lock className="w-3.5 h-3.5" />
            <span>Reserve</span>
          </button>

          <button
            onClick={() => {
              setActionError(null);
              setAdjustModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-all shadow-xs"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Stock Audit</span>
          </button>
        </div>
      </div>

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <span className="text-slate-500 block text-[10px] uppercase font-bold">Managed Material SKUs</span>
          <span className="text-xl font-black text-slate-900 mt-1 block font-mono">
            {inventory.length} Materials
          </span>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Across metals, fasteners & consumables</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <span className="text-slate-500 block text-[10px] uppercase font-bold">Stock Health</span>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xl font-black text-emerald-700 font-mono">
              {inventory.filter((i) => i.status === "HEALTHY").length} Healthy
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Within safe operational inventory buffers</span>
        </div>

        <div
          className={`p-4 rounded-xl border shadow-xs ${
            reorderRequiredCount > 0 ? "bg-amber-50 border-amber-200" : "bg-white border-slate-200"
          }`}
        >
          <span className="text-slate-500 block text-[10px] uppercase font-bold">Reorder Point Triggers</span>
          <span
            className={`text-xl font-black mt-1 block font-mono ${
              reorderRequiredCount > 0 ? "text-amber-700" : "text-slate-900"
            }`}
          >
            {reorderRequiredCount} SKUs Below Reorder
          </span>
          <span className="text-[10px] text-slate-600 mt-0.5 block">Lead time replenishment recommended</span>
        </div>

        <div
          className={`p-4 rounded-xl border shadow-xs ${
            criticalShortagesCount > 0 ? "bg-red-50 border-red-200" : "bg-white border-slate-200"
          }`}
        >
          <span className="text-slate-500 block text-[10px] uppercase font-bold">Critical Shortages</span>
          <span
            className={`text-xl font-black mt-1 block font-mono ${
              criticalShortagesCount > 0 ? "text-red-700" : "text-emerald-700"
            }`}
          >
            {criticalShortagesCount} Stockouts
          </span>
          <span className="text-[10px] text-slate-600 mt-0.5 block">
            {criticalShortagesCount > 0 ? "Blocks active production jobs" : "Zero line-stop risks"}
          </span>
        </div>
      </div>

      {/* Sub-navigation tabs: Ledger vs Movements vs Alerts */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-2 text-xs">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTabSub("LEDGER")}
            className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
              activeTabSub === "LEDGER"
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            Inventory Stock Balances ({filtered.length})
          </button>
          <button
            onClick={() => setActiveTabSub("MOVEMENTS")}
            className={`px-3 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 ${
              activeTabSub === "MOVEMENTS"
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>Perpetual Movement Audit ({movements.length})</span>
          </button>
          <button
            onClick={() => setActiveTabSub("ALERTS")}
            className={`px-3 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 ${
              activeTabSub === "ALERTS"
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
            <span>Operational Alerts ({alerts.length})</span>
          </button>
        </div>

        {activeTabSub === "LEDGER" && (
          <div className="flex items-center gap-3">
            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-700 font-semibold"
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c === "ALL" ? "All Categories" : c}
                </option>
              ))}
            </select>

            {/* Search */}
            <div className="relative text-xs">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2" />
              <input
                type="text"
                placeholder="Search material SKU or name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-1 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 w-52"
              />
            </div>
          </div>
        )}
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200 shadow-xs">
          Loading inventory records...
        </div>
      ) : activeTabSub === "LEDGER" ? (
        /* 1. Perpetual Inventory Ledger Table */
        <div className="overflow-x-auto border border-slate-200 rounded-xl bg-white shadow-xs">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-700 font-bold uppercase text-[10px] border-b border-slate-200">
              <tr>
                <th className="p-3.5">Material SKU / Name</th>
                <th className="p-3.5">Warehouse Bay</th>
                <th className="p-3.5 text-right">Physical On-Hand</th>
                <th className="p-3.5 text-right">Reserved (Jobs)</th>
                <th className="p-3.5 text-right">Available Stock</th>
                <th className="p-3.5 text-right">Safety Buffer</th>
                <th className="p-3.5 text-right">Reorder Level</th>
                <th className="p-3.5 text-right">Moving Avg Cost</th>
                <th className="p-3.5 text-center">Stock Status</th>
                <th className="p-3.5 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filtered.map((item) => {
                const isShortage = item.status === "CRITICAL_SHORTAGE";
                const isReorder = item.status === "REORDER_REQUIRED";
                return (
                  <tr key={item.material_id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-3.5">
                      <div className="font-bold text-slate-900">{item.material_name}</div>
                      <div className="text-[10px] text-blue-600 font-mono">{item.material_code}</div>
                    </td>
                    <td className="p-3.5 text-slate-600">
                      <div className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span>{item.warehouse_location || "Central Storage"}</span>
                      </div>
                    </td>
                    <td className="p-3.5 text-right font-mono font-bold text-slate-800">
                      {item.current_stock} {item.unit}
                    </td>
                    <td className="p-3.5 text-right font-mono text-slate-500">
                      {item.reserved_stock > 0 ? (
                        <span className="text-amber-700 font-bold">{item.reserved_stock} {item.unit}</span>
                      ) : (
                        `0.0 ${item.unit}`
                      )}
                    </td>
                    <td className="p-3.5 text-right font-mono font-black text-slate-900">
                      {item.available_stock} {item.unit}
                    </td>
                    <td className="p-3.5 text-right font-mono text-slate-500">
                      {item.safety_stock} {item.unit}
                    </td>
                    <td className="p-3.5 text-right font-mono text-slate-500">
                      {item.reorder_level} {item.unit}
                    </td>
                    <td className="p-3.5 text-right font-mono text-slate-700">
                      ₹{item.moving_average_cost?.toFixed(2) || "315.00"}
                    </td>
                    <td className="p-3.5 text-center">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          isShortage
                            ? "bg-red-50 text-red-700 border-red-200"
                            : isReorder
                            ? "bg-amber-50 text-amber-700 border-amber-200"
                            : "bg-emerald-50 text-emerald-700 border-emerald-200"
                        }`}
                      >
                        {item.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="p-3.5 text-center">
                      {isShortage || isReorder ? (
                        <button
                          onClick={() => setActiveTab("compare")}
                          className="px-2 py-1 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded text-[10px] font-bold border border-blue-200"
                        >
                          Source Quotes
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-400">Normal</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : activeTabSub === "MOVEMENTS" ? (
        /* 2. Perpetual Movement Audit Ledger */
        <div className="overflow-x-auto border border-slate-200 rounded-xl bg-white shadow-xs">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-700 font-bold uppercase text-[10px] border-b border-slate-200">
              <tr>
                <th className="p-3.5">Timestamp</th>
                <th className="p-3.5">Movement Type</th>
                <th className="p-3.5 text-right">Quantity</th>
                <th className="p-3.5">Unit Cost</th>
                <th className="p-3.5">Source / Destination</th>
                <th className="p-3.5">Reference ID</th>
                <th className="p-3.5">Operator</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {movements.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-500">
                    No movements recorded yet. Perform a stock receipt or issue above to generate transactions.
                  </td>
                </tr>
              ) : (
                movements.map((m: any) => (
                  <tr key={m.id} className="hover:bg-slate-50">
                    <td className="p-3.5 text-slate-600 font-mono text-[11px]">
                      {m.created_at ? new Date(m.created_at).toLocaleString() : "Recent"}
                    </td>
                    <td className="p-3.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          m.movement_type === "RECEIPT"
                            ? "bg-emerald-100 text-emerald-800"
                            : m.movement_type === "ISSUE"
                            ? "bg-blue-100 text-blue-800"
                            : m.movement_type === "RESERVATION"
                            ? "bg-indigo-100 text-indigo-800"
                            : "bg-slate-100 text-slate-800"
                        }`}
                      >
                        {m.movement_type}
                      </span>
                    </td>
                    <td className="p-3.5 text-right font-mono font-bold text-slate-900">
                      {m.movement_type === "ISSUE" ? `-${m.quantity}` : `+${m.quantity}`} {m.unit || "kg"}
                    </td>
                    <td className="p-3.5 font-mono text-slate-700">
                      {m.unit_cost ? `₹${Number(m.unit_cost).toFixed(2)}` : "—"}
                    </td>
                    <td className="p-3.5 text-slate-600">{m.destination || m.source || "Warehouse Bay"}</td>
                    <td className="p-3.5 font-mono text-[11px] text-blue-600">{m.reference_id || "PO-DIRECT"}</td>
                    <td className="p-3.5 text-slate-600">{m.user_id || "Shopfloor Operator"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        /* 3. Operational Inventory Alerts */
        <div className="space-y-3">
          {alerts.length === 0 ? (
            <div className="p-8 bg-white border border-slate-200 rounded-xl text-center text-xs text-slate-500">
              All materials are currently above safety thresholds. Zero alerts pending.
            </div>
          ) : (
            alerts.map((a: any, idx: number) => (
              <div
                key={idx}
                className={`p-4 rounded-xl border flex items-start justify-between gap-4 ${
                  a.severity === "CRITICAL"
                    ? "bg-red-50 border-red-200 text-red-900"
                    : "bg-amber-50 border-amber-200 text-amber-900"
                }`}
              >
                <div className="flex items-start gap-3">
                  <AlertTriangle
                    className={`w-5 h-5 mt-0.5 shrink-0 ${
                      a.severity === "CRITICAL" ? "text-red-600" : "text-amber-600"
                    }`}
                  />
                  <div>
                    <div className="font-bold text-xs flex items-center gap-2">
                      <span>{a.material_code}</span>
                      <span className="px-1.5 py-0.2 rounded text-[9px] bg-white border font-bold">
                        {a.alert_type}
                      </span>
                    </div>
                    <p className="text-xs mt-1 text-slate-700">{a.message}</p>
                  </div>
                </div>

                <button
                  onClick={() => setActiveTab("compare")}
                  className="px-3 py-1.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-50 text-xs font-bold text-slate-800 shadow-xs shrink-0"
                >
                  Create Requisition
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {/* MODAL 1: Receive Stock */}
      {receiveModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 space-y-4 border border-slate-200 shadow-xl">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <ArrowDownLeft className="w-5 h-5 text-emerald-600" />
                <h3 className="font-bold text-sm text-slate-900">Receive Inbound Raw Material</h3>
              </div>
              <button onClick={() => setReceiveModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {actionError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 font-medium">
                {actionError}
              </div>
            )}

            <form onSubmit={handleReceiveSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Raw Material</label>
                <select
                  value={selectedMaterialId}
                  onChange={(e) => setSelectedMaterialId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold text-slate-900"
                >
                  {materials.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.material_code || m.code} — {m.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Received Quantity</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={formQty}
                    onChange={(e) => setFormQty(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Unit Cost (₹)</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={formCost}
                    onChange={(e) => setFormCost(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">PO Reference / Inward Challan</label>
                <input
                  type="text"
                  placeholder="PO-2026-OCT-881"
                  value={formRef}
                  onChange={(e) => setFormRef(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-900"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Destination Storage Location</label>
                <input
                  type="text"
                  placeholder="Raw Material Bay B3"
                  value={formDest}
                  onChange={(e) => setFormDest(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setReceiveModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 font-bold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-emerald-600 text-white font-bold hover:bg-emerald-700 disabled:opacity-50"
                >
                  {submitting ? "Posting..." : "Confirm Inward Stock"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Issue Stock */}
      {issueModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 space-y-4 border border-slate-200 shadow-xl">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <ArrowUpRight className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-sm text-slate-900">Issue Stock to Production</h3>
              </div>
              <button onClick={() => setIssueModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {actionError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 font-medium">
                {actionError}
              </div>
            )}

            <form onSubmit={handleIssueSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Raw Material</label>
                <select
                  value={selectedMaterialId}
                  onChange={(e) => setSelectedMaterialId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold text-slate-900"
                >
                  {materials.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.material_code || m.code} — {m.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Issue Quantity</label>
                <input
                  type="number"
                  step="any"
                  required
                  value={formQty}
                  onChange={(e) => setFormQty(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Issuing Destination / Machine</label>
                <input
                  type="text"
                  placeholder="CNC Laser Cutting Bed 01"
                  value={formDest}
                  onChange={(e) => setFormDest(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setIssueModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 font-bold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 disabled:opacity-50"
                >
                  {submitting ? "Processing..." : "Issue Material"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: Stock Adjustment (Audit) */}
      {adjustModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 space-y-4 border border-slate-200 shadow-xl">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="w-5 h-5 text-slate-800" />
                <h3 className="font-bold text-sm text-slate-900">Physical Inventory Stock Audit</h3>
              </div>
              <button onClick={() => setAdjustModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {actionError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 font-medium">
                {actionError}
              </div>
            )}

            <form onSubmit={handleAdjustSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Raw Material</label>
                <select
                  value={selectedMaterialId}
                  onChange={(e) => setSelectedMaterialId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold text-slate-900"
                >
                  {materials.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.material_code || m.code} — {m.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Actual Physical Counted Stock</label>
                <input
                  type="number"
                  step="any"
                  required
                  value={formQty}
                  onChange={(e) => setFormQty(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Audit Reconciliation Reason</label>
                <input
                  type="text"
                  placeholder="Monthly physical cycle count variance"
                  value={formReason}
                  onChange={(e) => setFormReason(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setAdjustModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 font-bold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-slate-900 text-white font-bold hover:bg-slate-800 disabled:opacity-50"
                >
                  {submitting ? "Reconciling..." : "Save Audit Count"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: Reserve Stock */}
      {reserveModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 space-y-4 border border-slate-200 shadow-xl">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <Lock className="w-5 h-5 text-indigo-600" />
                <h3 className="font-bold text-sm text-slate-900">Reserve Stock for Production Job</h3>
              </div>
              <button onClick={() => setReserveModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {actionError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 font-medium">
                {actionError}
              </div>
            )}

            <form onSubmit={handleReserveSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Raw Material</label>
                <select
                  value={selectedMaterialId}
                  onChange={(e) => setSelectedMaterialId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold text-slate-900"
                >
                  {materials.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.material_code || m.code} — {m.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Reservation Quantity</label>
                <input
                  type="number"
                  step="any"
                  required
                  value={formQty}
                  onChange={(e) => setFormQty(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Production Job Reference</label>
                <input
                  type="text"
                  placeholder="JOB-2026-0001"
                  value={formRef}
                  onChange={(e) => setFormRef(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-900"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setReserveModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 font-bold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 text-white font-bold hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submitting ? "Reserving..." : "Lock Stock"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
