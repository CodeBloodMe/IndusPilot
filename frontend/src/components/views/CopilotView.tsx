"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Bot,
  Send,
  User,
  Sparkles,
  Globe2,
  CheckCircle2,
  ArrowRight,
  ShieldAlert,
  Plus,
  Trash2,
  Clock,
  Layers,
  Activity,
  Check,
  X,
  ChevronRight,
  FileText,
  TrendingUp,
  AlertTriangle,
  Cpu,
  Boxes,
  Loader2,
  Maximize2
} from "lucide-react";
import {
  getCopilotConversations,
  createCopilotConversation,
  getCopilotConversation,
  deleteCopilotConversation,
  postCopilotMessage,
  approveCopilotAction,
  rejectCopilotAction,
  getCopilotRunEvents
} from "@/lib/api";

interface Conversation {
  id: string;
  title: string;
  is_archived: boolean;
  messages_count?: number;
  last_message_preview?: string;
  updated_at?: string;
  created_at: string;
}

interface StepEvent {
  step_number: number;
  agent: string;
  event_type: string;
  description: string;
  status: string;
  time: string;
}

export default function CopilotView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  // State
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingConv, setLoadingConv] = useState(false);
  const [activeRunEvents, setActiveRunEvents] = useState<StepEvent[]>([]);
  const [showActivityPanel, setShowActivityPanel] = useState(true);
  const [actionProcessing, setActionProcessing] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Suggested Prompts
  const samplePrompts = [
    {
      label: "Master Workflow (SS304 Brackets)",
      query: "I have received an order for 500 stainless steel industrial brackets. Check inventory, find required materials, optimise procurement within 5 lakh and calculate profit at 20% margin."
    },
    {
      label: "Supplier Comparison",
      query: "Compare supplier quotations and identify the top candidate for SS304 plate."
    },
    {
      label: "Hinglish MRP Shortage Check",
      query: "500 brackets ke liye material shortage check karo aur batao kitna stock chahiye."
    },
    {
      label: "14-Factor Production Costing",
      query: "Calculate 14-factor manufacturing cost breakdown for 500 industrial brackets."
    },
    {
      label: "OR-Tools MILP Optimization",
      query: "Optimize procurement allocation for stainless steel using OR-Tools MILP solver under ₹5 Lakh budget."
    }
  ];

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const loadConversations = async () => {
    try {
      const data = await getCopilotConversations();
      if (Array.isArray(data) && data.length > 0) {
        setConversations(data);
        if (!activeConvId) {
          selectConversation(data[0].id);
        }
      } else {
        // Create initial default conversation
        const newConv = await createCopilotConversation("Manufacturing Copilot Session");
        setConversations([newConv]);
        selectConversation(newConv.id);
      }
    } catch (err) {
      console.error("Failed to load conversations:", err);
    }
  };

  const selectConversation = async (id: string) => {
    setActiveConvId(id);
    setLoadingConv(true);
    try {
      const details = await getCopilotConversation(id);
      setMessages(details.messages || []);

      // If the latest message has a run_id, load its execution events
      const lastBotMsg = (details.messages || []).slice().reverse().find((m: any) => m.role === "assistant" && m.run_id);
      if (lastBotMsg?.run_id) {
        loadRunEvents(lastBotMsg.run_id);
      } else {
        setActiveRunEvents([]);
      }
    } catch (err) {
      console.error("Failed to fetch conversation details:", err);
    } finally {
      setLoadingConv(false);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await createCopilotConversation("New Manufacturing Discussion");
      setConversations([newConv, ...conversations]);
      setActiveConvId(newConv.id);
      setMessages(newConv.messages || []);
      setActiveRunEvents([]);
    } catch (err) {
      console.error("Failed to create conversation:", err);
    }
  };

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteCopilotConversation(id);
      const updated = conversations.filter(c => c.id !== id);
      setConversations(updated);
      if (activeConvId === id) {
        if (updated.length > 0) {
          selectConversation(updated[0].id);
        } else {
          handleNewConversation();
        }
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  const loadRunEvents = async (runId: string) => {
    try {
      const events = await getCopilotRunEvents(runId);
      setActiveRunEvents(events || []);
    } catch (err) {
      console.error("Failed to load run events:", err);
    }
  };

  const handleSend = async (queryText?: string) => {
    const q = (queryText || inputQuery).trim();
    if (!q || !activeConvId) return;

    // Optimistically append user message
    const optimisticMsg = {
      id: `user-${Date.now()}`,
      role: "user",
      content: q,
      created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages(prev => [...prev, optimisticMsg]);
    setInputQuery("");
    setSending(true);

    try {
      const res = await postCopilotMessage(activeConvId, q);
      const assistantMsg = res.message;
      setMessages(prev => [...prev, assistantMsg]);

      if (res.step_trace && Array.isArray(res.step_trace)) {
        setActiveRunEvents(res.step_trace.map((s: any, idx: number) => ({
          step_number: idx + 1,
          agent: s.agent_name || s.agent,
          event_type: s.step_type || s.event_type,
          description: s.description,
          status: s.status || "COMPLETED",
          time: s.timestamp || new Date().toLocaleTimeString()
        })));
      } else if (assistantMsg.run_id) {
        loadRunEvents(assistantMsg.run_id);
      }

      // Update conversation title in list if updated
      loadConversations();
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          agent_name: "Supervisor Error Handler",
          content: `Unable to coordinate agent workflow: ${err.message}`,
          created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleActionDecision = async (actionId: string, decision: "APPROVE" | "REJECT") => {
    setActionProcessing(actionId);
    try {
      if (decision === "APPROVE") {
        await approveCopilotAction(actionId, {
          approver_name: "Plant Head / Commercial Director",
          reason: "Approved commercial quotation dispatch after verifying landed margin."
        });
      } else {
        await rejectCopilotAction(actionId, {
          approver_name: "Plant Head / Commercial Director",
          reason: "Margin threshold renegotiation requested."
        });
      }
      // Reload current conversation messages
      if (activeConvId) {
        selectConversation(activeConvId);
      }
    } catch (err: any) {
      alert(`Action error: ${err.message}`);
    } finally {
      setActionProcessing(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Bot className="w-6 h-6 text-blue-600" />
            <span>AI Manufacturing Copilot & Multi-Agent Supervisor</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Deterministic LangGraph orchestration coordinating 9 specialized agents across BOM, Inventory, Google OR-Tools, 14-Factor Costing, and Customer Quotes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-xs text-blue-700 font-semibold shadow-2xs">
            <Globe2 className="w-4 h-4 text-blue-600" />
            <span>English • हिंदी • Hinglish NLU</span>
          </div>
          <button
            onClick={() => setShowActivityPanel(!showActivityPanel)}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-all ${
              showActivityPanel
                ? "bg-slate-900 text-white border-slate-900 shadow-2xs"
                : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>{showActivityPanel ? "Hide Agent Activity" : "Show Agent Activity"}</span>
          </button>
        </div>
      </div>

      {/* Suggested Prompt Chips */}
      <div className="flex flex-wrap gap-2">
        {samplePrompts.map((p, i) => (
          <button
            key={i}
            onClick={() => handleSend(p.query)}
            disabled={sending}
            className="text-xs px-3 py-1.5 rounded-lg bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-300 transition-all text-left flex items-center gap-1.5 shadow-2xs group disabled:opacity-50"
          >
            <Sparkles className="w-3 h-3 text-blue-600 shrink-0 group-hover:scale-110 transition-transform" />
            <span className="font-medium">{p.label}</span>
          </button>
        ))}
      </div>

      {/* Main 3-Column Layout */}
      <div className="grid grid-cols-12 gap-4 h-[680px]">
        {/* 1. Left Sidebar: Conversation History */}
        <div className="col-span-12 md:col-span-3 bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col overflow-hidden">
          <div className="p-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-600" />
              <span>Sessions</span>
            </span>
            <button
              onClick={handleNewConversation}
              className="px-2.5 py-1 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center gap-1 transition-all shadow-2xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {conversations.map(c => {
              const isActive = c.id === activeConvId;
              return (
                <div
                  key={c.id}
                  onClick={() => selectConversation(c.id)}
                  className={`p-2.5 rounded-lg cursor-pointer transition-all flex items-start justify-between group ${
                    isActive
                      ? "bg-blue-50 border border-blue-200 text-blue-900 shadow-2xs font-medium"
                      : "hover:bg-slate-50 text-slate-700 border border-transparent"
                  }`}
                >
                  <div className="min-w-0 flex-1 pr-2">
                    <div className="text-xs font-semibold truncate text-slate-900">
                      {c.title}
                    </div>
                    {c.last_message_preview && (
                      <div className="text-[11px] text-slate-500 truncate mt-0.5">
                        {c.last_message_preview}
                      </div>
                    )}
                    <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
                      <Clock className="w-2.5 h-2.5" />
                      <span>{c.updated_at || "Recent"}</span>
                    </div>
                  </div>

                  <button
                    onClick={(e) => handleDeleteConversation(c.id, e)}
                    className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-600 p-1 rounded transition-all"
                    title="Delete Conversation"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* 2. Center Chat Workspace */}
        <div className={`col-span-12 ${showActivityPanel ? "md:col-span-6" : "md:col-span-9"} bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col overflow-hidden`}>
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {loadingConv ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-500 gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                <span>Loading discussion history...</span>
              </div>
            ) : (
              messages.map((m, idx) => {
                const isUser = m.role === "user";
                return (
                  <div
                    key={m.id || idx}
                    className={`flex gap-3 text-xs ${isUser ? "items-start justify-end" : "items-start"}`}
                  >
                    {!isUser && (
                      <div className="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}

                    <div className={`max-w-[85%] rounded-xl leading-relaxed shadow-2xs ${
                      isUser
                        ? "p-3 bg-blue-600 text-white font-medium"
                        : "p-4 bg-slate-50 border border-slate-200 text-slate-800"
                    }`}>
                      {!isUser && m.agent_name && (
                        <div className="text-[10px] font-bold text-blue-700 uppercase tracking-wider mb-2 flex items-center gap-2">
                          <span className="px-1.5 py-0.5 rounded bg-blue-100/60 text-blue-800 border border-blue-200">
                            {m.agent_name}
                          </span>
                          {m.requires_human_approval && (
                            <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-300 flex items-center gap-1 font-semibold">
                              <ShieldAlert className="w-2.5 h-2.5 text-amber-600" />
                              <span>Requires Commercial Approval</span>
                            </span>
                          )}
                        </div>
                      )}

                      <div className="whitespace-pre-line text-xs font-normal leading-relaxed">
                        {m.content}
                      </div>

                      {/* Structured Response Cards */}
                      {!isUser && m.structured_data && (
                        <div className="mt-3.5 pt-3 border-t border-slate-200">
                          {renderStructuredCard(m.structured_data, setActiveTab)}
                        </div>
                      )}

                      {/* Commercial Action Approval Banner */}
                      {!isUser && m.pending_action && (
                        <div className="mt-3 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-900">
                          <div className="flex items-center gap-1.5 font-bold text-xs text-amber-800">
                            <ShieldAlert className="w-4 h-4 text-amber-600" />
                            <span>{m.pending_action.title}</span>
                          </div>
                          <p className="text-[11px] text-amber-700 mt-1">
                            {m.pending_action.description}
                          </p>
                          {m.pending_action.financial_impact && (
                            <div className="text-[11px] font-semibold text-amber-900 mt-1">
                              Financial Impact: {m.pending_action.financial_impact}
                            </div>
                          )}

                          <div className="mt-3 flex items-center gap-2">
                            <button
                              onClick={() => handleActionDecision(m.pending_action.id, "APPROVE")}
                              disabled={actionProcessing === m.pending_action.id}
                              className="px-3 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center gap-1 shadow-2xs transition-all disabled:opacity-50"
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>Authorize & Dispatch</span>
                            </button>
                            <button
                              onClick={() => handleActionDecision(m.pending_action.id, "REJECT")}
                              disabled={actionProcessing === m.pending_action.id}
                              className="px-3 py-1.5 rounded-md bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 font-semibold text-xs flex items-center gap-1 transition-all disabled:opacity-50"
                            >
                              <X className="w-3.5 h-3.5" />
                              <span>Reject / Revise</span>
                            </button>
                          </div>
                        </div>
                      )}

                      <div className="text-[10px] text-slate-400 mt-1.5 text-right">
                        {m.created_at}
                      </div>
                    </div>

                    {isUser && (
                      <div className="w-7 h-7 rounded-lg bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                        <User className="w-4 h-4" />
                      </div>
                    )}
                  </div>
                );
              })
            )}

            {sending && (
              <div className="flex gap-3 text-xs items-start">
                <div className="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                  <Bot className="w-4 h-4 animate-pulse" />
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                  <span className="font-medium text-xs">LangGraph Multi-Agent graph executing step trace...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Query Input Bar */}
          <div className="p-3 border-t border-slate-200 bg-slate-50/50">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !sending && handleSend()}
                placeholder="Ask in English or Hinglish (e.g. '500 brackets ke liye inventory check karo aur cost batao')..."
                className="flex-1 bg-white border border-slate-300 rounded-lg px-4 py-2.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 shadow-2xs font-normal"
              />
              <button
                onClick={() => handleSend()}
                disabled={sending || !inputQuery.trim()}
                className="px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-50 flex items-center gap-1.5"
              >
                {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                <span>{sending ? "Solving..." : "Send"}</span>
              </button>
            </div>
          </div>
        </div>

        {/* 3. Right Sidebar: Agent Activity & Execution Trace Panel */}
        {showActivityPanel && (
          <div className="col-span-12 md:col-span-3 bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col overflow-hidden">
            <div className="p-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-blue-600" />
                <span>Agent Activity Trace</span>
              </span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                Live StateGraph
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              {activeRunEvents.length === 0 ? (
                <div className="text-center py-12 text-slate-400 text-xs">
                  <Activity className="w-8 h-8 mx-auto text-slate-300 mb-2 stroke-1" />
                  <p className="font-semibold text-slate-600">No active agent run</p>
                  <p className="text-[11px] text-slate-400 mt-1">Submit a manufacturing query to observe real-time agent coordination.</p>
                </div>
              ) : (
                activeRunEvents.map((evt, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 hover:bg-slate-50 transition-all text-xs"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-blue-900 text-[11px] flex items-center gap-1">
                        <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-800 text-[9px] flex items-center justify-center font-bold">
                          {evt.step_number}
                        </span>
                        <span>{evt.agent}</span>
                      </span>
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-200 font-semibold text-slate-700">
                        {evt.event_type}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-600 leading-relaxed font-normal">
                      {evt.description}
                    </p>

                    <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400 font-medium">
                      <span className="text-emerald-600 flex items-center gap-1 font-semibold">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        <span>{evt.status}</span>
                      </span>
                      <span>{evt.time}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


// ============================================================================
// STRUCTURED CARD RENDERER
// ============================================================================

function renderStructuredCard(card: any, setActiveTab: (t: string) => void) {
  if (!card || typeof card !== "object") return null;

  const cardType = card.card_type;

  // 1. END-TO-END WORKFLOW SUMMARY CARD
  if (cardType === "END_TO_END_SUMMARY") {
    return (
      <div className="rounded-lg bg-blue-50/60 border border-blue-200 p-3.5">
        <div className="font-bold text-xs text-blue-950 flex items-center justify-between mb-2.5">
          <span className="flex items-center gap-1.5">
            <TrendingUp className="w-4 h-4 text-blue-600" />
            <span>End-to-End Manufacturing Workflow Results</span>
          </span>
          <span className="px-2 py-0.5 rounded bg-blue-200/60 text-blue-900 font-semibold text-[10px]">
            {card.production_quantity} Units
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
          <div className="p-2 rounded bg-white border border-blue-100 text-center">
            <div className="text-[10px] text-slate-500 font-medium">Net Shortage</div>
            <div className="text-xs font-bold text-rose-600 mt-0.5">{card.shortage_kg} kg</div>
          </div>
          <div className="p-2 rounded bg-white border border-blue-100 text-center">
            <div className="text-[10px] text-slate-500 font-medium">OR-Tools Cost</div>
            <div className="text-xs font-bold text-slate-900 mt-0.5">₹{card.procurement_cost?.toLocaleString()}</div>
          </div>
          <div className="p-2 rounded bg-white border border-blue-100 text-center">
            <div className="text-[10px] text-slate-500 font-medium">Selling Price</div>
            <div className="text-xs font-bold text-blue-700 mt-0.5">₹{card.selling_price?.toFixed(2)}</div>
          </div>
          <div className="p-2 rounded bg-white border border-blue-100 text-center">
            <div className="text-[10px] text-slate-500 font-medium">Gross Profit ({card.gross_margin_pct}%)</div>
            <div className="text-xs font-bold text-emerald-600 mt-0.5">₹{card.projected_profit?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 text-xs">
          <button
            onClick={() => setActiveTab("quotations")}
            className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold flex items-center gap-1 transition-all"
          >
            <span>View Customer Quotations</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  // 2. SUPPLIER COMPARISON CARD
  if (cardType === "SUPPLIER_COMPARISON") {
    const comp = card.data || {};
    const top = comp.top_candidate || {};
    return (
      <div className="rounded-lg bg-slate-100/70 border border-slate-200 p-3">
        <div className="font-bold text-xs text-slate-900 flex items-center gap-1.5 mb-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>Top Sourcing Candidate: {top.supplier_name || "Apex Steel & Alloys Pvt Ltd"}</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-[11px] mb-2">
          <div className="p-1.5 rounded bg-white border border-slate-200">
            <span className="text-slate-500 block">Score</span>
            <span className="font-bold text-emerald-700">{top.composite_score || 84.5} / 100</span>
          </div>
          <div className="p-1.5 rounded bg-white border border-slate-200">
            <span className="text-slate-500 block">Landed Cost</span>
            <span className="font-bold text-slate-900">₹{top.effective_landed_cost || 315.0}/kg</span>
          </div>
          <div className="p-1.5 rounded bg-white border border-slate-200">
            <span className="text-slate-500 block">Lead Time</span>
            <span className="font-bold text-slate-900">{top.lead_time_days || 6} days</span>
          </div>
        </div>
        <button
          onClick={() => setActiveTab("compare")}
          className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 mt-1"
        >
          <span>Open Full Supplier Comparison Matrix</span>
          <ChevronRight className="w-3 h-3" />
        </button>
      </div>
    );
  }

  // 3. INVENTORY SHORTAGE CARD
  if (cardType === "INVENTORY_SHORTAGE") {
    return (
      <div className="rounded-lg bg-amber-50/70 border border-amber-200 p-3">
        <div className="font-bold text-xs text-amber-900 flex items-center gap-1.5 mb-2">
          <AlertTriangle className="w-4 h-4 text-amber-600" />
          <span>Critical Inventory Shortage Detected</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-[11px] mb-2">
          <div className="p-1.5 rounded bg-white border border-amber-200">
            <span className="text-slate-500 block">Gross Required</span>
            <span className="font-bold text-slate-900">1,050.0 kg</span>
          </div>
          <div className="p-1.5 rounded bg-white border border-amber-200">
            <span className="text-slate-500 block">Net Available</span>
            <span className="font-bold text-slate-900">350.0 kg</span>
          </div>
          <div className="p-1.5 rounded bg-white border border-amber-200">
            <span className="text-slate-500 block">Shortage</span>
            <span className="font-bold text-rose-600">750.0 kg</span>
          </div>
        </div>
        <button
          onClick={() => setActiveTab("inventory")}
          className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 mt-1"
        >
          <span>Inspect Material Stock in Inventory View</span>
          <ChevronRight className="w-3 h-3" />
        </button>
      </div>
    );
  }

  // 4. COST BREAKDOWN CARD
  if (cardType === "COST_BREAKDOWN") {
    const cost = card.data || {};
    const cb = cost.cost_breakdown || {};
    const ue = cost.unit_economics || {};
    return (
      <div className="rounded-lg bg-slate-100/70 border border-slate-200 p-3">
        <div className="font-bold text-xs text-slate-900 flex items-center gap-1.5 mb-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <span>14-Factor Manufacturing Cost Engine Breakdown</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-[11px] mb-2">
          <div className="p-1.5 rounded bg-white border border-slate-200 flex justify-between">
            <span className="text-slate-500">Break-Even Unit Cost:</span>
            <span className="font-bold text-slate-900">₹{ue.break_even_price || 637.00}</span>
          </div>
          <div className="p-1.5 rounded bg-white border border-slate-200 flex justify-between">
            <span className="text-slate-500">Target Selling Price:</span>
            <span className="font-bold text-blue-700">₹{ue.suggested_unit_price || 849.33}</span>
          </div>
        </div>
        <button
          onClick={() => setActiveTab("costing")}
          className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 mt-1"
        >
          <span>Open Detailed Manufacturing Cost Engine</span>
          <ChevronRight className="w-3 h-3" />
        </button>
      </div>
    );
  }

  return null;
}
