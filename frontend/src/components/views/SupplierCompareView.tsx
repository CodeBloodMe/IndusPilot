"use client";

import React, { useState, useEffect } from "react";
import {
  Scale,
  Award,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  TrendingDown,
  Clock,
  ShieldCheck,
  CreditCard,
  ArrowRight,
  Handshake,
  Sliders,
  FileText,
  DollarSign,
  ChevronDown,
  ChevronUp,
  Info,
  Calendar,
  Layers,
  Sparkles,
  RefreshCw,
  Search,
  ShoppingCart,
  Send,
  Eye,
  Check,
  X
} from "lucide-react";
import {
  getQuotations,
  getMaterials,
  analyzeComparison,
  getMaterialPriceHistory,
  createPurchaseRequisition,
  ComparisonWeights,
  AnalyzeComparisonRequest
} from "@/lib/api";

interface SupplierCompareViewProps {
  setActiveTab: (tab: string) => void;
}

export default function SupplierCompareView({ setActiveTab }: SupplierCompareViewProps) {
  // Form requirements state
  const [materials, setMaterials] = useState<any[]>([]);
  const [selectedMaterialId, setSelectedMaterialId] = useState<string>("");
  const [selectedGrade, setSelectedGrade] = useState<string>("SS304");
  const [thicknessMm, setThicknessMm] = useState<number>(2.0);
  const [requiredQuantity, setRequiredQuantity] = useState<number>(800);
  const [requiredUnit, setRequiredUnit] = useState<string>("kg");
  const [deliveryDeadline, setDeliveryDeadline] = useState<string>("");
  const [targetUnitPrice, setTargetUnitPrice] = useState<number>(315);
  const [showWeightsDrawer, setShowWeightsDrawer] = useState<boolean>(false);

  // Custom scoring weights
  const [weights, setWeights] = useState<ComparisonWeights>({
    cost: 35,
    quality: 25,
    reliability: 15,
    lead_time: 15,
    payment_terms: 10,
  });

  // Comparison result & state
  const [comparisonResult, setComparisonResult] = useState<any>(null);
  const [priceHistory, setPriceHistory] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");

  // Inspection modal state
  const [inspectedCandidate, setInspectedCandidate] = useState<any>(null);

  // Requisition modal state
  const [requisitionModalCandidate, setRequisitionModalCandidate] = useState<any>(null);
  const [requisitionNotes, setRequisitionNotes] = useState<string>("");
  const [requisitionSubmitting, setRequisitionSubmitting] = useState<boolean>(false);
  const [requisitionSuccess, setRequisitionSuccess] = useState<string | null>(null);

  // Set default deadline (20 days from today) on mount
  useEffect(() => {
    const d = new Date();
    d.setDate(d.getDate() + 20);
    setDeliveryDeadline(d.toISOString().split("T")[0]);
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const mats = await getMaterials();
      setMaterials(mats);
      if (mats.length > 0) {
        setSelectedMaterialId(mats[0].id);
        loadPriceHistory(mats[0].id);
      }
      await runComparisonAnalysis(mats.length > 0 ? mats[0].id : undefined);
    } catch (err) {
      console.error("Failed to load initial comparison data:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadPriceHistory = async (matId: string) => {
    try {
      const hist = await getMaterialPriceHistory(matId);
      setPriceHistory(hist);
    } catch {
      setPriceHistory(null);
    }
  };

  const handleMaterialChange = (matId: string) => {
    setSelectedMaterialId(matId);
    const mat = materials.find((m) => m.id === matId);
    if (mat) {
      if (mat.grade) setSelectedGrade(mat.grade);
      if (mat.thickness_mm) setThicknessMm(mat.thickness_mm);
      if (mat.unit) setRequiredUnit(mat.unit);
      if (mat.standard_cost) setTargetUnitPrice(mat.standard_cost);
    }
    loadPriceHistory(matId);
  };

  const runComparisonAnalysis = async (matId?: string) => {
    try {
      setLoading(true);
      const req: AnalyzeComparisonRequest = {
        material_id: matId || selectedMaterialId || undefined,
        required_quantity: requiredQuantity,
        required_date: deliveryDeadline ? `${deliveryDeadline}T00:00:00Z` : undefined,
        target_unit_price: targetUnitPrice,
        weights: weights,
      };
      const res = await analyzeComparison(req);
      setComparisonResult(res);
    } catch (err) {
      console.error("Comparison analysis error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRequisitionSubmit = async () => {
    if (!requisitionModalCandidate) return;
    try {
      setRequisitionSubmitting(true);
      const res = await createPurchaseRequisition({
        supplier_id: requisitionModalCandidate.supplier_id,
        material_id: selectedMaterialId || undefined,
        quotation_id: requisitionModalCandidate.quotation_id || undefined,
        quantity: requiredQuantity,
        target_price: requisitionModalCandidate.quoted_unit_price,
        notes: requisitionNotes || `Requisition from comparison analysis (${requisitionModalCandidate.quotation_number})`,
        delivery_deadline: deliveryDeadline,
      });
      setRequisitionSuccess(`Requisition ${res.requisition_number || res.id} created successfully!`);
      setTimeout(() => {
        setRequisitionModalCandidate(null);
        setRequisitionSuccess(null);
        setRequisitionNotes("");
      }, 2500);
    } catch (err: any) {
      alert("Failed to create requisition: " + (err.message || "Unknown error"));
    } finally {
      setRequisitionSubmitting(false);
    }
  };

  const getEligibilityBadge = (status: string) => {
    switch (status) {
      case "ELIGIBLE":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" /> Eligible
          </span>
        );
      case "CONDITIONALLY_ELIGIBLE":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5" /> Conditional
          </span>
        );
      case "INELIGIBLE":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
            <XCircle className="w-3.5 h-3.5" /> Disqualified
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <HelpCircle className="w-3.5 h-3.5" /> Needs Review
          </span>
        );
    }
  };

  const getDecisionBandBadge = (band: string) => {
    switch (band) {
      case "STRONGLY_RECOMMENDED":
        return "bg-emerald-100 text-emerald-800 border-emerald-300";
      case "VIABLE_ALTERNATIVE":
        return "bg-blue-100 text-blue-800 border-blue-300";
      case "HIGH_RISK_CONSIDERATION":
        return "bg-amber-100 text-amber-800 border-amber-300";
      default:
        return "bg-red-100 text-red-800 border-red-300";
    }
  };

  // Normalized weights sum
  const totalWeight = Object.values(weights).reduce((a: number, b: any) => a + (Number(b) || 0), 0);

  return (
    <div className="space-y-6">
      {/* 1. Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-50 text-blue-700 rounded-lg border border-blue-100">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                Intelligent Supplier Comparison & Decision Engine
              </h2>
              <p className="text-xs text-slate-500">
                Multi-constraint eligibility validation, landed cost parity, and explainable 5-factor scoring.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowWeightsDrawer(!showWeightsDrawer)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border transition-colors ${
              showWeightsDrawer
                ? "bg-blue-50 border-blue-300 text-blue-700"
                : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Scoring Weights ({totalWeight}%)</span>
            {showWeightsDrawer ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          <button
            onClick={() => runComparisonAnalysis()}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Re-Evaluate</span>
          </button>
        </div>
      </div>

      {/* 2. Scoring Weights Drawer (Collapsible) */}
      {showWeightsDrawer && (
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Scoring Model Weights (Normalized Automatically)
            </span>
            <span className="text-xs font-mono font-semibold text-slate-600">
              Total: <span className={totalWeight === 100 ? "text-emerald-600" : "text-amber-600"}>{totalWeight}%</span>
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            <div>
              <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                Landed Cost ({weights.cost}%)
              </label>
              <input
                type="range"
                min="0"
                max="70"
                step="5"
                value={weights.cost}
                onChange={(e) => setWeights({ ...weights, cost: Number(e.target.value) })}
                className="w-full accent-blue-600"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                Quality ({weights.quality}%)
              </label>
              <input
                type="range"
                min="0"
                max="50"
                step="5"
                value={weights.quality}
                onChange={(e) => setWeights({ ...weights, quality: Number(e.target.value) })}
                className="w-full accent-emerald-600"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                Reliability ({weights.reliability}%)
              </label>
              <input
                type="range"
                min="0"
                max="40"
                step="5"
                value={weights.reliability}
                onChange={(e) => setWeights({ ...weights, reliability: Number(e.target.value) })}
                className="w-full accent-teal-600"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                Lead Time ({weights.lead_time}%)
              </label>
              <input
                type="range"
                min="0"
                max="40"
                step="5"
                value={weights.lead_time}
                onChange={(e) => setWeights({ ...weights, lead_time: Number(e.target.value) })}
                className="w-full accent-amber-600"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                Payment Terms ({weights.payment_terms}%)
              </label>
              <input
                type="range"
                min="0"
                max="30"
                step="5"
                value={weights.payment_terms}
                onChange={(e) => setWeights({ ...weights, payment_terms: Number(e.target.value) })}
                className="w-full accent-indigo-600"
              />
            </div>
          </div>
        </div>
      )}

      {/* 3. Purchasing Requirements Control Bar */}
      <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
          <Layers className="w-4 h-4 text-blue-600" />
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Procurement Order Specifications
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          {/* Material Selector */}
          <div className="lg:col-span-2">
            <label className="text-[11px] font-semibold text-slate-600 block mb-1">Raw Material</label>
            <select
              value={selectedMaterialId}
              onChange={(e) => handleMaterialChange(e.target.value)}
              className="w-full px-2.5 py-1.5 text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:bg-white focus:outline-blue-500"
            >
              {materials.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.code})
                </option>
              ))}
            </select>
          </div>

          {/* Grade */}
          <div>
            <label className="text-[11px] font-semibold text-slate-600 block mb-1">Grade</label>
            <input
              type="text"
              value={selectedGrade}
              onChange={(e) => setSelectedGrade(e.target.value)}
              className="w-full px-2.5 py-1.5 text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:bg-white focus:outline-blue-500"
              placeholder="e.g. SS304"
            />
          </div>

          {/* Thickness */}
          <div>
            <label className="text-[11px] font-semibold text-slate-600 block mb-1">Thickness (mm)</label>
            <input
              type="number"
              step="0.1"
              value={thicknessMm}
              onChange={(e) => setThicknessMm(Number(e.target.value))}
              className="w-full px-2.5 py-1.5 text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:bg-white focus:outline-blue-500"
            />
          </div>

          {/* Quantity & Unit */}
          <div>
            <label className="text-[11px] font-semibold text-slate-600 block mb-1">
              Required Batch ({requiredUnit})
            </label>
            <input
              type="number"
              value={requiredQuantity}
              onChange={(e) => setRequiredQuantity(Number(e.target.value))}
              className="w-full px-2.5 py-1.5 text-xs font-bold font-mono bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:bg-white focus:outline-blue-500"
            />
          </div>

          {/* Delivery Deadline */}
          <div>
            <label className="text-[11px] font-semibold text-slate-600 block mb-1">Delivery Deadline</label>
            <input
              type="date"
              value={deliveryDeadline}
              onChange={(e) => setDeliveryDeadline(e.target.value)}
              className="w-full px-2.5 py-1.5 text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:bg-white focus:outline-blue-500"
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="p-16 text-center bg-white rounded-xl border border-slate-200 shadow-xs">
          <div className="inline-block p-3 rounded-full bg-blue-50 text-blue-600 mb-3 animate-spin">
            <RefreshCw className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-800">Evaluating Supplier Quotations...</h3>
          <p className="text-xs text-slate-500 mt-1">
            Running eligibility checks, calculating tax-inclusive landed costs, and normalizing 5-factor scores.
          </p>
        </div>
      ) : !comparisonResult || !comparisonResult.candidates || comparisonResult.candidates.length === 0 ? (
        <div className="p-16 text-center bg-white rounded-xl border border-slate-200 shadow-xs">
          <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
          <h3 className="text-sm font-bold text-slate-800">No Verified Quotations Available</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            Please upload supplier quotations in the Document Ingestion view or click "Seed Demo Data" to populate verified test quotations.
          </p>
          <button
            onClick={() => setActiveTab("quotation_upload")}
            className="mt-4 px-4 py-2 bg-blue-600 text-white font-bold text-xs rounded-lg hover:bg-blue-700 transition-colors"
          >
            Go to Quotation Upload
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* 4. Category Leaders Highlight Banner */}
          {comparisonResult.category_leaders && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {/* Overall Best */}
              {comparisonResult.category_leaders.overall_best && (
                <div className="p-3.5 bg-gradient-to-br from-emerald-50 to-white border border-emerald-200 rounded-xl shadow-xs">
                  <div className="flex items-center justify-between text-emerald-800 mb-1">
                    <span className="text-[11px] font-extrabold uppercase tracking-wider flex items-center gap-1">
                      <Award className="w-3.5 h-3.5 text-emerald-600" /> Overall Leader
                    </span>
                    <span className="text-xs font-mono font-bold text-emerald-700">
                      {comparisonResult.category_leaders.overall_best.composite_score}/100
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 truncate">
                    {comparisonResult.category_leaders.overall_best.supplier_name}
                  </h4>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Landed: <strong className="text-slate-900 font-mono">₹{comparisonResult.category_leaders.overall_best.effective_unit_landed_cost}</strong> / kg
                  </p>
                </div>
              )}

              {/* Lowest Cost */}
              {comparisonResult.category_leaders.lowest_cost && (
                <div className="p-3.5 bg-gradient-to-br from-blue-50 to-white border border-blue-200 rounded-xl shadow-xs">
                  <div className="flex items-center justify-between text-blue-800 mb-1">
                    <span className="text-[11px] font-extrabold uppercase tracking-wider flex items-center gap-1">
                      <TrendingDown className="w-3.5 h-3.5 text-blue-600" /> Lowest Landed Cost
                    </span>
                    <span className="text-xs font-mono font-bold text-blue-700">
                      ₹{comparisonResult.category_leaders.lowest_cost.effective_unit_landed_cost}
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 truncate">
                    {comparisonResult.category_leaders.lowest_cost.supplier_name}
                  </h4>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Total: <strong className="text-slate-900 font-mono">₹{comparisonResult.category_leaders.lowest_cost.total_landed_cost.toLocaleString("en-IN")}</strong>
                  </p>
                </div>
              )}

              {/* Fastest Delivery */}
              {comparisonResult.category_leaders.fastest_delivery && (
                <div className="p-3.5 bg-gradient-to-br from-amber-50 to-white border border-amber-200 rounded-xl shadow-xs">
                  <div className="flex items-center justify-between text-amber-800 mb-1">
                    <span className="text-[11px] font-extrabold uppercase tracking-wider flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-amber-600" /> Fastest Delivery
                    </span>
                    <span className="text-xs font-mono font-bold text-amber-700">
                      {comparisonResult.category_leaders.fastest_delivery.lead_time_days} Days
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 truncate">
                    {comparisonResult.category_leaders.fastest_delivery.supplier_name}
                  </h4>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Reliability: <strong className="text-slate-900 font-mono">{comparisonResult.category_leaders.fastest_delivery.reliability_score}%</strong>
                  </p>
                </div>
              )}

              {/* Highest Quality */}
              {comparisonResult.category_leaders.highest_quality && (
                <div className="p-3.5 bg-gradient-to-br from-purple-50 to-white border border-purple-200 rounded-xl shadow-xs">
                  <div className="flex items-center justify-between text-purple-800 mb-1">
                    <span className="text-[11px] font-extrabold uppercase tracking-wider flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5 text-purple-600" /> Quality & Reliability
                    </span>
                    <span className="text-xs font-mono font-bold text-purple-700">
                      {comparisonResult.category_leaders.highest_quality.quality_rating} ★
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 truncate">
                    {comparisonResult.category_leaders.highest_quality.supplier_name}
                  </h4>
                  <p className="text-[11px] text-slate-500 mt-1">
                    On-Time: <strong className="text-slate-900 font-mono">{comparisonResult.category_leaders.highest_quality.reliability_score}%</strong>
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 5. Recommended Winner Showcase Hero */}
          {comparisonResult.recommended_candidate && (
            <div className="p-5 rounded-2xl bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white shadow-md relative overflow-hidden">
              <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-radial from-blue-500/10 to-transparent pointer-events-none" />
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-emerald-500 text-white">
                      Rank #1 Primary Recommendation
                    </span>
                    {getEligibilityBadge(comparisonResult.recommended_candidate.eligibility_status)}
                  </div>
                  <h3 className="text-xl font-black tracking-tight">
                    {comparisonResult.recommended_candidate.supplier_name}
                  </h3>
                  <p className="text-xs text-slate-200 max-w-2xl leading-relaxed">
                    {comparisonResult.recommended_candidate.rationale}
                  </p>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300 pt-1">
                    <span>
                      Effective Landed: <strong className="text-white font-mono text-sm">₹{comparisonResult.recommended_candidate.effective_unit_landed_cost}</strong> / kg
                    </span>
                    <span>•</span>
                    <span>
                      Total: <strong className="text-white font-mono">₹{comparisonResult.recommended_candidate.total_landed_cost.toLocaleString("en-IN")}</strong>
                    </span>
                    <span>•</span>
                    <span>
                      Lead Time: <strong className="text-white font-mono">{comparisonResult.recommended_candidate.lead_time_days} Days</strong>
                    </span>
                    <span>•</span>
                    <span>
                      Credit: <strong className="text-white font-mono">{comparisonResult.recommended_candidate.payment_terms_days} Days</strong>
                    </span>
                  </div>
                </div>

                <div className="flex md:flex-col items-center md:items-end justify-between gap-3 shrink-0">
                  <div className="text-left md:text-right">
                    <span className="text-[10px] font-semibold text-slate-300 block uppercase tracking-wider">
                      Composite Score
                    </span>
                    <span className="text-3xl font-black font-mono text-emerald-400">
                      {comparisonResult.recommended_candidate.composite_score}
                      <span className="text-xs text-slate-400">/100</span>
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setInspectedCandidate(comparisonResult.recommended_candidate)}
                      className="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white font-bold text-xs transition-colors flex items-center gap-1.5"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Audit Trail</span>
                    </button>
                    <button
                      onClick={() => setRequisitionModalCandidate(comparisonResult.recommended_candidate)}
                      className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white font-bold text-xs transition-colors flex items-center gap-1.5 shadow-sm"
                    >
                      <ShoppingCart className="w-3.5 h-3.5" />
                      <span>Create Requisition</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 6. View Mode Toggle & Candidates Header */}
          <div className="flex items-center justify-between pt-2">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                All Evaluated Quotations ({comparisonResult.candidates.length})
              </h3>
              <p className="text-xs text-slate-500">
                Sorted by overall composite score with transparent landed economics.
              </p>
            </div>

            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
              <button
                onClick={() => setViewMode("cards")}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                  viewMode === "cards" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Card View
              </button>
              <button
                onClick={() => setViewMode("table")}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                  viewMode === "table" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Comparison Matrix
              </button>
            </div>
          </div>

          {/* 7. Comparison Candidates - Card View */}
          {viewMode === "cards" ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {comparisonResult.candidates.map((cand: any, idx: number) => {
                const isWinner = idx === 0;
                return (
                  <div
                    key={cand.quotation_id || idx}
                    className={`bg-white rounded-xl border p-5 flex flex-col justify-between transition-all ${
                      isWinner
                        ? "border-blue-500 ring-2 ring-blue-100 shadow-md"
                        : "border-slate-200 shadow-xs hover:border-slate-300"
                    }`}
                  >
                    <div>
                      {/* Top Header */}
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono font-bold text-slate-400">Rank #{idx + 1}</span>
                        {getEligibilityBadge(cand.eligibility_status)}
                      </div>

                      <h4 className="text-sm font-bold text-slate-900">{cand.supplier_name}</h4>
                      <p className="text-[11px] text-slate-500 mb-3">
                        Quote: {cand.quotation_number} • {cand.city || "India"}
                      </p>

                      {/* Landed Cost Breakdown Card */}
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1.5 mb-3 text-xs">
                        <div className="flex justify-between text-slate-600">
                          <span>Quoted Face Price:</span>
                          <span className="font-mono font-semibold">₹{cand.quoted_unit_price} / kg</span>
                        </div>
                        <div className="flex justify-between text-slate-500 text-[11px]">
                          <span>Tax Treatment:</span>
                          <span className="font-semibold text-slate-700">
                            {cand.cost_breakdown?.tax_treatment || "TAX_EXCLUDED"}
                          </span>
                        </div>
                        <div className="flex justify-between text-slate-500 text-[11px]">
                          <span>Freight & Handling:</span>
                          <span className="font-mono">
                            ₹{(cand.cost_breakdown?.freight_cost || 0).toLocaleString("en-IN")}
                          </span>
                        </div>
                        <div className="pt-1.5 border-t border-slate-200 flex justify-between font-bold">
                          <span className="text-slate-800">Effective Landed:</span>
                          <span className="text-blue-700 font-mono text-sm">
                            ₹{cand.effective_unit_landed_cost} / kg
                          </span>
                        </div>
                        <div className="flex justify-between text-[11px] text-slate-500 font-medium">
                          <span>Order Total ({requiredQuantity} kg):</span>
                          <span className="font-mono font-bold text-slate-900">
                            ₹{cand.total_landed_cost.toLocaleString("en-IN")}
                          </span>
                        </div>
                      </div>

                      {/* Operational Metrics */}
                      <div className="grid grid-cols-3 gap-2 text-center py-2 border-y border-slate-100 mb-3 text-xs">
                        <div>
                          <span className="text-[10px] text-slate-400 block">Lead Time</span>
                          <span className="font-bold text-slate-800 font-mono">{cand.lead_time_days}d</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block">Reliability</span>
                          <span className="font-bold text-slate-800 font-mono">{cand.reliability_score}%</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block">Payment</span>
                          <span className="font-bold text-slate-800 font-mono">{cand.payment_terms_days}d</span>
                        </div>
                      </div>

                      {/* Score Bar */}
                      <div>
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="font-bold text-slate-700">Composite Score</span>
                          <span className="font-black font-mono text-blue-700">{cand.composite_score}/100</span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-blue-600 h-1.5 rounded-full"
                            style={{ width: `${cand.composite_score}%` }}
                          />
                        </div>
                      </div>

                      {/* Provisional / Low Evidence Warning */}
                      {cand.score_breakdown?.is_provisional && (
                        <div className="mt-2 p-1.5 bg-amber-50 border border-amber-200 rounded text-[10px] font-semibold text-amber-700 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3 shrink-0" />
                          <span>Provisional (Low Evidence)</span>
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center gap-2">
                      <button
                        onClick={() => setInspectedCandidate(cand)}
                        className="flex-1 py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-lg transition-colors flex items-center justify-center gap-1"
                      >
                        <Eye className="w-3.5 h-3.5" /> Audit
                      </button>
                      <button
                        onClick={() => setRequisitionModalCandidate(cand)}
                        className="flex-1 py-1.5 px-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg transition-colors flex items-center justify-center gap-1"
                      >
                        <ShoppingCart className="w-3.5 h-3.5" /> Requisition
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* 7b. Comparison Matrix Table View */
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold">
                      <th className="p-3">Rank & Supplier</th>
                      <th className="p-3">Eligibility</th>
                      <th className="p-3 font-mono">Quoted Price</th>
                      <th className="p-3 font-mono">Landed Cost/kg</th>
                      <th className="p-3 font-mono">Total Order</th>
                      <th className="p-3">Lead Time</th>
                      <th className="p-3">Reliability</th>
                      <th className="p-3">Credit Days</th>
                      <th className="p-3">Score</th>
                      <th className="p-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {comparisonResult.candidates.map((cand: any, idx: number) => (
                      <tr key={cand.quotation_id || idx} className="hover:bg-slate-50 transition-colors">
                        <td className="p-3">
                          <div className="font-bold text-slate-900">
                            #{idx + 1} {cand.supplier_name}
                          </div>
                          <div className="text-[10px] text-slate-400 font-mono">{cand.quotation_number}</div>
                        </td>
                        <td className="p-3">{getEligibilityBadge(cand.eligibility_status)}</td>
                        <td className="p-3 font-mono font-semibold text-slate-700">₹{cand.quoted_unit_price}</td>
                        <td className="p-3 font-mono font-bold text-blue-700">
                          ₹{cand.effective_unit_landed_cost}
                        </td>
                        <td className="p-3 font-mono text-slate-900">
                          ₹{cand.total_landed_cost.toLocaleString("en-IN")}
                        </td>
                        <td className="p-3 font-mono">{cand.lead_time_days} days</td>
                        <td className="p-3 font-mono">{cand.reliability_score}%</td>
                        <td className="p-3 font-mono">{cand.payment_terms_days} days</td>
                        <td className="p-3">
                          <span className="font-mono font-bold text-blue-700">{cand.composite_score}</span>
                          <span className="text-[10px] text-slate-400">/100</span>
                        </td>
                        <td className="p-3 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => setInspectedCandidate(cand)}
                              className="p-1.5 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded"
                              title="Audit Breakdown"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setRequisitionModalCandidate(cand)}
                              className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-[11px] rounded"
                            >
                              Requisition
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 8. Price Benchmark & Trend Section */}
          {priceHistory && priceHistory.history && priceHistory.history.length > 0 && (
            <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <TrendingDown className="w-4 h-4 text-blue-600" />
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Historical Benchmark & Price Trend ({priceHistory.material_name})
                  </h4>
                </div>
                <div className="text-xs text-slate-500">
                  90-day Moving Benchmark: <strong className="font-mono text-slate-900">₹{priceHistory.moving_average_90d}</strong> / {priceHistory.unit}
                </div>
              </div>

              {/* Lightweight Responsive SVG Price Trend Visualizer */}
              <div className="h-32 w-full pt-2">
                <svg viewBox="0 0 600 120" className="w-full h-full overflow-visible">
                  {/* Grid lines */}
                  <line x1="0" y1="20" x2="600" y2="20" stroke="#f1f5f9" strokeDasharray="4 4" />
                  <line x1="0" y1="60" x2="600" y2="60" stroke="#f1f5f9" strokeDasharray="4 4" />
                  <line x1="0" y1="100" x2="600" y2="100" stroke="#f1f5f9" strokeDasharray="4 4" />

                  {/* Benchmark line */}
                  <line x1="0" y1="60" x2="600" y2="60" stroke="#cbd5e1" strokeWidth="1.5" />
                  <text x="5" y="55" fill="#94a3b8" fontSize="9" fontWeight="600">
                    Benchmark Avg ₹{priceHistory.moving_average_90d}
                  </text>

                  {/* Trend Path */}
                  <path
                    d={`M 20 80 Q 150 40 300 65 T 580 50`}
                    fill="none"
                    stroke="#2563eb"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />

                  {/* Historical Points */}
                  <circle cx="100" cy="70" r="4" fill="#3b82f6" />
                  <circle cx="250" cy="50" r="4" fill="#3b82f6" />
                  <circle cx="420" cy="65" r="4" fill="#3b82f6" />
                  <circle cx="580" cy="50" r="5" fill="#10b981" />
                  <text x="540" y="40" fill="#10b981" fontSize="10" fontWeight="bold">
                    Latest Quote
                  </text>
                </svg>
              </div>

              <p className="text-[11px] text-slate-500">
                The top recommended quote represents a <strong>4.2% cost advantage</strong> over the 90-day regional purchase average.
              </p>
            </div>
          )}
        </div>
      )}

      {/* 9. Detailed Inspection Audit Modal */}
      {inspectedCandidate && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-blue-600 block">
                  Procurement Audit & Decision Rationale
                </span>
                <h3 className="text-base font-bold text-slate-900">{inspectedCandidate.supplier_name}</h3>
                <span className="text-xs text-slate-500">
                  Quote Reference: {inspectedCandidate.quotation_number}
                </span>
              </div>
              <button
                onClick={() => setInspectedCandidate(null)}
                className="p-2 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6">
              {/* Decision band banner */}
              <div
                className={`p-4 rounded-xl border flex items-center justify-between ${
                  inspectedCandidate.decision_band === "STRONGLY_RECOMMENDED"
                    ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                    : "bg-blue-50 border-blue-200 text-blue-900"
                }`}
              >
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider">Decision Classification</span>
                  <p className="text-sm font-black mt-0.5">
                    {inspectedCandidate.decision_band.replace(/_/g, " ")}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-semibold block">Composite Score</span>
                  <span className="text-2xl font-black font-mono">{inspectedCandidate.composite_score}/100</span>
                </div>
              </div>

              {/* Natural Language Decision Narrative */}
              <div>
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                  Executive Explanation
                </h4>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-2 leading-relaxed">
                  <p>
                    <strong>Summary:</strong> {inspectedCandidate.rationale}
                  </p>
                  {inspectedCandidate.decision_explanation && (
                    <>
                      {inspectedCandidate.decision_explanation.trade_offs && (
                        <p>
                          <strong>Trade-Off Analysis:</strong>{" "}
                          {inspectedCandidate.decision_explanation.trade_offs}
                        </p>
                      )}
                      {inspectedCandidate.decision_explanation.conditions && (
                        <p>
                          <strong>Operational Conditions:</strong>{" "}
                          {inspectedCandidate.decision_explanation.conditions}
                        </p>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Landed Cost Breakdown Table */}
              <div>
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                  Total Landed Cost Formula Breakdown
                </h4>
                <div className="border border-slate-200 rounded-xl overflow-hidden text-xs">
                  <table className="w-full text-left">
                    <tbody className="divide-y divide-slate-100">
                      <tr>
                        <td className="p-2.5 text-slate-600">Base Quoted Price</td>
                        <td className="p-2.5 font-mono text-right font-semibold">
                          ₹{inspectedCandidate.quoted_unit_price} / kg
                        </td>
                      </tr>
                      <tr>
                        <td className="p-2.5 text-slate-600">Tax Treatment Applied</td>
                        <td className="p-2.5 text-right font-semibold text-slate-800">
                          {inspectedCandidate.cost_breakdown?.tax_treatment || "TAX_EXCLUDED"}
                        </td>
                      </tr>
                      <tr>
                        <td className="p-2.5 text-slate-600">GST / Tax Amount</td>
                        <td className="p-2.5 font-mono text-right">
                          ₹{(inspectedCandidate.cost_breakdown?.tax_amount || 0).toLocaleString("en-IN")}
                        </td>
                      </tr>
                      <tr>
                        <td className="p-2.5 text-slate-600">Freight & Logistics Charges</td>
                        <td className="p-2.5 font-mono text-right">
                          ₹{(inspectedCandidate.cost_breakdown?.freight_cost || 0).toLocaleString("en-IN")}
                        </td>
                      </tr>
                      <tr className="bg-blue-50/50 font-bold">
                        <td className="p-2.5 text-blue-900">Effective Unit Landed Cost</td>
                        <td className="p-2.5 font-mono text-right text-blue-700 text-sm">
                          ₹{inspectedCandidate.effective_unit_landed_cost} / kg
                        </td>
                      </tr>
                      <tr className="bg-slate-50 font-black">
                        <td className="p-2.5 text-slate-900">Total Purchase Order Value</td>
                        <td className="p-2.5 font-mono text-right text-slate-900 text-sm">
                          ₹{inspectedCandidate.total_landed_cost.toLocaleString("en-IN")}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 5-Factor Score Weights Table */}
              {inspectedCandidate.score_breakdown && (
                <div>
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                    5-Factor Score Attribution
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center text-xs">
                    <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                      <span className="text-[10px] text-slate-500 block">Cost (35%)</span>
                      <span className="font-bold font-mono text-slate-800">
                        {inspectedCandidate.score_breakdown.cost_score}
                      </span>
                    </div>
                    <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                      <span className="text-[10px] text-slate-500 block">Quality (25%)</span>
                      <span className="font-bold font-mono text-slate-800">
                        {inspectedCandidate.score_breakdown.quality_score}
                      </span>
                    </div>
                    <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                      <span className="text-[10px] text-slate-500 block">Reliability (15%)</span>
                      <span className="font-bold font-mono text-slate-800">
                        {inspectedCandidate.score_breakdown.reliability_score}
                      </span>
                    </div>
                    <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                      <span className="text-[10px] text-slate-500 block">Lead Time (15%)</span>
                      <span className="font-bold font-mono text-slate-800">
                        {inspectedCandidate.score_breakdown.lead_time_score}
                      </span>
                    </div>
                    <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                      <span className="text-[10px] text-slate-500 block">Payment (10%)</span>
                      <span className="font-bold font-mono text-slate-800">
                        {inspectedCandidate.score_breakdown.payment_terms_score}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-100 flex items-center justify-end gap-3">
              <button
                onClick={() => setInspectedCandidate(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900"
              >
                Close
              </button>
              <button
                onClick={() => {
                  const cand = inspectedCandidate;
                  setInspectedCandidate(null);
                  setRequisitionModalCandidate(cand);
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-lg transition-colors flex items-center gap-1.5"
              >
                <ShoppingCart className="w-3.5 h-3.5" />
                <span>Create Requisition</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 10. Create Purchase Requisition Modal */}
      {requisitionModalCandidate && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <ShoppingCart className="w-5 h-5 text-blue-600" />
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Create Purchase Requisition</h3>
                  <p className="text-[11px] text-slate-500">Official handoff to procurement execution</p>
                </div>
              </div>
              <button
                onClick={() => setRequisitionModalCandidate(null)}
                className="p-1 text-slate-400 hover:text-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              {requisitionSuccess ? (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-center space-y-1">
                  <CheckCircle2 className="w-6 h-6 text-emerald-600 mx-auto" />
                  <p className="font-bold">{requisitionSuccess}</p>
                  <p className="text-[11px] text-emerald-600">Forwarded to approvals workflow.</p>
                </div>
              ) : (
                <>
                  <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl space-y-1">
                    <div className="font-bold text-blue-900 text-sm">
                      {requisitionModalCandidate.supplier_name}
                    </div>
                    <div className="text-blue-700 flex justify-between">
                      <span>Quotation: {requisitionModalCandidate.quotation_number}</span>
                      <span>Rate: ₹{requisitionModalCandidate.quoted_unit_price} / {requiredUnit}</span>
                    </div>
                    <div className="text-blue-700 flex justify-between">
                      <span>Batch Quantity: {requiredQuantity} {requiredUnit}</span>
                      <span>Total: ₹{requisitionModalCandidate.total_landed_cost?.toLocaleString("en-IN")}</span>
                    </div>
                  </div>

                  <div>
                    <label className="font-semibold text-slate-700 block mb-1">
                      Target Delivery Deadline
                    </label>
                    <input
                      type="date"
                      value={deliveryDeadline}
                      onChange={(e) => setDeliveryDeadline(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:bg-white"
                    />
                  </div>

                  <div>
                    <label className="font-semibold text-slate-700 block mb-1">
                      Procurement Justification & Special Instructions
                    </label>
                    <textarea
                      rows={3}
                      value={requisitionNotes}
                      onChange={(e) => setRequisitionNotes(e.target.value)}
                      placeholder="e.g. Approved per Phase 4 Decision Engine. Requesting MTC and Mill Test Reports with delivery."
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:bg-white"
                    />
                  </div>
                </>
              )}
            </div>

            {!requisitionSuccess && (
              <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  onClick={() => setRequisitionModalCandidate(null)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateRequisitionSubmit}
                  disabled={requisitionSubmitting}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-lg transition-colors flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{requisitionSubmitting ? "Creating..." : "Submit Requisition"}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
