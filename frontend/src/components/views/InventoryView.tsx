"use client";

import React, { useState, useEffect } from "react";
import {
  Boxes,
  AlertTriangle,
  CheckCircle2,
  MapPin,
  Search,
  ArrowRight,
} from "lucide-react";
import { getInventory } from "@/lib/api";

export default function InventoryView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  const [inventory, setInventory] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadInventory();
  }, []);

  const loadInventory = async () => {
    try {
      setLoading(true);
      const data = await getInventory();
      setInventory(data);
    } catch (err) {
      console.error("Failed to load inventory:", err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = inventory.filter(
    (i) =>
      i.material_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      i.material_code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Boxes className="w-5 h-5 text-blue-600" />
            <span>Warehouse Raw Material Stock & Shortage Ledger</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Physical stock balances, production job allocations, safety stock buffers, and reorder alerts.
          </p>
        </div>

        <div className="relative text-xs">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search material or code..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200 shadow-xs">
          Loading inventory records...
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200 shadow-xs">
          No inventory items found. Click "Seed Demo Data" to load standard inventory.
        </div>
      ) : (
        <div className="overflow-x-auto border border-slate-200 rounded-xl bg-white shadow-xs">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-700 font-bold uppercase text-[10px] border-b border-slate-200">
              <tr>
                <th className="p-3.5">Material SKU / Description</th>
                <th className="p-3.5">Location</th>
                <th className="p-3.5 text-right">Physical Stock</th>
                <th className="p-3.5 text-right">Reserved</th>
                <th className="p-3.5 text-right">Available Stock</th>
                <th className="p-3.5 text-right">Safety Buffer</th>
                <th className="p-3.5 text-right">Reorder Point</th>
                <th className="p-3.5 text-center">Status</th>
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
                    <td className="p-3.5 text-slate-600 flex items-center gap-1.5 pt-4">
                      <MapPin className="w-3.5 h-3.5 text-slate-400" />
                      <span>{item.warehouse_location}</span>
                    </td>
                    <td className="p-3.5 text-right font-mono font-bold text-slate-800">
                      {item.current_stock} {item.unit}
                    </td>
                    <td className="p-3.5 text-right font-mono text-slate-500">
                      {item.reserved_stock} {item.unit}
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
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

