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
} from "lucide-react";
import { getNegotiationSessions, sendAndSimulateNegotiation, startNegotiation } from "@/lib/api";

export default function NegotiationView({ onApprovalNeeded }: { onApprovalNeeded?: () => void }) {
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [transmitting, setTransmitting] = useState(false);
  const [targetPriceInput, setTargetPriceInput] = useState<number>(295.0);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await getNegotiationSessions();
      setSessions(data);
      if (data.length > 0) {
        setActiveSession(data[0]);
      }
    } catch (err) {
      console.error("Failed to load negotiation sessions:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateRound = async () => {
    if (!activeSession) return;
    try {
      setTransmitting(true);
      const res = await sendAndSimulateNegotiation(activeSession.id);
      await loadSessions();
    } catch (err) {
      console.error("Simulation error:", err);
    } finally {
      setTransmitting(false);
    }
  };

  const states = [
    "DRAFT",
    "READY_FOR_APPROVAL",
    "APPROVED_TO_SEND",
    "SENT",
    "RESPONSE_RECEIVED",
    "ACCEPTANCE_PROPOSED",
    "CLOSED",
  ];

  const getStateIndex = (st: string) => {
    const idx = states.indexOf(st);
    return idx === -1 ? 1 : idx;
  };

  const activeIdx = activeSession ? getStateIndex(activeSession.status) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <Handshake className="w-5 h-5 text-blue-600" />
          <span>Autonomous AI Supplier Negotiation Centre</span>
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Formulates evidence-backed counteroffers based on order volumes and market benchmarks.
          Features multi-round concession curve simulation and mandatory human authorization.
        </p>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
          Loading negotiation dialogues...
        </div>
      ) : !activeSession ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
          No negotiation sessions found. Click "Seed Demo Data" to load initial session.
        </div>
      ) : (
        <div className="space-y-6">
          {/* State Machine Visualizer */}
          <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
              Negotiation State Lifecycle
            </div>
            <div className="flex items-center justify-between overflow-x-auto pb-2 gap-2 text-[11px]">
              {states.map((st, i) => {
                const isPassed = i < activeIdx;
                const isCurrent = i === activeIdx;
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
                    {i < states.length - 1 && (
                      <span className="text-slate-400 font-bold">$\to$</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Active Negotiation Console */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column: Target & Savings Card */}
            <div className="space-y-4">
              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
                <div className="border-b border-slate-200 pb-3">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                    Vendor in Negotiation
                  </span>
                  <h3 className="text-base font-bold text-slate-900 mt-0.5">
                    {activeSession.supplier_name}
                  </h3>
                  <div className="text-xs text-slate-500 mt-1">
                    Material: <b className="text-slate-800">{activeSession.material_name}</b>
                    <br />
                    Volume: <b className="text-slate-800">{activeSession.quantity} kg</b>
                  </div>
                </div>

                {/* Economics summary */}
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between p-2.5 rounded bg-slate-50 border border-slate-200">
                    <span className="text-slate-500">Opening Quote:</span>
                    <span className="font-mono font-semibold text-slate-800">
                      ₹{activeSession.original_unit_price.toFixed(2)} / kg
                    </span>
                  </div>
                  <div className="flex justify-between p-2.5 rounded bg-slate-50 border border-slate-200">
                    <span className="text-slate-500">Target Counter Price:</span>
                    <span className="font-mono font-bold text-blue-700">
                      ₹{activeSession.target_unit_price.toFixed(2)} / kg
                    </span>
                  </div>
                  <div className="flex justify-between p-2.5 rounded bg-blue-50 border border-blue-200">
                    <span className="text-blue-800 font-bold">Current Active Offer:</span>
                    <span className="font-mono font-extrabold text-blue-900">
                      ₹{activeSession.current_offered_price.toFixed(2)} / kg
                    </span>
                  </div>
                </div>

                {/* Savings counter */}
                {activeSession.current_offered_price < activeSession.original_unit_price && (
                  <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
                    <div className="flex items-center gap-1.5 font-bold">
                      <TrendingDown className="w-4 h-4 text-emerald-600" />
                      <span>Captured Batch Savings</span>
                    </div>
                    <div className="text-lg font-black font-mono mt-1 text-emerald-900">
                      ₹
                      {(
                        (activeSession.original_unit_price - activeSession.current_offered_price) *
                        activeSession.quantity
                      ).toLocaleString("en-IN")}
                    </div>
                    <div className="text-[11px] text-emerald-700 mt-0.5">
                      Concession of ₹
                      {(activeSession.original_unit_price - activeSession.current_offered_price).toFixed(
                        2
                      )}
                      /kg obtained
                    </div>
                  </div>
                )}

                {/* Human approval trigger action */}
                <div className="pt-2">
                  <button
                    onClick={handleSimulateRound}
                    disabled={transmitting}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-50"
                  >
                    <Send className={`w-4 h-4 ${transmitting ? "animate-spin" : ""}`} />
                    <span>
                      {transmitting
                        ? "Transmitting & Simulating Reply..."
                        : "Approve & Dispatch Counteroffer"}
                    </span>
                  </button>
                  <p className="text-[10px] text-slate-500 text-center mt-2">
                    ⚠️ Human Authorization Safeguard: Simulates realistic vendor concession curve.
                  </p>
                </div>
              </div>
            </div>

            {/* Right Column: Negotiation Thread & Email Messages */}
            <div className="lg:col-span-2 p-5 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-slate-200 pb-3 mb-4">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-teal-600" />
                    <h4 className="text-sm font-bold text-slate-900">
                      Dialogue Thread & Generated Communications
                    </h4>
                  </div>
                  <span className="text-[11px] text-slate-500">
                    Rounds Logged: <b className="text-slate-800">{activeSession.messages?.length || 0}</b>
                  </span>
                </div>

                <div className="space-y-3.5 max-h-[460px] overflow-y-auto pr-2">
                  {activeSession.messages?.map((msg: any, idx: number) => {
                    const isAgent = msg.sender_type === "BUYER_AGENT";
                    return (
                      <div
                        key={idx}
                        className={`p-4 rounded-xl text-xs space-y-2 border ${
                          isAgent
                            ? "bg-slate-50 border-slate-200 text-slate-800"
                            : "bg-teal-50/40 border-teal-200 text-slate-800"
                        }`}
                      >
                        <div className="flex items-center justify-between text-[11px] font-bold">
                          <div className="flex items-center gap-1.5">
                            {isAgent ? (
                              <Bot className="w-4 h-4 text-blue-600" />
                            ) : (
                              <Building2 className="w-4 h-4 text-teal-600" />
                            )}
                            <span className={isAgent ? "text-blue-700" : "text-teal-700"}>
                              {isAgent ? "IndusPilot Buyer Agent" : activeSession.supplier_name}
                            </span>
                            <span className="text-slate-400">• Round {msg.round_number}</span>
                          </div>
                          {msg.proposed_unit_price && (
                            <span className="px-2 py-0.5 rounded bg-white border border-slate-200 font-mono text-slate-800 font-bold">
                              Rate: ₹{msg.proposed_unit_price.toFixed(2)}/kg
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
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

