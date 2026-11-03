"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  User,
  ArrowRight,
} from "lucide-react";
import { getApprovals, actOnApproval } from "@/lib/api";

export default function ApprovalCentreView({ onApprovalProcessed }: { onApprovalProcessed?: () => void }) {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [processingId, setProcessingId] = useState<string | null>(null);

  useEffect(() => {
    loadApprovals();
  }, []);

  const loadApprovals = async () => {
    try {
      setLoading(true);
      const data = await getApprovals();
      setApprovals(data);
    } catch (err) {
      console.error("Failed to load approvals:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (id: string, action: "APPROVE" | "REJECT") => {
    try {
      setProcessingId(id);
      await actOnApproval(id, action);
      await loadApprovals();
      if (onApprovalProcessed) onApprovalProcessed();
    } catch (err) {
      console.error("Failed to act on approval:", err);
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-blue-600" />
          <span>Central Human Approval & Governance Centre</span>
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Engineering safeguard: AI agents can draft counteroffers and calculate quotes, but no binding
          financial commitments are executed without explicit human authorization.
        </p>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200 shadow-xs">
          Loading approval requests...
        </div>
      ) : approvals.length === 0 ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200 shadow-xs">
          No pending approval requests. All agent workflows are up to date.
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((appr) => {
            const isPending = appr.status === "PENDING";
            return (
              <div
                key={appr.id}
                className={`p-5 rounded-xl border transition-all bg-white shadow-xs ${
                  isPending
                    ? "border-amber-400 ring-1 ring-amber-300"
                    : "border-slate-200"
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
                        isPending
                          ? "bg-amber-50 text-amber-800 border-amber-300"
                          : appr.status === "APPROVED"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                          : "bg-red-50 text-red-700 border-red-300"
                      }`}
                    >
                      {appr.status}
                    </span>
                    <span className="text-xs font-bold text-slate-900">
                      {appr.request_type.replace(/_/g, " ")}
                    </span>
                    <span className="text-xs text-slate-500">• Requested by {appr.requested_by}</span>
                  </div>

                  <span className="text-[11px] text-slate-500 font-mono">{appr.created_at}</span>
                </div>

                {/* Details Container */}
                <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono text-slate-700 mb-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {appr.details &&
                      Object.entries(appr.details).map(([k, v]: [string, any]) => (
                        <div key={k}>
                          <span className="text-slate-500 block text-[10px] uppercase font-bold">
                            {k.replace(/_/g, " ")}
                          </span>
                          <span className="font-semibold text-slate-900 mt-0.5 block truncate">
                            {typeof v === "number" ? v.toLocaleString("en-IN") : String(v)}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>

                {/* Action Bar */}
                {isPending ? (
                  <div className="flex items-center justify-end gap-3 pt-1 border-t border-slate-200">
                    <button
                      onClick={() => handleAction(appr.id, "REJECT")}
                      disabled={processingId === appr.id}
                      className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-red-50 text-red-700 text-xs font-bold border border-slate-200 hover:border-red-300 transition-all disabled:opacity-50"
                    >
                      Reject Request
                    </button>
                    <button
                      onClick={() => handleAction(appr.id, "APPROVE")}
                      disabled={processingId === appr.id}
                      className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition-all disabled:opacity-50 flex items-center gap-1.5"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>{processingId === appr.id ? "Authorizing..." : "Authorize & Execute"}</span>
                    </button>
                  </div>
                ) : (
                  <div className="text-[11px] text-slate-500 flex items-center gap-1 pt-1 border-t border-slate-200">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Decision Recorded: {appr.decision_reason || "Decision confirmed."}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
