"use client";

import React, { useState } from "react";
import {
  Bot,
  Send,
  User,
  Sparkles,
  Globe2,
  CheckCircle2,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import { chatCopilot } from "@/lib/api";

export default function CopilotView({ setActiveTab }: { setActiveTab: (tab: string) => void }) {
  const [messages, setMessages] = useState<any[]>([
    {
      sender: "bot",
      agent: "Supervisor Agent",
      text: (
        "Hello! I am IndusPilot, your AI Manufacturing & Procurement Copilot. " +
        "You can ask me questions in English, Hindi, or Hinglish! I connect directly to our deterministic " +
        "costing engine, Google OR-Tools optimizer, and BOM database. How can I help you today?"
      ),
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [sending, setSending] = useState(false);

  const samplePrompts = [
    "Compare supplier quotations for stainless steel 304",
    "500 brackets ke liye material shortage check karo",
    "Calculate my production cost for 500 industrial brackets",
    "Draft a negotiation counteroffer for Apex Steel",
    "Optimize supplier allocation under ₹3 Lakh budget",
  ];

  const handleSend = async (queryText?: string) => {
    const q = (queryText || inputQuery).trim();
    if (!q) return;

    const newMessages = [...messages, { sender: "user", text: q }];
    setMessages(newMessages);
    setInputQuery("");
    setSending(true);

    try {
      const res = await chatCopilot(q);
      setMessages([
        ...newMessages,
        {
          sender: "bot",
          agent: res.agent_name,
          text: res.response_text,
          data: res.data,
          requiresApproval: res.requires_human_approval,
        },
      ]);
    } catch (err: any) {
      setMessages([
        ...newMessages,
        {
          sender: "bot",
          agent: "System Error",
          text: `Error processing query: ${err.message}`,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Bot className="w-5 h-5 text-blue-600" />
            <span>AI Manufacturing Copilot (English • हिंदी • Hinglish)</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Ask natural-language questions about material shortages, quotation comparisons,
            negotiation emails, or production costing. Powered by specialized backend agents.
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-xs text-slate-700 font-medium">
          <Globe2 className="w-4 h-4 text-blue-600" />
          <span>Multilingual NLP Enabled</span>
        </div>
      </div>

      {/* Suggested Prompt Chips */}
      <div className="flex flex-wrap gap-2">
        {samplePrompts.map((p, i) => (
          <button
            key={i}
            onClick={() => handleSend(p)}
            className="text-xs px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 hover:border-blue-300 transition-all text-left flex items-center gap-1.5 shadow-2xs"
          >
            <Sparkles className="w-3 h-3 text-blue-600 shrink-0" />
            <span>{p}</span>
          </button>
        ))}
      </div>

      {/* Chat Messages Container */}
      <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs h-[480px] flex flex-col justify-between">
        <div className="space-y-4 overflow-y-auto pr-2 flex-1">
          {messages.map((m, idx) => {
            const isBot = m.sender === "bot";
            return (
              <div
                key={idx}
                className={`flex gap-3 text-xs ${isBot ? "items-start" : "items-start justify-end"}`}
              >
                {isBot && (
                  <div className="w-7 h-7 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`p-4 rounded-xl max-w-2xl leading-relaxed whitespace-pre-line shadow-2xs ${
                    isBot
                      ? "bg-slate-50 border border-slate-200 text-slate-800"
                      : "bg-blue-600 text-white font-medium"
                  }`}
                >
                  {isBot && m.agent && (
                    <div className="text-[10px] font-bold text-blue-700 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <span>{m.agent}</span>
                      {m.requiresApproval && (
                        <span className="px-1.5 py-0.2 rounded bg-amber-50 text-amber-800 border border-amber-300 text-[9px]">
                          Requires Approval
                        </span>
                      )}
                    </div>
                  )}
                  {m.text}
                </div>

                {!isBot && (
                  <div className="w-7 h-7 rounded-lg bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Query Input Bar */}
        <div className="pt-4 border-t border-slate-200 flex items-center gap-2">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Type your instruction or question in English or Hinglish (e.g. '500 brackets ka shortage check karo')..."
            className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={() => handleSend()}
            disabled={sending || !inputQuery.trim()}
            className="px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-50 flex items-center gap-1.5"
          >
            <Send className="w-4 h-4" />
            <span>{sending ? "Thinking..." : "Send"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
