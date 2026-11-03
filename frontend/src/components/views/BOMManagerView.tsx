"use client";

import React, { useState, useEffect } from "react";
import {
  Layers,
  Boxes,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  Plus,
  GitCompare,
  ShieldCheck,
  FileText,
  Percent,
  SlidersHorizontal,
  ChevronDown,
  Info,
  X
} from "lucide-react";
import {
  getProductsDetailed,
  getBOMs,
  explodeBOM,
  validateBOM,
  compareBOMs,
  createBOMRevision,
  getMaterials
} from "@/lib/api";

export default function BOMManagerView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  const [products, setProducts] = useState<any[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [boms, setBoms] = useState<any[]>([]);
  const [selectedBomId, setSelectedBomId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState<number>(500);
  const [explosionResult, setExplosionResult] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [exploding, setExploding] = useState<boolean>(false);

  // Validation modal state
  const [validationModalOpen, setValidationModalOpen] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [validating, setValidating] = useState(false);

  // Compare revisions state
  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [compareBom1, setCompareBom1] = useState<string>("");
  const [compareBom2, setCompareBom2] = useState<string>("");
  const [comparisonDiff, setComparisonDiff] = useState<any>(null);
  const [comparing, setComparing] = useState(false);

  // New Revision modal state
  const [revisionModalOpen, setRevisionModalOpen] = useState(false);
  const [newVersionLabel, setNewVersionLabel] = useState("");
  const [revisionNotes, setRevisionNotes] = useState("");
  const [setAsActive, setSetAsActive] = useState(true);
  const [creatingRevision, setCreatingRevision] = useState(false);

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    if (selectedProductId) {
      loadBOMsForProduct(selectedProductId);
    }
  }, [selectedProductId]);

  useEffect(() => {
    if (selectedProductId) {
      runExplosion(selectedProductId, quantity, selectedBomId || undefined);
    }
  }, [selectedProductId, selectedBomId, quantity]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const data = await getProductsDetailed();
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

  const loadBOMsForProduct = async (prodId: string) => {
    try {
      const bomList = await getBOMs(prodId);
      setBoms(bomList);
      const active = bomList.find((b: any) => b.is_active);
      setSelectedBomId(active ? active.id : (bomList.length > 0 ? bomList[0].id : null));
    } catch (err) {
      console.error("Failed to load BOMs:", err);
    }
  };

  const runExplosion = async (prodId: string, qty: number, bomId?: string) => {
    try {
      setExploding(true);
      const res = await explodeBOM(prodId, qty, undefined, bomId);
      setExplosionResult(res);
    } catch (err) {
      console.error("BOM explosion failed:", err);
    } finally {
      setExploding(false);
    }
  };

  const handleValidate = async () => {
    if (!selectedBomId) return;
    try {
      setValidating(true);
      const res = await validateBOM(selectedBomId);
      setValidationResult(res);
      setValidationModalOpen(true);
    } catch (err) {
      console.error("Validation error:", err);
    } finally {
      setValidating(false);
    }
  };

  const handleOpenCompare = () => {
    if (boms.length >= 2) {
      setCompareBom1(boms[0].id);
      setCompareBom2(boms[1].id);
    } else if (boms.length === 1) {
      setCompareBom1(boms[0].id);
      setCompareBom2(boms[0].id);
    }
    setComparisonDiff(null);
    setCompareModalOpen(true);
  };

  const handleRunCompare = async () => {
    if (!compareBom1 || !compareBom2) return;
    try {
      setComparing(true);
      const diff = await compareBOMs(compareBom1, compareBom2);
      setComparisonDiff(diff);
    } catch (err) {
      console.error("Failed to compare BOMs:", err);
    } finally {
      setComparing(false);
    }
  };

  const handleCreateRevision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBomId || !newVersionLabel) return;
    try {
      setCreatingRevision(true);
      await createBOMRevision(selectedBomId, {
        new_version_label: newVersionLabel,
        revision_notes: revisionNotes,
        set_as_active: setAsActive
      });
      setRevisionModalOpen(false);
      setNewVersionLabel("");
      setRevisionNotes("");
      if (selectedProductId) {
        await loadBOMsForProduct(selectedProductId);
      }
    } catch (err) {
      console.error("Failed to create revision:", err);
    } finally {
      setCreatingRevision(false);
    }
  };

  const activeProduct = products.find((p) => p.id === selectedProductId);
  const activeBom = boms.find((b) => b.id === selectedBomId);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-600" />
            <span>Manufacturing Bill of Materials (BOM) & Revisions</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Engineering structure, scrap allowances (additive vs yield), live stock netting, and multi-version revision control.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleValidate}
            disabled={validating || !selectedBomId}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-bold hover:bg-emerald-100 transition-all shadow-xs"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>{validating ? "Validating..." : "Validate BOM"}</span>
          </button>

          <button
            onClick={handleOpenCompare}
            disabled={boms.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-bold hover:bg-indigo-100 transition-all shadow-xs"
          >
            <GitCompare className="w-3.5 h-3.5" />
            <span>Compare Revisions</span>
          </button>

          <button
            onClick={() => setRevisionModalOpen(true)}
            disabled={!selectedBomId}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 transition-all shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Revision</span>
          </button>
        </div>
      </div>

      {/* Control Bar: Product Selector, BOM Selector, Batch Quantity */}
      <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Product Dropdown */}
        <div>
          <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
            Manufacturing Product
          </label>
          <select
            value={selectedProductId || ""}
            onChange={(e) => setSelectedProductId(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500"
          >
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code} — {p.name}
              </option>
            ))}
          </select>
          {activeProduct && (
            <div className="mt-1 text-[10px] text-slate-500 flex items-center gap-2">
              <span>Process: {activeProduct.manufacturing_process || "Fabrication"}</span>
              <span>•</span>
              <span>Base Unit: {activeProduct.base_unit || "units"}</span>
            </div>
          )}
        </div>

        {/* BOM Version Selector */}
        <div>
          <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
            BOM Version & Revision
          </label>
          <select
            value={selectedBomId || ""}
            onChange={(e) => setSelectedBomId(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500"
          >
            {boms.map((b) => (
              <option key={b.id} value={b.id}>
                {b.version} ({b.revision_status || (b.is_active ? "ACTIVE" : "SUPERSEDED")}) — {b.name}
              </option>
            ))}
          </select>
          {activeBom && (
            <div className="mt-1 text-[10px] flex items-center gap-2">
              <span
                className={`font-bold px-1.5 py-0.2 rounded text-[9px] ${
                  activeBom.is_active
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-slate-100 text-slate-600"
                }`}
              >
                {activeBom.is_active ? "ACTIVE PRODUCTION" : activeBom.revision_status || "HISTORICAL"}
              </span>
              <span className="text-slate-500">Method: {activeBom.scrap_allowance_method || "ADDITIVE_SCRAP"}</span>
            </div>
          )}
        </div>

        {/* Production Batch Size */}
        <div>
          <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
            Batch Production Run
          </label>
          <div className="flex items-center gap-1.5">
            {[100, 250, 500, 1000].map((qty) => (
              <button
                key={qty}
                onClick={() => setQuantity(qty)}
                className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                  quantity === qty
                    ? "bg-blue-600 text-white border-blue-600 shadow-xs"
                    : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                }`}
              >
                {qty}
              </button>
            ))}
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-20 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-mono font-bold text-center text-slate-900"
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
          Loading Bill of Materials...
        </div>
      ) : !explosionResult ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
          No BOM records found for the selected product.
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
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Planned Batch</span>
              <span className="text-xl font-black text-slate-900 mt-1 block font-mono">
                {explosionResult.production_quantity} {activeProduct?.base_unit || "Units"}
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
              <span className="text-[10px] text-slate-500 mt-0.5 block">
                Method: {activeBom?.scrap_allowance_method || "ADDITIVE_SCRAP"}
              </span>
            </div>

            <div
              className={`p-4 rounded-xl border shadow-xs ${
                explosionResult.shortages_count > 0
                  ? "bg-red-50 border-red-200"
                  : "bg-emerald-50 border-emerald-200"
              }`}
            >
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Warehouse Netting</span>
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
                  : "Fully Covered by Unreserved Stock"}
              </span>
            </div>
          </div>

          {/* Exploded Components Table */}
          <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Component Hierarchy & Warehouse Allocation</h3>
                <p className="text-[11px] text-slate-500">
                  Shows unit consumption, scrap allowances, warehouse physical stock, and procurement shortages.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveTab("inventory")}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-all"
                >
                  <Boxes className="w-3.5 h-3.5" />
                  <span>View Inventory Ledger</span>
                </button>
                <button
                  onClick={() => setActiveTab("compare")}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-xs font-bold hover:bg-blue-100 transition-all"
                >
                  <span>Compare Sourcing Quotes</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-bold uppercase text-[10px] border-b border-slate-200">
                  <tr>
                    <th className="p-3">Component / Material</th>
                    <th className="p-3">Process Stage</th>
                    <th className="p-3 text-right">Net Qty / Unit</th>
                    <th className="p-3 text-right">Scrap %</th>
                    <th className="p-3 text-right">Total Gross Req.</th>
                    <th className="p-3 text-right">Physical Stock</th>
                    <th className="p-3 text-right">Reserved</th>
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
                        <td className="p-3 text-slate-600">{c.process_stage || "General Assembly"}</td>
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
                          {inv ? `${inv.current_stock} ${c.unit}` : "N/A"}
                        </td>
                        <td className="p-3 text-right font-mono text-slate-500">
                          {inv ? `${inv.reserved_stock} ${c.unit}` : "N/A"}
                        </td>
                        <td className="p-3 text-right font-mono font-bold text-slate-800">
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

      {/* MODAL 1: BOM Validation Results */}
      {validationModalOpen && validationResult && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 space-y-4 border border-slate-200 shadow-xl">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck
                  className={`w-5 h-5 ${
                    validationResult.is_valid ? "text-emerald-600" : "text-amber-600"
                  }`}
                />
                <h3 className="font-bold text-sm text-slate-900">
                  BOM Engineering Validation Report
                </h3>
              </div>
              <button
                onClick={() => setValidationModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <span className="font-medium text-slate-700">Validation Status</span>
                <span
                  className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                    validationResult.is_valid
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-red-100 text-red-800"
                  }`}
                >
                  {validationResult.is_valid ? "PASSED (Ready for Production)" : "ERRORS DETECTED"}
                </span>
              </div>

              {validationResult.errors?.length > 0 && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg space-y-1">
                  <div className="font-bold text-red-800 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Blocking Errors:</span>
                  </div>
                  <ul className="list-disc pl-4 text-red-700 space-y-0.5">
                    {validationResult.errors.map((e: string, idx: number) => (
                      <li key={idx}>{e}</li>
                    ))}
                  </ul>
                </div>
              )}

              {validationResult.warnings?.length > 0 && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-1">
                  <div className="font-bold text-amber-800 flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5" />
                    <span>Engineering Warnings:</span>
                  </div>
                  <ul className="list-disc pl-4 text-amber-700 space-y-0.5">
                    {validationResult.warnings.map((w: string, idx: number) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {validationResult.is_valid && validationResult.warnings?.length === 0 && (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <span>
                    BOM items, material specifications, and scrap allowances have passed all engineering integrity checks.
                  </span>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setValidationModalOpen(false)}
                className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-slate-800"
              >
                Close Report
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Compare Revisions */}
      {compareModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-2xl w-full p-6 space-y-4 border border-slate-200 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <GitCompare className="w-5 h-5 text-indigo-600" />
                <h3 className="font-bold text-sm text-slate-900">
                  Side-by-Side BOM Revision Comparison
                </h3>
              </div>
              <button
                onClick={() => setCompareModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Baseline Revision</label>
                <select
                  value={compareBom1}
                  onChange={(e) => setCompareBom1(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold text-slate-900"
                >
                  {boms.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.version} ({b.name})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Target Revision</label>
                <select
                  value={compareBom2}
                  onChange={(e) => setCompareBom2(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold text-slate-900"
                >
                  {boms.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.version} ({b.name})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleRunCompare}
                disabled={comparing || !compareBom1 || !compareBom2}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-bold hover:bg-indigo-700 disabled:opacity-50"
              >
                {comparing ? "Comparing Revisions..." : "Compute Differences"}
              </button>
            </div>

            {comparisonDiff && (
              <div className="mt-4 space-y-3 text-xs border-t pt-3">
                <div className="p-3 bg-slate-50 rounded-lg font-bold text-slate-800 flex justify-between">
                  <span>Comparison: {comparisonDiff.bom_1.version} vs {comparisonDiff.bom_2.version}</span>
                  <span className="text-slate-600">{comparisonDiff.differences.length} Differences Found</span>
                </div>

                {comparisonDiff.differences.length === 0 ? (
                  <div className="p-4 text-center text-slate-500">
                    The two revisions are identical in components, quantities, and scrap allowances.
                  </div>
                ) : (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-100 text-slate-700 font-bold uppercase text-[10px]">
                        <tr>
                          <th className="p-2.5">Material SKU</th>
                          <th className="p-2.5">Change Type</th>
                          <th className="p-2.5 text-right">{comparisonDiff.bom_1.version} Value</th>
                          <th className="p-2.5 text-right">{comparisonDiff.bom_2.version} Value</th>
                          <th className="p-2.5">Field Changed</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200">
                        {comparisonDiff.differences.map((d: any, idx: number) => (
                          <tr key={idx} className="hover:bg-slate-50">
                            <td className="p-2.5 font-mono font-bold text-slate-900">{d.material_code}</td>
                            <td className="p-2.5">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  d.change_type === "ADDED"
                                    ? "bg-emerald-100 text-emerald-800"
                                    : d.change_type === "REMOVED"
                                    ? "bg-red-100 text-red-800"
                                    : "bg-blue-100 text-blue-800"
                                }`}
                              >
                                {d.change_type}
                              </span>
                            </td>
                            <td className="p-2.5 text-right font-mono text-slate-600">
                              {d.old_value !== undefined ? String(d.old_value) : "—"}
                            </td>
                            <td className="p-2.5 text-right font-mono font-bold text-slate-900">
                              {d.new_value !== undefined ? String(d.new_value) : "—"}
                            </td>
                            <td className="p-2.5 text-slate-600">{d.field_changed || "Item"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL 3: Create Revision */}
      {revisionModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 space-y-4 border border-slate-200 shadow-xl">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <Plus className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-sm text-slate-900">
                  Create New BOM Engineering Revision
                </h3>
              </div>
              <button
                onClick={() => setRevisionModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateRevision} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  New Version Identifier (e.g., v1.1, v2.0)
                </label>
                <input
                  type="text"
                  required
                  placeholder="v2.0"
                  value={newVersionLabel}
                  onChange={(e) => setNewVersionLabel(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Engineering Change Notes / Reason
                </label>
                <textarea
                  rows={3}
                  placeholder="Optimised nesting layout, scrap allowance reduced from 5% to 3.5%."
                  value={revisionNotes}
                  onChange={(e) => setRevisionNotes(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="setActiveCheckbox"
                  checked={setAsActive}
                  onChange={(e) => setSetAsActive(e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="setActiveCheckbox" className="font-medium text-slate-700 cursor-pointer">
                  Set this revision as the active production BOM immediately
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setRevisionModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 font-bold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingRevision}
                  className="px-4 py-1.5 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 disabled:opacity-50"
                >
                  {creatingRevision ? "Creating Revision..." : "Save Revision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
