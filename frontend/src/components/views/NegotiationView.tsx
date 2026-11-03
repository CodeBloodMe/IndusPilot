"use client";

import React, { useState, useEffect } from "react";
import {
  Handshake,
  Send,
  CheckCircle2,
  AlertCircle,
  TrendingDown,
  Sparkles,
  Bot,
  User,
  Building2,
  ShieldAlert,
  ArrowRight,
  RefreshCw,
  FileText,
  Check,
  X,
  ShieldCheck,
  Scale,
  Award,
  ArrowUpRight,
  Languages,
  Sliders,
  DollarSign,
  Layers,
  ChevronRight,
} from "lucide-react";
import {
  getNegotiationSessions,
  getNegotiationSession,
  generateNegotiationMessage,
  approveNegotiationMessage,
  simulateNegotiationResponse,
  finalizeNegotiationAgreement,
  createNegotiationSession,
  getSuppliers,
  getQuotations,
} from "@/lib/api";

const STRATEGIES = [
  { id: "VOLUME_COMMITMENT", label: "Volume Commitment", desc: "Leverage aggregate batch demand for volume tier discounts" },
  { id: "BENCHMARK_PARITY", label: "Benchmark Parity", desc: "Reference prevailing industrial index & regional raw material rates" },
  { id: "PAYMENT_ACCELERATION", label: "Payment Acceleration", desc: "Offer 10-15 day prompt payment in exchange for cash rebate" },
  { id: "LONG_TERM_CONTRACT", label: "Long-Term Contract", desc: "Propose quarterly blanket order in exchange for fixed price lock" },
  { id: "SPOT_CLEARANCE", label: "Spot Clearance", desc: "Offer immediate off-take for existing mill stocks and coils" },
];

const LANGUAGES = [
  { id: "en", label: "English", desc: "Formal Commercial Tender" },
  { id: "hi", label: "Hindi (हिंदी)", desc: "Formal Hindi Trade Register" },
  { id: "hinglish", label: "Hinglish", desc: "Standard Indian Industrial Trade" },
];

const LIFECYCLE_STEPS = [
  "DRAFT",
  "AWAITING_APPROVAL",
  "APPROVED_TO_SEND",
  "SENT",
  "RESPONSE_RECEIVED",
  "CONCESSION_OFFERED",
  "ACCEPTANCE_PROPOSED",
  "AGREEMENT_REACHED",
];

export default function NegotiationView({ onApprovalNeeded }: { onApprovalNeeded?: () => void }) {
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [selectedStrategy, setSelectedStrategy] = useState<string>("VOLUME_COMMITMENT");
  const [selectedLanguage, setSelectedLanguage] = useState<string>("en");
  const [targetPrice, setTargetPrice] = useState<number>(295.0);
  const [maxWalkawayPrice, setMaxWalkawayPrice] = useState<number>(315.0);
  const [editableMessage, setEditableMessage] = useState<string>("");
  const [pendingMessageId, setPendingMessageId] = useState<string | null>(null);
  const [simulationScenario, setSimulationScenario] = useState<string>("CONCESSION");
  const [showNewModal, setShowNewModal] = useState<boolean>(false);
  const [verifiedQuotations, setVerifiedQuotations] = useState<any[]>([]);
  const [selectedQuoteId, setSelectedQuoteId] = useState<string>("");
  const [notice, setNotice] = useState<{ type: "success" | "error" | "info"; message: string } | null>(null);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async (selectId?: string) => {
    try {
      setLoading(true);
      const data = await getNegotiationSessions();
      setSessions(data || []);
      if (data && data.length > 0) {
        const toSelect = selectId ? data.find((s: any) => s.id === selectId) || data[0] : data[0];
        await selectSession(toSelect.id);
      } else {
        setActiveSession(null);
      }
    } catch (err: any) {
      console.error("Failed to load negotiation sessions:", err);
      showNotice("error", err.message || "Failed to load negotiation sessions.");
    } finally {
      setLoading(false);
    }
  };

  const selectSession = async (sessionId: string) => {
    try {
      const full = await getNegotiationSession(sessionId);
      setActiveSession(full);
      setSelectedStrategy(full.strategy || "VOLUME_COMMITMENT");
      setSelectedLanguage(full.language || "en");
      setTargetPrice(full.target_unit_price || 295.0);
      setMaxWalkawayPrice(full.max_walkaway_price || full.original_unit_price || 315.0);

      // Check for pending approval messages
      const msgs = full.messages || [];
      const pending = msgs.find((m: any) => m.sender_type === "BUYER_AGENT" && !m.is_approved);
      if (pending) {
        setPendingMessageId(pending.id);
        setEditableMessage(pending.message_text);
      } else {
        setPendingMessageId(null);
        setEditableMessage("");
      }
    } catch (err: any) {
      console.error("Failed to select session:", err);
    }
  };

  const showNotice = (type: "success" | "error" | "info", message: string) => {
    setNotice({ type, message });
    setTimeout(() => setNotice(null), 6000);
  };

  const handleGenerateMessage = async () => {
    if (!activeSession) return;
    try {
      setActionLoading(true);
      const res = await generateNegotiationMessage(activeSession.id, {
        strategy: selectedStrategy,
        language: selectedLanguage,
        target_unit_price: targetPrice,
      });
      setEditableMessage(res.message_text || "");
      setPendingMessageId(res.message_id || null);
      await selectSession(activeSession.id);
      showNotice("success", "AI Counteroffer draft created! Review terms and authorize transmission.");
      if (onApprovalNeeded) onApprovalNeeded();
    } catch (err: any) {
      showNotice("error", err.message || "Failed to generate message draft.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleApproveMessage = async () => {
    if (!pendingMessageId) return;
    try {
      setActionLoading(true);
      await approveNegotiationMessage(pendingMessageId, "Procurement Director");
      await selectSession(activeSession.id);
      setPendingMessageId(null);
      showNotice("success", "Counteroffer authorized and queued for supplier transmission.");
    } catch (err: any) {
      showNotice("error", err.message || "Failed to approve message.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleSimulateResponse = async () => {
    if (!activeSession) return;
    try {
      setActionLoading(true);
      const res = await simulateNegotiationResponse(activeSession.id, simulationScenario);
      await selectSession(activeSession.id);
      const concession = res.net_savings_abs > 0 ? `₹${res.net_savings_abs.toLocaleString("en-IN")}` : "0";
      showNotice("info", `Supplier reply simulated: ${res.classification}. Landed savings: ${concession}.`);
    } catch (err: any) {
      showNotice("error", err.message || "Simulation failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleFinalizeAgreement = async () => {
    if (!activeSession) return;
    try {
      setActionLoading(true);
      const res = await finalizeNegotiationAgreement(activeSession.id, {
        agreed_unit_price: activeSession.current_offered_price,
        notes: "Formally concluded via IndusPilot Autonomous Negotiation Engine.",
      });
      await selectSession(activeSession.id);
      showNotice("success", `Agreement Finalized! Revised quotation created (v${res.revised_quotation_version || 2}) at ₹${res.agreed_unit_price}/kg.`);
    } catch (err: any) {
      showNotice("error", err.message || "Failed to finalize agreement.");
    } finally {
      setActionLoading(false);
    }
  };

  const openNewSessionModal = async () => {
    try {
      const quotes = await getQuotations(undefined, "VERIFIED");
      setVerifiedQuotations(quotes || []);
      if (quotes && quotes.length > 0) {
        setSelectedQuoteId(quotes[0].id);
      }
      setShowNewModal(true);
    } catch (err) {
      console.error("Failed to load quotes for modal:", err);
    }
  };

  const handleCreateSession = async () => {
    if (!selectedQuoteId) return;
    try {
      setActionLoading(true);
      const res = await createNegotiationSession({
        quotation_id: selectedQuoteId,
        strategy: selectedStrategy,
        language: selectedLanguage,
        target_unit_price: targetPrice,
      });
      setShowNewModal(false);
      await loadSessions(res.session_id);
      showNotice("success", "New autonomous negotiation session created.");
    } catch (err: any) {
      showNotice("error", err.message || "Failed to create negotiation session.");
    } finally {
      setActionLoading(false);
    }
  };

  const getStepIndex = (st: string) => {
    const idx = LIFECYCLE_STEPS.indexOf(st);
    return idx === -1 ? 1 : idx;
  };

  const currentStepIdx = activeSession ? getStepIndex(activeSession.status) : 0;
  const isApproved = activeSession?.status === "AGREEMENT_REACHED";
  const hasSavings = (activeSession?.net_savings_abs || 0) > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Handshake className="w-5 h-5 text-blue-600" />
            <span>Agentic Supplier Negotiation & Commercial Guard</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Autonomous agentic negotiation with multi-language phrasing (EN, HI, Hinglish), human commercial gates,
            deterministic 9-component landed cost recalculation, and reproducible concession simulation.
          </p>
        </div>

        <button
          onClick={openNewSessionModal}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all self-start sm:self-auto"
        >
          <Sparkles className="w-4 h-4" />
          <span>New Negotiation Session</span>
        </button>
      </div>

      {/* Notice Banner */}
      {notice && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center justify-between transition-all ${
            notice.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : notice.type === "error"
              ? "bg-red-50 border-red-200 text-red-800"
              : "bg-blue-50 border-blue-200 text-blue-800"
          }`}
        >
          <div className="flex items-center gap-2">
            {notice.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : notice.type === "error" ? (
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            ) : (
              <Sparkles className="w-4 h-4 text-blue-600 shrink-0" />
            )}
            <span>{notice.message}</span>
          </div>
          <button onClick={() => setNotice(null)} className="text-xs font-bold opacity-70 hover:opacity-100">
            ✕
          </button>
        </div>
      )}

      {/* Session Selector Bar */}
      {sessions.length > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          <span className="text-slate-500 font-semibold whitespace-nowrap">Active Sessions:</span>
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => selectSession(s.id)}
              className={`px-3 py-1.5 rounded-lg font-medium text-xs border transition-all whitespace-nowrap flex items-center gap-2 ${
                activeSession?.id === s.id
                  ? "bg-blue-600 text-white border-blue-600 shadow-xs"
                  : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
              }`}
            >
              <span>{s.supplier_name}</span>
              <span className="font-mono text-[10px] opacity-80">({s.status})</span>
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
          Loading negotiation engine...
        </div>
      ) : !activeSession ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
          No negotiation sessions found. Click "New Negotiation Session" to begin negotiating.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Lifecycle State Machine Stepper */}
          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                16-State Lifecycle Machine
              </span>
              <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                Current State: {activeSession.status}
              </span>
            </div>
            <div className="flex items-center justify-between overflow-x-auto pb-2 gap-2 text-[11px]">
              {LIFECYCLE_STEPS.map((st, i) => {
                const isPassed = i < currentStepIdx;
                const isCurrent = i === currentStepIdx;
                return (
                  <div key={st} className="flex items-center gap-2 shrink-0">
                    <div
                      className={`px-3 py-1.5 rounded-lg font-mono font-bold flex items-center gap-1.5 ${
                        isCurrent
                          ? "bg-blue-600 text-white ring-2 ring-blue-300 shadow-xs"
                          : isPassed
                          ? "bg-blue-50 text-blue-700 border border-blue-200"
                          : "bg-slate-50 text-slate-400 border border-slate-200"
                      }`}
                    >
                      {isPassed && <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />}
                      <span>{st.replace(/_/g, " ")}</span>
                    </div>
                    {i < LIFECYCLE_STEPS.length - 1 && (
                      <ChevronRight className="w-3.5 h-3.5 text-slate-300 shrink-0" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Main 2-Column Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column: Commercial Controls & Economics */}
            <div className="space-y-5">
              {/* Supplier & Deal Overview */}
              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
                <div className="border-b border-slate-200 pb-3">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                    Counterparty
                  </span>
                  <h3 className="text-base font-bold text-slate-900 mt-0.5">{activeSession.supplier_name}</h3>
                  <div className="text-xs text-slate-500 mt-1">
                    Material: <b className="text-slate-800">{activeSession.material_name}</b>
                    <br />
                    Order Volume: <b className="text-slate-800">{activeSession.quantity.toLocaleString("en-IN")} kg</b>
                  </div>
                </div>

                {/* Economics Matrix */}
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between p-2.5 rounded bg-slate-50 border border-slate-200">
                    <span className="text-slate-500">Opening Quote:</span>
                    <span className="font-mono font-semibold text-slate-800">
                      ₹{activeSession.original_unit_price?.toFixed(2)} / kg
                    </span>
                  </div>
                  <div className="flex justify-between p-2.5 rounded bg-slate-50 border border-slate-200">
                    <span className="text-slate-500">Target Counter Price:</span>
                    <span className="font-mono font-bold text-blue-700">
                      ₹{activeSession.target_unit_price?.toFixed(2)} / kg
                    </span>
                  </div>
                  <div className="flex justify-between p-2.5 rounded bg-blue-50 border border-blue-200">
                    <span className="text-blue-800 font-bold">Current Active Offer:</span>
                    <span className="font-mono font-extrabold text-blue-900">
                      ₹{activeSession.current_offered_price?.toFixed(2)} / kg
                    </span>
                  </div>
                </div>

                {/* Captured Savings Banner */}
                {hasSavings && (
                  <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
                    <div className="flex items-center gap-1.5 font-bold">
                      <TrendingDown className="w-4 h-4 text-emerald-600" />
                      <span>Captured Batch Savings</span>
                    </div>
                    <div className="text-xl font-black font-mono mt-1 text-emerald-900">
                      ₹{activeSession.net_savings_abs?.toLocaleString("en-IN")}
                    </div>
                    <div className="text-[11px] text-emerald-700 mt-0.5">
                      Concession: ₹
                      {(activeSession.original_unit_price - activeSession.current_offered_price).toFixed(2)} / kg (
                      {activeSession.net_savings_pct?.toFixed(2)}% net reduction)
                    </div>
                  </div>
                )}

                {/* Finalize Agreement Button */}
                {activeSession.status !== "AGREEMENT_REACHED" && (
                  <button
                    onClick={handleFinalizeAgreement}
                    disabled={actionLoading}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Conclude Agreement & Revise Quote</span>
                  </button>
                )}
                {activeSession.status === "AGREEMENT_REACHED" && (
                  <div className="p-3 rounded-lg bg-emerald-100 border border-emerald-300 text-emerald-800 text-xs font-bold text-center flex items-center justify-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-700" />
                    <span>Agreement Finalized & Quotation Revised</span>
                  </div>
                )}
              </div>

              {/* Strategy & Phrasing Configuration */}
              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
                <div className="border-b border-slate-200 pb-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <Sliders className="w-3.5 h-3.5 text-blue-600" />
                    <span>Commercial Strategy</span>
                  </h4>
                </div>

                {/* 5 Strategies Selector */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-slate-600 block">Strategy Formulation:</label>
                  <select
                    value={selectedStrategy}
                    onChange={(e) => setSelectedStrategy(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-xs text-slate-800 font-medium"
                  >
                    {STRATEGIES.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                  <p className="text-[10px] text-slate-500">
                    {STRATEGIES.find((s) => s.id === selectedStrategy)?.desc}
                  </p>
                </div>

                {/* Language Phrasing Selector */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-slate-600 flex items-center gap-1">
                    <Languages className="w-3.5 h-3.5 text-slate-400" />
                    <span>Communication Language:</span>
                  </label>
                  <div className="grid grid-cols-3 gap-1.5">
                    {LANGUAGES.map((l) => (
                      <button
                        key={l.id}
                        type="button"
                        onClick={() => setSelectedLanguage(l.id)}
                        className={`py-1.5 px-2 rounded-lg text-xs font-semibold border text-center transition-all ${
                          selectedLanguage === l.id
                            ? "bg-blue-600 text-white border-blue-600 shadow-2xs"
                            : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                        }`}
                      >
                        {l.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Target Price Input */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-slate-600 block">
                    Target Counter Unit Price (₹/kg):
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={targetPrice}
                    onChange={(e) => setTargetPrice(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-xs font-mono font-bold text-slate-900"
                  />
                </div>

                {/* Generate Button */}
                <button
                  onClick={handleGenerateMessage}
                  disabled={actionLoading}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-50"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Draft AI Counteroffer</span>
                </button>
              </div>

              {/* Simulation Testing Tool */}
              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3">
                <div className="border-b border-slate-200 pb-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <Bot className="w-3.5 h-3.5 text-teal-600" />
                    <span>Concession Simulator</span>
                  </h4>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-slate-600 block">Simulate Vendor Scenario:</label>
                  <select
                    value={simulationScenario}
                    onChange={(e) => setSimulationScenario(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-xs text-slate-800"
                  >
                    <option value="CONCESSION">CONCESSION (Realistic concession curve)</option>
                    <option value="FIRM">FIRM (Supplier holds initial quotation rate)</option>
                    <option value="COUNTER">COUNTER (Supplier offers split compromise)</option>
                    <option value="REJECT">REJECT (Supplier declines counteroffer)</option>
                  </select>
                </div>

                <button
                  onClick={handleSimulateResponse}
                  disabled={actionLoading}
                  className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs shadow-2xs transition-all disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${actionLoading ? "animate-spin" : ""}`} />
                  <span>Simulate Vendor Reply</span>
                </button>
                <p className="text-[10px] text-slate-400 text-center">
                  ⚠️ Tagged as [SIMULATED] in dialogue history for audit transparency.
                </p>
              </div>
            </div>

            {/* Right 2 Columns: Human Approval Gate & Dialogue Feed */}
            <div className="lg:col-span-2 space-y-5">
              {/* Human Governance Approval Banner & Editor */}
              {pendingMessageId && (
                <div className="p-5 rounded-xl bg-amber-50/70 border border-amber-300 shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ShieldAlert className="w-5 h-5 text-amber-700" />
                      <h4 className="text-sm font-bold text-amber-900">
                        Human Authorization Required: Review Draft Message
                      </h4>
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-200 text-amber-900 font-mono">
                      AWAITING_APPROVAL
                    </span>
                  </div>

                  <p className="text-xs text-amber-800">
                    The AI agent has drafted the following counteroffer. You may edit the message text or modify commercial
                    clauses before approving and transmitting to the supplier.
                  </p>

                  <textarea
                    rows={6}
                    value={editableMessage}
                    onChange={(e) => setEditableMessage(e.target.value)}
                    className="w-full bg-white border border-amber-200 rounded-lg p-3 text-xs font-mono text-slate-800 leading-relaxed shadow-inner"
                  />

                  <div className="flex justify-end gap-2 pt-1">
                    <button
                      onClick={handleApproveMessage}
                      disabled={actionLoading}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs shadow-sm transition-all"
                    >
                      <Check className="w-4 h-4" />
                      <span>Authorize & Transmit to Supplier</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Dialogue Thread */}
              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between border-b border-slate-200 pb-3 mb-4">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-blue-600" />
                      <h4 className="text-sm font-bold text-slate-900">
                        Negotiation Dialogue Thread & Concession History
                      </h4>
                    </div>
                    <span className="text-[11px] text-slate-500">
                      Rounds Logged: <b className="text-slate-800">{activeSession.messages?.length || 0}</b>
                    </span>
                  </div>

                  {(!activeSession.messages || activeSession.messages.length === 0) ? (
                    <div className="p-8 text-center text-xs text-slate-400">
                      No communications recorded yet. Click "Draft AI Counteroffer" to formulate the first round.
                    </div>
                  ) : (
                    <div className="space-y-4 max-h-[560px] overflow-y-auto pr-2">
                      {activeSession.messages.map((msg: any, idx: number) => {
                        const isBuyer = msg.sender_type === "BUYER_AGENT";
                        return (
                          <div
                            key={idx}
                            className={`p-4 rounded-xl text-xs space-y-2 border ${
                              isBuyer
                                ? "bg-slate-50 border-slate-200 text-slate-800"
                                : "bg-blue-50/40 border-blue-200 text-slate-800"
                            }`}
                          >
                            <div className="flex items-center justify-between text-[11px] font-bold">
                              <div className="flex items-center gap-1.5">
                                {isBuyer ? (
                                  <Bot className="w-4 h-4 text-blue-600" />
                                ) : (
                                  <Building2 className="w-4 h-4 text-teal-600" />
                                )}
                                <span className={isBuyer ? "text-blue-700" : "text-teal-700"}>
                                  {isBuyer ? "IndusPilot Commercial Agent" : activeSession.supplier_name}
                                </span>
                                <span className="text-slate-400">• Round {msg.round_number}</span>
                                {msg.is_simulated && (
                                  <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-mono text-[9px]">
                                    [SIMULATED]
                                  </span>
                                )}
                                {isBuyer && (
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                                      msg.is_approved
                                        ? "bg-emerald-100 text-emerald-800"
                                        : "bg-amber-100 text-amber-800"
                                    }`}
                                  >
                                    {msg.is_approved ? "APPROVED" : "DRAFT"}
                                  </span>
                                )}
                              </div>
                              {msg.proposed_unit_price && (
                                <span className="px-2 py-0.5 rounded bg-white border border-slate-200 font-mono text-slate-800 font-bold">
                                  Offered: ₹{msg.proposed_unit_price.toFixed(2)}/kg
                                </span>
                              )}
                            </div>

                            <div className="whitespace-pre-line text-slate-700 font-mono text-[11px] leading-relaxed bg-white p-3 rounded-lg border border-slate-200 shadow-xs">
                              {msg.message_text}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* New Negotiation Session Modal */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900">Initiate Supplier Negotiation Session</h3>
              <button
                onClick={() => setShowNewModal(false)}
                className="text-slate-400 hover:text-slate-700 text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="text-slate-600 block mb-1 font-semibold">Select Verified Supplier Quotation:</label>
                <select
                  value={selectedQuoteId}
                  onChange={(e) => setSelectedQuoteId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-medium"
                >
                  {verifiedQuotations.map((q) => (
                    <option key={q.id} value={q.id}>
                      {q.supplier_name || "Supplier"} — {q.quotation_number} (₹{q.total_amount?.toLocaleString("en-IN")})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-slate-600 block mb-1 font-semibold">Initial Negotiation Strategy:</label>
                <select
                  value={selectedStrategy}
                  onChange={(e) => setSelectedStrategy(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
                >
                  {STRATEGIES.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-600 block mb-1 font-semibold">Target Discount (%):</label>
                  <input
                    type="number"
                    defaultValue={6.5}
                    step="0.5"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-600 block mb-1 font-semibold">Language Phrasing:</label>
                  <select
                    value={selectedLanguage}
                    onChange={(e) => setSelectedLanguage(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
                  >
                    {LANGUAGES.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleCreateSession}
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-50"
                >
                  {actionLoading ? "Initializing..." : "Create Negotiation Session"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
