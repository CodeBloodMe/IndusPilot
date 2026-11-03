"use client";

import React, { useState, useEffect } from "react";
import {
  Layers,
  Boxes,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  Calculator,
} from "lucide-react";
import { getProducts, explodeBOM } from "@/lib/api";

export default function BOMManagerView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  const [products, setProducts] = useState<any[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState<number>(500);
  const [explosionResult, setExplosionResult] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    if (selectedProductId) {
      runExplosion(selectedProductId, quantity);
    }
  }, [selectedProductId, quantity]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const data = await getProducts();
      setProducts(data);
      if (data.length > 0) {
        setSelectedProductId(data[0].id);
      }
    } catch (err) {
      console.error("Failed to load products:", err);
    } finally {
      setLoading(false);
    }
  };

  const runExplosion = async (prodId: string, qty: number) => {
    try {
      const res = await explodeBOM(prodId, qty);
      setExplosionResult(res);
    } catch (err) {
      console.error("BOM explosion failed:", err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-600" />
            <span>Bill of Materials (BOM) & Inventory Netting Engine</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Explodes raw material assembly components, applies scrap/cutting wastage allowances,
            and nets requirements against warehouse stock.
          </p>
        </div>

        {/* Batch Quantity Selector */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-600 font-medium">Production Batch:</span>
          <div className="flex items-center gap-1 bg-slate-100 border border-slate-200 rounded-lg p-1">
            {[100, 250, 500, 1000].map((qty) => (
              <button
                key={qty}
                onClick={() => setQuantity(qty)}
                className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${
                  quantity === qty
                    ? "bg-blue-600 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {qty} Units
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
          Loading Bill of Materials...
        </div>
      ) : !explosionResult ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
          No BOM records found.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Summary KPIs Banner */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Finished Product</span>
              <span className="text-sm font-bold text-slate-900 mt-1 block truncate">
                {explosionResult.product.name}
              </span>
              <span className="text-[10px] text-blue-600 font-mono mt-0.5 block">
                Part #{explosionResult.product.code}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Planned Quantity</span>
              <span className="text-xl font-black text-slate-900 mt-1 block font-mono">
                {explosionResult.production_quantity} Units
              </span>
              <span className="text-[10px] text-slate-500 mt-0.5 block">
                {explosionResult.components_count} Active Components
              </span>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Total Gross Raw Mass</span>
              <span className="text-xl font-black text-slate-900 mt-1 block font-mono">
                {explosionResult.total_raw_mass_kg} kg
              </span>
              <span className="text-[10px] text-slate-500 mt-0.5 block">Includes 5% scrap yield loss</span>
            </div>

            <div
              className={`p-4 rounded-xl border shadow-xs ${
                explosionResult.shortages_count > 0
                  ? "bg-red-50 border-red-200"
                  : "bg-emerald-50 border-emerald-200"
              }`}
            >
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Net Shortage</span>
              <span
                className={`text-xl font-black mt-1 block font-mono ${
                  explosionResult.shortages_count > 0 ? "text-red-700" : "text-emerald-700"
                }`}
              >
                {explosionResult.total_shortage_mass_kg} kg
              </span>
              <span className="text-[10px] text-slate-600 mt-0.5 block">
                {explosionResult.shortages_count > 0
                  ? `${explosionResult.shortages_count} Material Requisitions Required`
                  : "Fully Covered by Stock"}
              </span>
            </div>
          </div>

          {/* Exploded Components Table */}
          <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-sm font-bold text-slate-900">Component Breakdown & Stock Netting</h3>
              <button
                onClick={() => setActiveTab("compare")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-xs font-bold hover:bg-blue-100 transition-all"
              >
                <span>Compare Sourcing Quotes</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-bold uppercase text-[10px] border-b border-slate-200">
                  <tr>
                    <th className="p-3">Component / Material</th>
                    <th className="p-3">Process Stage</th>
                    <th className="p-3 text-right">Unit Qty</th>
                    <th className="p-3 text-right">Scrap %</th>
                    <th className="p-3 text-right">Gross Needed</th>
                    <th className="p-3 text-right">Available Stock</th>
                    <th className="p-3 text-right">Net Shortage</th>
                    <th className="p-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {explosionResult.components?.map((c: any, i: number) => {
                    const inv = c.inventory_status;
                    const hasShortage = inv?.has_shortage;
                    return (
                      <tr key={i} className="hover:bg-slate-50">
                        <td className="p-3">
                          <div className="font-bold text-slate-900">{c.material_name}</div>
                          <div className="text-[10px] text-slate-500 font-mono">{c.material_code}</div>
                        </td>
                        <td className="p-3 text-slate-600">{c.process_stage}</td>
                        <td className="p-3 text-right font-mono text-slate-800">
                          {c.net_quantity_per_unit} {c.unit}
                        </td>
                        <td className="p-3 text-right font-mono text-amber-700 font-bold">
                          +{c.wastage_pct}%
                        </td>
                        <td className="p-3 text-right font-mono font-bold text-slate-900">
                          {c.total_gross_required} {c.unit}
                        </td>
                        <td className="p-3 text-right font-mono text-slate-700">
                          {inv ? `${inv.available_stock} ${c.unit}` : "N/A"}
                        </td>
                        <td className="p-3 text-right font-mono font-black">
                          {hasShortage ? (
                            <span className="text-red-700">
                              {inv.net_shortage} {c.unit}
                            </span>
                          ) : (
                            <span className="text-emerald-700">0.0 {c.unit}</span>
                          )}
                        </td>
                        <td className="p-3 text-center">
                          {hasShortage ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-50 text-red-700 border border-red-200">
                              Requisition Needed
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Covered
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

