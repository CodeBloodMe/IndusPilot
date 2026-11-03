"use client";

import React, { useState, useEffect } from "react";
import {
  Compass,
  CheckCircle2,
  AlertTriangle,
  Play,
  Layers,
  ArrowRight,
  ShieldCheck,
  Split,
  Building2,
  DollarSign,
  TrendingDown,
  Calendar,
  Box,
  Truck,
  Sparkles,
  FileText,
  Clock,
  History,
  Send,
  Check,
  X,
  PackageCheck,
  Percent,
  RefreshCw
} from "lucide-react";
import {
  getProcurementStrategies,
  getProcurementPlans,
  getProcurementPlanDetails,
  createProcurementPlan,
  createProcurementPlanFromJob,
  reoptimizeProcurementPlan,
  requestProcurementPlanApproval,
  approveProcurementPlan,
  rejectProcurementPlan,
  generateRequisitionsFromPlan,
  getProductionJobs,
  getMaterials
} from "@/lib/api";

export default function OptimizationView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  // Navigation sub-tab
  const [activeSubTab, setActiveSubTab] = useState<"optimize" | "history">("optimize");

  // Input source mode
  const [sourceMode, setSourceMode] = useState<"job" | "custom">("job");

  // Reference data
  const [productionJobs, setProductionJobs] = useState<any[]>([]);
  const [materialsList, setMaterialsList] = useState<any[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);

  // Job selection state
  const [selectedJobId, setSelectedJobId] = useState<string>("");

  // Custom materials selection state
  const [customItems, setCustomItems] = useState<Array<{
    material_id: string;
    material_code: string;
    material_name: string;
    required_quantity: number;
    unit: string;
    max_lead_time_days: number;
  }>>([]);

  // Strategy & Constraints
  const [selectedStrategy, setSelectedStrategy] = useState<string>("LOWEST_LANDED_COST");
  const [budgetLimit, setBudgetLimit] = useState<string>("");
  const [maxLeadTimeDays, setMaxLeadTimeDays] = useState<string>("14");
  const [minQualityRating, setMinQualityRating] = useState<string>("4.0");
  const [allowSplitPurchasing, setAllowSplitPurchasing] = useState<boolean>(true);
  const [maxSuppliersPerMaterial, setMaxSuppliersPerMaterial] = useState<number>(3);
  const [maxOverbuyPct, setMaxOverbuyPct] = useState<number>(10);

  // Execution & Solution state
  const [solving, setSolving] = useState<boolean>(false);
  const [currentPlan, setCurrentPlan] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // History & Approval state
  const [historicalPlans, setHistoricalPlans] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [rejectionModalOpen, setRejectionModalOpen] = useState<boolean>(false);
  const [rejectionReason, setRejectionReason] = useState<string>("");

  // Load initial data
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [stratRes, jobsRes, matsRes] = await Promise.allSettled([
          getProcurementStrategies(),
          getProductionJobs(),
          getMaterials()
        ]);

        if (stratRes.status === "fulfilled" && stratRes.value?.strategies) {
          setStrategies(stratRes.value.strategies);
        } else {
          // Fallback strategies
          setStrategies([
            { id: "LOWEST_LANDED_COST", name: "Lowest Landed Cost", description: "Minimises total landed cost including GST and freight." },
            { id: "BALANCED", name: "Balanced Multi-Criteria", description: "Pareto optimal balance: Cost 40%, Quality 25%, Reliability 25%, Speed 10%." },
            { id: "FASTEST_DELIVERY", name: "Fastest Delivery", description: "Prioritises minimal vendor lead time to expedite manufacturing schedule." },
            { id: "QUALITY_FIRST", name: "Quality First", description: "Allocates to ISO/AS9100 vendors with highest historical ratings." },
            { id: "BUDGET_CONSTRAINED", name: "Budget Constrained", description: "Enforces strict financial cap with multi-sourcing." }
          ]);
        }

        if (jobsRes.status === "fulfilled" && Array.isArray(jobsRes.value)) {
          setProductionJobs(jobsRes.value);
          if (jobsRes.value.length > 0) {
            setSelectedJobId(jobsRes.value[0].id);
          }
        }

        if (matsRes.status === "fulfilled" && Array.isArray(matsRes.value)) {
          setMaterialsList(matsRes.value);
          // Pre-populate custom items with default 2 materials
          if (matsRes.value.length >= 2) {
            setCustomItems([
              {
                material_id: matsRes.value[0].id,
                material_code: matsRes.value[0].code,
                material_name: matsRes.value[0].name,
                required_quantity: 800,
                unit: matsRes.value[0].unit || "kg",
                max_lead_time_days: 14
              },
              {
                material_id: matsRes.value[1].id,
                material_code: matsRes.value[1].code,
                material_name: matsRes.value[1].name,
                required_quantity: 500,
                unit: matsRes.value[1].unit || "nos",
                max_lead_time_days: 14
              }
            ]);
          }
        }
      } catch (e) {
        console.error("Failed to load initial optimizer metadata:", e);
      }
    }

    loadInitialData();
  }, []);

  // Fetch plan history
  const fetchPlanHistory = async () => {
    try {
      setLoadingHistory(true);
      const plans = await getProcurementPlans();
      setHistoricalPlans(plans);
    } catch (e: any) {
      console.error("Error loading plans history:", e);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (activeSubTab === "history") {
      fetchPlanHistory();
    }
  }, [activeSubTab]);

  // Execute OR-Tools Optimization
  const handleRunOptimization = async () => {
    try {
      setSolving(true);
      setErrorMsg(null);
      setSuccessMsg(null);

      const parsedBudget = budgetLimit ? parseFloat(budgetLimit) : undefined;
      const parsedLead = maxLeadTimeDays ? parseInt(maxLeadTimeDays) : undefined;
      const parsedQuality = minQualityRating ? parseFloat(minQualityRating) : undefined;

      let res: any;

      if (sourceMode === "job") {
        if (!selectedJobId) {
          throw new Error("Please select an active production job to optimize.");
        }
        res = await createProcurementPlanFromJob({
          job_id: selectedJobId,
          strategy: selectedStrategy,
          budget_limit: parsedBudget,
          max_suppliers_per_material: maxSuppliersPerMaterial,
          allow_split_purchasing: allowSplitPurchasing,
          global_max_lead_time_days: parsedLead,
          min_quality_rating: parsedQuality,
          max_overbuy_pct: maxOverbuyPct
        });
      } else {
        if (customItems.length === 0) {
          throw new Error("Please add at least one material requirement.");
        }
        res = await createProcurementPlan({
          requirements: customItems.map(item => ({
            material_id: item.material_id,
            material_code: item.material_code,
            material_name: item.material_name,
            required_quantity: item.required_quantity,
            unit: item.unit,
            max_lead_time_days: item.max_lead_time_days
          })),
          strategy: selectedStrategy,
          budget_limit: parsedBudget,
          max_suppliers_per_material: maxSuppliersPerMaterial,
          allow_split_purchasing: allowSplitPurchasing,
          global_max_lead_time_days: parsedLead,
          min_quality_rating: parsedQuality,
          max_overbuy_pct: maxOverbuyPct
        });
      }

      setCurrentPlan(res);
      setSuccessMsg(`Plan ${res.plan_number || "Optimized"} generated successfully!`);
    } catch (err: any) {
      setErrorMsg(err.message || "Procurement optimization failed.");
    } finally {
      setSolving(false);
    }
  };

  // Re-optimize existing plan with modified parameters
  const handleReoptimize = async () => {
    if (!currentPlan?.plan_id) return;
    try {
      setSolving(true);
      setErrorMsg(null);
      const parsedBudget = budgetLimit ? parseFloat(budgetLimit) : undefined;
      const parsedLead = maxLeadTimeDays ? parseInt(maxLeadTimeDays) : undefined;
      const parsedQuality = minQualityRating ? parseFloat(minQualityRating) : undefined;

      const res = await reoptimizeProcurementPlan(currentPlan.plan_id, {
        strategy: selectedStrategy,
        budget_limit: parsedBudget,
        max_suppliers_per_material: maxSuppliersPerMaterial,
        allow_split_purchasing: allowSplitPurchasing,
        global_max_lead_time_days: parsedLead,
        min_quality_rating: parsedQuality,
        max_overbuy_pct: maxOverbuyPct
      });

      setCurrentPlan(res);
      setSuccessMsg(`Plan ${res.plan_number} re-optimized with strategy ${selectedStrategy}!`);
    } catch (err: any) {
      setErrorMsg(err.message || "Re-optimization failed.");
    } finally {
      setSolving(false);
    }
  };

  // Submit for Approval
  const handleSubmitApproval = async () => {
    if (!currentPlan?.plan_id) return;
    try {
      setSolving(true);
      const res = await requestProcurementPlanApproval(currentPlan.plan_id, "Procurement Officer");
      setCurrentPlan((prev: any) => ({ ...prev, status: "PENDING_APPROVAL", approval_status: "PENDING_APPROVAL" }));
      setSuccessMsg(res.message || "Submitted for managerial approval.");
    } catch (err: any) {
      setErrorMsg(err.message || "Approval request failed.");
    } finally {
      setSolving(false);
    }
  };

  // Manager Approve Plan
  const handleApprovePlan = async () => {
    if (!currentPlan?.plan_id) return;
    try {
      setSolving(true);
      const res = await approveProcurementPlan(currentPlan.plan_id, "Operations Director", "Approved based on Pareto landed cost optimization.");
      setCurrentPlan((prev: any) => ({ ...prev, status: "APPROVED", approval_status: "APPROVED" }));
      setSuccessMsg(res.message || "Plan approved by Operations Director!");
    } catch (err: any) {
      setErrorMsg(err.message || "Approval action failed.");
    } finally {
      setSolving(false);
    }
  };

  // Manager Reject Plan
  const handleRejectPlan = async () => {
    if (!currentPlan?.plan_id) return;
    if (!rejectionReason.trim()) {
      setErrorMsg("Please specify a reason for rejecting the procurement plan.");
      return;
    }
    try {
      setSolving(true);
      const res = await rejectProcurementPlan(currentPlan.plan_id, rejectionReason, "Operations Director");
      setCurrentPlan((prev: any) => ({ ...prev, status: "REJECTED", approval_status: "REJECTED" }));
      setRejectionModalOpen(false);
      setSuccessMsg(res.message || "Plan marked as REJECTED.");
    } catch (err: any) {
      setErrorMsg(err.message || "Rejection action failed.");
    } finally {
      setSolving(false);
    }
  };

  // Generate Purchase Requisitions
  const handleGenerateRequisitions = async () => {
    if (!currentPlan?.plan_id) return;
    try {
      setSolving(true);
      const res = await generateRequisitionsFromPlan(currentPlan.plan_id, "MRP Optimization Engine");
      setCurrentPlan((prev: any) => ({ ...prev, status: "CONVERTED_TO_PO" }));
      setSuccessMsg(`Dispatched ${res.requisitions_count} Purchase Requisitions to procurement ledger!`);
    } catch (err: any) {
      setErrorMsg(err.message || "Generating requisitions failed.");
    } finally {
      setSolving(false);
    }
  };

  // Load a historical plan
  const handleSelectHistoricalPlan = async (planId: string) => {
    try {
      setSolving(true);
      const details = await getProcurementPlanDetails(planId);
      setCurrentPlan(details);
      setSelectedStrategy(details.strategy || "LOWEST_LANDED_COST");
      if (details.budget_limit) setBudgetLimit(String(details.budget_limit));
      setActiveSubTab("optimize");
      setSuccessMsg(`Loaded plan ${details.plan_number}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load plan details.");
    } finally {
      setSolving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Navigation Sub-Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
            <Compass className="w-6 h-6 text-blue-600" />
            <span>Advanced Multi-Material Procurement Optimizer</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Google OR-Tools Mixed-Integer Linear Programming (MILP) solver for multi-material, multi-supplier allocation,
            BOM requirement netting, baseline comparative benchmarking, and approval governance.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-xl">
          <button
            onClick={() => setActiveSubTab("optimize")}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeSubTab === "optimize"
                ? "bg-white text-blue-700 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Optimizer Console</span>
          </button>
          <button
            onClick={() => setActiveSubTab("history")}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeSubTab === "history"
                ? "bg-white text-blue-700 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>Saved Plans & Approvals</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-red-500 hover:text-red-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            <span className="font-semibold">{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-500 hover:text-emerald-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {activeSubTab === "optimize" ? (
        <div className="space-y-6">
          {/* Configuration Card */}
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-6">
            {/* Step 1: Input Source Selection */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-[11px] font-bold">1</span>
                  Requirement Origin
                </span>
                <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-lg text-xs">
                  <button
                    onClick={() => setSourceMode("job")}
                    className={`px-3 py-1 rounded-md font-bold transition-all ${
                      sourceMode === "job" ? "bg-white text-blue-700 shadow-2xs" : "text-slate-600"
                    }`}
                  >
                    From Production Job (MRP Shortages)
                  </button>
                  <button
                    onClick={() => setSourceMode("custom")}
                    className={`px-3 py-1 rounded-md font-bold transition-all ${
                      sourceMode === "custom" ? "bg-white text-blue-700 shadow-2xs" : "text-slate-600"
                    }`}
                  >
                    Custom Multi-Material Requirement
                  </button>
                </div>
              </div>

              {sourceMode === "job" ? (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block">
                      Target Production Job:
                    </label>
                    <select
                      value={selectedJobId}
                      onChange={(e) => setSelectedJobId(e.target.value)}
                      className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs font-semibold text-slate-900 w-full sm:w-80 shadow-2xs"
                    >
                      {productionJobs.map((job) => (
                        <option key={job.id} value={job.id}>
                          {job.job_number} — {job.product?.name || "Product"} ({job.production_quantity} Units)
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="text-xs text-slate-600 max-w-sm">
                    <p className="font-semibold text-slate-800">Automated MRP Netting:</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Explodes the multi-level BOM, applies scrap factors, deducts unreserved warehouse inventory, and isolates exact shortages.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="overflow-x-auto border border-slate-200 rounded-xl">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px]">
                        <tr>
                          <th className="py-2.5 px-3">Material SKU</th>
                          <th className="py-2.5 px-3">Required Qty</th>
                          <th className="py-2.5 px-3">Unit</th>
                          <th className="py-2.5 px-3">Max Lead Time</th>
                          <th className="py-2.5 px-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {customItems.map((item, idx) => (
                          <tr key={idx} className="hover:bg-slate-50/50">
                            <td className="py-2 px-3">
                              <select
                                value={item.material_id}
                                onChange={(e) => {
                                  const m = materialsList.find(mat => mat.id === e.target.value);
                                  const updated = [...customItems];
                                  updated[idx] = {
                                    ...updated[idx],
                                    material_id: e.target.value,
                                    material_code: m?.code || "SKU",
                                    material_name: m?.name || "Material",
                                    unit: m?.unit || "kg"
                                  };
                                  setCustomItems(updated);
                                }}
                                className="bg-white border border-slate-200 rounded px-2 py-1 text-xs text-slate-800 font-medium"
                              >
                                {materialsList.map((m) => (
                                  <option key={m.id} value={m.id}>
                                    {m.code} — {m.name}
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td className="py-2 px-3">
                              <input
                                type="number"
                                min={1}
                                value={item.required_quantity}
                                onChange={(e) => {
                                  const updated = [...customItems];
                                  updated[idx].required_quantity = parseFloat(e.target.value) || 0;
                                  setCustomItems(updated);
                                }}
                                className="w-24 bg-white border border-slate-200 rounded px-2 py-1 text-xs font-mono"
                              />
                            </td>
                            <td className="py-2 px-3 font-mono text-slate-600">{item.unit}</td>
                            <td className="py-2 px-3">
                              <input
                                type="number"
                                min={1}
                                value={item.max_lead_time_days}
                                onChange={(e) => {
                                  const updated = [...customItems];
                                  updated[idx].max_lead_time_days = parseInt(e.target.value) || 14;
                                  setCustomItems(updated);
                                }}
                                className="w-20 bg-white border border-slate-200 rounded px-2 py-1 text-xs font-mono"
                              />
                              <span className="text-[10px] text-slate-400 ml-1">days</span>
                            </td>
                            <td className="py-2 px-3 text-right">
                              <button
                                onClick={() => setCustomItems(customItems.filter((_, i) => i !== idx))}
                                className="text-red-500 hover:text-red-700 text-xs font-bold"
                              >
                                Remove
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <button
                    onClick={() => {
                      if (materialsList.length > 0) {
                        setCustomItems([
                          ...customItems,
                          {
                            material_id: materialsList[0].id,
                            material_code: materialsList[0].code,
                            material_name: materialsList[0].name,
                            required_quantity: 100,
                            unit: materialsList[0].unit || "kg",
                            max_lead_time_days: 14
                          }
                        ]);
                      }
                    }}
                    className="text-xs text-blue-600 hover:text-blue-800 font-bold"
                  >
                    + Add Another Material Requirement
                  </button>
                </div>
              )}
            </div>

            {/* Step 2: Optimization Strategy */}
            <div>
              <span className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2 mb-3">
                <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-[11px] font-bold">2</span>
                Procurement Objective Function
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                {strategies.map((st) => (
                  <button
                    key={st.id}
                    onClick={() => setSelectedStrategy(st.id)}
                    className={`p-3.5 rounded-xl border text-left transition-all flex flex-col justify-between ${
                      selectedStrategy === st.id
                        ? "bg-blue-50/70 border-blue-600 shadow-xs ring-1 ring-blue-600"
                        : "bg-white border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className={`text-[10px] font-bold uppercase tracking-wider ${
                          selectedStrategy === st.id ? "text-blue-700" : "text-slate-500"
                        }`}>
                          {st.id === "LOWEST_LANDED_COST" && "Cost Centric"}
                          {st.id === "BALANCED" && "Balanced"}
                          {st.id === "FASTEST_DELIVERY" && "Schedule First"}
                          {st.id === "QUALITY_FIRST" && "Quality Priority"}
                          {st.id === "BUDGET_CONSTRAINED" && "Budget Cap"}
                        </span>
                        {selectedStrategy === st.id && (
                          <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                        )}
                      </div>
                      <h4 className="text-xs font-bold text-slate-900">{st.name}</h4>
                      <p className="text-[10px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                        {st.description}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Step 3: Hard Constraints & Boundary Conditions */}
            <div>
              <span className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2 mb-3">
                <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-[11px] font-bold">3</span>
                Mathematical Boundary Conditions
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-6 gap-4 text-xs bg-slate-50/70 p-4 rounded-xl border border-slate-200">
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">
                    Budget Ceiling (₹):
                  </label>
                  <input
                    type="number"
                    placeholder="e.g. 500000"
                    value={budgetLimit}
                    onChange={(e) => setBudgetLimit(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900"
                  />
                  <span className="text-[10px] text-slate-400">Optional upper cap</span>
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">
                    Max Lead Time (Days):
                  </label>
                  <input
                    type="number"
                    value={maxLeadTimeDays}
                    onChange={(e) => setMaxLeadTimeDays(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900"
                  />
                  <span className="text-[10px] text-slate-400">Delivery deadline</span>
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">
                    Min Quality Rating:
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="1.0"
                    max="5.0"
                    value={minQualityRating}
                    onChange={(e) => setMinQualityRating(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900"
                  />
                  <span className="text-[10px] text-slate-400">Out of 5.0 stars</span>
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">
                    Max Overbuy Tol. (%):
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="50"
                    value={maxOverbuyPct}
                    onChange={(e) => setMaxOverbuyPct(parseFloat(e.target.value) || 0)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900"
                  />
                  <span className="text-[10px] text-slate-400">For packaging/MOQs</span>
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">
                    Max Suppliers/Material:
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={maxSuppliersPerMaterial}
                    onChange={(e) => setMaxSuppliersPerMaterial(parseInt(e.target.value) || 1)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900"
                  />
                  <span className="text-[10px] text-slate-400">Quota splitting cap</span>
                </div>

                <div className="flex flex-col justify-center">
                  <label className="flex items-center gap-2 cursor-pointer pt-2 text-slate-800">
                    <input
                      type="checkbox"
                      checked={allowSplitPurchasing}
                      onChange={(e) => setAllowSplitPurchasing(e.target.checked)}
                      className="rounded accent-blue-600 w-4 h-4"
                    />
                    <span className="font-bold text-[11px]">Allow Split Quotas</span>
                  </label>
                  <span className="text-[10px] text-slate-400 mt-1">Distribute across vendors</span>
                </div>
              </div>
            </div>

            {/* Submit Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-100">
              <span className="text-xs text-slate-500 font-mono">
                MILP SCIP Model Formulation: Decision Variables x[s,m], y[s,m], z[s], k[s,m]
              </span>

              <div className="flex items-center gap-3 w-full sm:w-auto">
                {currentPlan && (
                  <button
                    onClick={handleReoptimize}
                    disabled={solving}
                    className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold text-xs transition-all disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${solving ? "animate-spin" : ""}`} />
                    <span>Re-optimize Parameters</span>
                  </button>
                )}

                <button
                  onClick={handleRunOptimization}
                  disabled={solving}
                  className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-black text-xs shadow-md shadow-blue-500/20 transition-all disabled:opacity-50"
                >
                  <Play className={`w-4 h-4 fill-white ${solving ? "animate-spin" : ""}`} />
                  <span>{solving ? "Solving Mathematical Model..." : "Execute OR-Tools Optimization"}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Results Console */}
          {currentPlan && (
            <div className="space-y-6">
              {/* Executive Summary Card */}
              <div
                className={`p-6 rounded-2xl border shadow-sm transition-all ${
                  currentPlan.status === "OPTIMIZED" || currentPlan.status === "APPROVED"
                    ? "bg-white border-blue-200"
                    : currentPlan.status === "NEEDS_REVIEW"
                    ? "bg-amber-50/50 border-amber-300"
                    : "bg-white border-slate-200"
                }`}
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-100">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2.5">
                      <span className="px-2.5 py-1 rounded-lg bg-slate-900 text-white font-mono text-xs font-bold">
                        {currentPlan.plan_number || "PLAN-2026"}
                      </span>
                      <span
                        className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                          currentPlan.solver_status === "OPTIMAL"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                            : currentPlan.solver_status === "FEASIBLE"
                            ? "bg-blue-50 text-blue-700 border-blue-300"
                            : "bg-red-50 text-red-700 border-red-300"
                        }`}
                      >
                        Solver: {currentPlan.solver_status || currentPlan.status}
                      </span>
                      <span
                        className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                          currentPlan.approval_status === "APPROVED"
                            ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                            : currentPlan.approval_status === "PENDING_APPROVAL"
                            ? "bg-amber-100 text-amber-800 border-amber-300"
                            : currentPlan.approval_status === "REJECTED"
                            ? "bg-red-100 text-red-800 border-red-300"
                            : "bg-slate-100 text-slate-700 border-slate-300"
                        }`}
                      >
                        Approval: {currentPlan.approval_status || "DRAFT"}
                      </span>
                    </div>

                    <h3 className="text-xl font-black text-slate-900">
                      {currentPlan.explanation_headline || "Procurement Allocation Optimized"}
                    </h3>
                    <p className="text-xs text-slate-600 max-w-2xl font-mono whitespace-pre-line leading-relaxed">
                      {currentPlan.explanation_detail || currentPlan.message}
                    </p>
                  </div>

                  {/* Financial KPI Badges */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 shrink-0 bg-slate-50 p-4 rounded-xl border border-slate-200">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">Total Landed Cost</span>
                      <span className="text-lg font-black text-slate-900 font-mono">
                        ₹{Number(currentPlan.total_landed_cost || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">Budget Utilized</span>
                      <span className="text-lg font-black text-blue-700 font-mono">
                        {currentPlan.budget_utilized_pct ? `${currentPlan.budget_utilized_pct}%` : "100%"}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">Units Allocated</span>
                      <span className="text-lg font-black text-slate-800 font-mono">
                        {currentPlan.total_units_allocated || currentPlan.total_units_required || 0}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">Surplus Overbuy</span>
                      <span className="text-lg font-black text-slate-700 font-mono">
                        {currentPlan.excess_units || 0} units
                      </span>
                    </div>
                  </div>
                </div>

                {/* Workflow Governance Action Toolbar */}
                <div className="flex flex-wrap items-center justify-between gap-4 pt-4">
                  <div className="text-xs text-slate-500">
                    Strategy: <span className="font-bold text-slate-800">{currentPlan.strategy}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Submit for Manager Approval */}
                    {(!currentPlan.approval_status || currentPlan.approval_status === "PENDING" || currentPlan.approval_status === "DRAFT") && currentPlan.status !== "NEEDS_REVIEW" && (
                      <button
                        onClick={handleSubmitApproval}
                        disabled={solving}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs shadow-xs transition-all disabled:opacity-50"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>Request Manager Approval</span>
                      </button>
                    )}

                    {/* Manager Approve */}
                    {currentPlan.approval_status === "PENDING_APPROVAL" && (
                      <>
                        <button
                          onClick={handleApprovePlan}
                          disabled={solving}
                          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-xs transition-all disabled:opacity-50"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Approve Procurement Plan</span>
                        </button>
                        <button
                          onClick={() => setRejectionModalOpen(true)}
                          disabled={solving}
                          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold text-xs shadow-xs transition-all disabled:opacity-50"
                        >
                          <X className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </button>
                      </>
                    )}

                    {/* Generate Purchase Requisitions */}
                    {(currentPlan.approval_status === "APPROVED" || currentPlan.status === "OPTIMIZED") && currentPlan.status !== "CONVERTED_TO_PO" && (
                      <button
                        onClick={handleGenerateRequisitions}
                        disabled={solving}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs shadow-xs transition-all disabled:opacity-50"
                      >
                        <PackageCheck className="w-3.5 h-3.5" />
                        <span>Dispatch Purchase Requisitions</span>
                      </button>
                    )}

                    {currentPlan.status === "CONVERTED_TO_PO" && (
                      <span className="flex items-center gap-1 px-3 py-1 rounded-lg bg-emerald-100 text-emerald-800 font-bold text-xs">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Requisitions Dispatched
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Baseline Comparison Benchmark Cards */}
              {currentPlan.baseline_comparison && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
                      <TrendingDown className="w-4 h-4 text-emerald-600" />
                      Comparative Procurement Sourcing Baselines & Verified Savings
                    </h4>
                    <span className="text-[11px] text-slate-500 font-mono">
                      Benchmarked against status-quo industry purchasing habits
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Baseline A: Single Consolidated Supplier */}
                    <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 uppercase">
                            Baseline A
                          </span>
                          <Building2 className="w-4 h-4 text-slate-400" />
                        </div>
                        <h5 className="text-sm font-bold text-slate-900 mt-2">Single Consolidated Supplier</h5>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          {currentPlan.baseline_comparison.baseline_a_single_supplier?.description || "Consolidates all materials under one prime vendor to reduce admin overhead."}
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate-500">Selected Vendor:</span>
                          <span className="font-bold text-slate-800 truncate max-w-[140px]">
                            {currentPlan.baseline_comparison.baseline_a_single_supplier?.supplier_name || "N/A"}
                          </span>
                        </div>
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate-500">Expenditure:</span>
                          <span className="font-bold text-slate-900 font-mono">
                            {currentPlan.baseline_comparison.baseline_a_single_supplier?.is_feasible
                              ? `₹${Number(currentPlan.baseline_comparison.baseline_a_single_supplier.total_landed_cost).toLocaleString("en-IN")}`
                              : "Capacity Exceeded"}
                          </span>
                        </div>
                        {currentPlan.baseline_comparison.baseline_a_single_supplier?.is_feasible && (
                          <div className="flex justify-between items-center text-xs pt-1 border-t border-slate-200">
                            <span className="text-emerald-700 font-bold">IndusPilot Savings:</span>
                            <span className="font-black text-emerald-700 font-mono">
                              ₹{Number(currentPlan.baseline_comparison.baseline_a_single_supplier.savings_vs_baseline_a_inr || 0).toLocaleString("en-IN")} ({currentPlan.baseline_comparison.baseline_a_single_supplier.savings_vs_baseline_a_pct}%)
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Baseline B: Cheapest Sourcing Per Material */}
                    <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 uppercase">
                            Baseline B
                          </span>
                          <DollarSign className="w-4 h-4 text-slate-400" />
                        </div>
                        <h5 className="text-sm font-bold text-slate-900 mt-2">Lowest Price Per Material</h5>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          {currentPlan.baseline_comparison.baseline_b_cheapest_per_material?.description || "Selects lowest quoted price per material independently without global optimization."}
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate-500">Suppliers Used:</span>
                          <span className="font-bold text-slate-800">
                            {currentPlan.baseline_comparison.baseline_b_cheapest_per_material?.suppliers_used_count || 1} Vendors
                          </span>
                        </div>
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate-500">Expenditure:</span>
                          <span className="font-bold text-slate-900 font-mono">
                            ₹{Number(currentPlan.baseline_comparison.baseline_b_cheapest_per_material?.total_landed_cost || 0).toLocaleString("en-IN")}
                          </span>
                        </div>
                        <div className="flex justify-between items-center text-xs pt-1 border-t border-slate-200">
                          <span className="text-emerald-700 font-bold">IndusPilot Advantage:</span>
                          <span className="font-black text-emerald-700 font-mono">
                            {currentPlan.baseline_comparison.baseline_b_cheapest_per_material?.savings_vs_baseline_b_inr > 0
                              ? `₹${Number(currentPlan.baseline_comparison.baseline_b_cheapest_per_material.savings_vs_baseline_b_inr).toLocaleString("en-IN")} (${currentPlan.baseline_comparison.baseline_b_cheapest_per_material.savings_vs_baseline_b_pct}%)`
                              : "Pareto Balanced"}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Baseline C: IndusPilot OR-Tools Optimal */}
                    <div className="p-4 rounded-xl bg-blue-50/50 border border-blue-300 shadow-xs space-y-3 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-600 text-white uppercase">
                            IndusPilot Optimal
                          </span>
                          <Sparkles className="w-4 h-4 text-blue-600" />
                        </div>
                        <h5 className="text-sm font-bold text-blue-900 mt-2">Mixed-Integer Linear Allocation</h5>
                        <p className="text-[11px] text-blue-700 mt-0.5">
                          Multi-objective solver simultaneously honoring MOQs, capacities, package multiples, and freight fees.
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-white border border-blue-200 space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate-500">Suppliers Selected:</span>
                          <span className="font-bold text-blue-800">
                            {currentPlan.allocated_suppliers_count || currentPlan.allocations?.length || 0} Vendors
                          </span>
                        </div>
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate-500">Total Landed:</span>
                          <span className="font-black text-blue-950 font-mono text-sm">
                            ₹{Number(currentPlan.total_landed_cost || 0).toLocaleString("en-IN")}
                          </span>
                        </div>
                        <div className="flex justify-between items-center text-xs pt-1 border-t border-blue-100 text-emerald-700 font-bold">
                          <span>Status:</span>
                          <span>{currentPlan.solver_status || "OPTIMAL"}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Allocated Supplier Purchasing Splits */}
              {currentPlan.allocations && currentPlan.allocations.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
                    <Split className="w-4 h-4 text-blue-600" />
                    Recommended Supplier Quota Allocations ({currentPlan.allocations.length} Order Batches)
                  </h4>

                  <div className="overflow-x-auto border border-slate-200 rounded-2xl bg-white shadow-xs">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px]">
                        <tr>
                          <th className="py-3 px-4">Material Requirement</th>
                          <th className="py-3 px-4">Awarded Supplier</th>
                          <th className="py-3 px-4">Allocated Volume</th>
                          <th className="py-3 px-4">Unit Landed</th>
                          <th className="py-3 px-4">Packaging & MOQ</th>
                          <th className="py-3 px-4">Lead Time</th>
                          <th className="py-3 px-4 text-right">Subtotal Landed</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {currentPlan.allocations.map((alloc: any, i: number) => (
                          <tr key={i} className="hover:bg-slate-50/70 transition-colors">
                            <td className="py-3 px-4">
                              <span className="font-bold text-slate-900 block">{alloc.material_name}</span>
                              <span className="text-[10px] text-slate-500 font-mono">{alloc.material_code}</span>
                            </td>
                            <td className="py-3 px-4">
                              <span className="font-bold text-slate-900 block">{alloc.supplier_name}</span>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.2 rounded border border-amber-200">
                                  ★ {alloc.quality_rating || 4.5}
                                </span>
                                {alloc.reliability_score && (
                                  <span className="text-[10px] text-slate-500">
                                    Rel: {alloc.reliability_score}%
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="py-3 px-4">
                              <span className="font-black text-blue-700 font-mono px-2 py-0.5 rounded bg-blue-50 border border-blue-100">
                                {Number(alloc.allocated_quantity).toLocaleString("en-IN")} {alloc.unit}
                              </span>
                            </td>
                            <td className="py-3 px-4 font-mono text-slate-700">
                              ₹{Number(alloc.unit_landed_cost).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/{alloc.unit}
                            </td>
                            <td className="py-3 px-4 text-slate-600">
                              <div className="text-[11px]">
                                {alloc.package_count ? `${alloc.package_count} pkgs` : "Bulk"}
                                <span className="text-slate-400 block text-[10px]">MOQ: {alloc.moq} {alloc.unit} (OK)</span>
                              </div>
                            </td>
                            <td className="py-3 px-4">
                              <span className="font-semibold text-slate-800">{alloc.lead_time_days} days</span>
                            </td>
                            <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                              ₹{Number(alloc.subtotal_cost).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-slate-50 border-t border-slate-200 font-bold text-xs">
                        <tr>
                          <td colSpan={6} className="py-3 px-4 text-right text-slate-600 uppercase tracking-wider text-[11px]">
                            Total Guaranteed Landed Expenditure:
                          </td>
                          <td className="py-3 px-4 text-right font-mono font-black text-sm text-slate-900">
                            ₹{Number(currentPlan.total_landed_cost || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              )}

              {/* Mathematical Constraints Verified */}
              {currentPlan.constraints_satisfied && (
                <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs space-y-2">
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
                    Mathematical Linear Optimization Verification:
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-700">
                    {currentPlan.constraints_satisfied.map((cs: string, idx: number) => (
                      <div key={idx} className="flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                        <span>{cs}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        /* Saved Plans & Approvals History Tab */
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
              Procurement Optimization Records & Managerial Audit Trail
            </h3>
            <button
              onClick={fetchPlanHistory}
              disabled={loadingHistory}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs text-slate-600 hover:bg-slate-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? "animate-spin" : ""}`} />
              <span>Refresh Plans</span>
            </button>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-2xl bg-white shadow-xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px]">
                <tr>
                  <th className="py-3 px-4">Plan Number</th>
                  <th className="py-3 px-4">Strategy</th>
                  <th className="py-3 px-4">Items / Allocations</th>
                  <th className="py-3 px-4">Total Landed Cost</th>
                  <th className="py-3 px-4">Solver Status</th>
                  <th className="py-3 px-4">Approval State</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {historicalPlans.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-400">
                      No procurement plans generated yet. Execute an optimization from the console.
                    </td>
                  </tr>
                ) : (
                  historicalPlans.map((plan) => (
                    <tr key={plan.id} className="hover:bg-slate-50/70">
                      <td className="py-3 px-4 font-mono font-bold text-slate-900">
                        {plan.plan_number}
                        {plan.production_job_id && (
                          <span className="block text-[10px] text-slate-400 font-normal">
                            Job: {plan.production_job_id.slice(0, 8)}...
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-800">
                        {plan.strategy}
                      </td>
                      <td className="py-3 px-4 text-slate-600">
                        {plan.items_count || 1} Materials / {plan.allocations_count || 0} Splits
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-slate-900">
                        ₹{Number(plan.total_landed_cost || 0).toLocaleString("en-IN")}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          plan.solver_status === "OPTIMAL"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                            : "bg-red-50 text-red-700 border-red-300"
                        }`}>
                          {plan.solver_status}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          plan.approval_status === "APPROVED"
                            ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                            : plan.approval_status === "PENDING_APPROVAL"
                            ? "bg-amber-100 text-amber-800 border-amber-300"
                            : plan.approval_status === "REJECTED"
                            ? "bg-red-100 text-red-800 border-red-300"
                            : "bg-slate-100 text-slate-700 border-slate-300"
                        }`}>
                          {plan.approval_status || plan.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleSelectHistoricalPlan(plan.id)}
                          className="px-3 py-1 rounded bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-xs"
                        >
                          Load Plan
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Rejection Reason Modal */}
      {rejectionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-2xs p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold text-slate-900">Reject Procurement Plan</h3>
            <p className="text-xs text-slate-500">
              Provide a clear operational rationale for rejecting this plan. This audit log will be preserved for compliance.
            </p>
            <textarea
              rows={3}
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="e.g. Budget ceiling needs re-allocation with finance team; lead times are too high..."
              className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-900 focus:outline-blue-500"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setRejectionModalOpen(false)}
                className="px-4 py-2 rounded-lg border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleRejectPlan}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
