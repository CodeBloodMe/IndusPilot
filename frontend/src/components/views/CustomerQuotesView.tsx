"use client";

import React, { useState, useEffect } from "react";
import {
  FileCheck2,
  Download,
  AlertTriangle,
  CheckCircle2,
  Plus,
  ShieldCheck,
  Building,
  User,
  ArrowDownToLine,
} from "lucide-react";
import { getCustomerQuotations, generateCustomerQuotation } from "@/lib/api";

export default function CustomerQuotesView() {
  const [quotes, setQuotes] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [generating, setGenerating] = useState<boolean>(false);
  const [showModal, setShowModal] = useState<boolean>(false);

  // Form State
  const [customerName, setCustomerName] = useState("Larsen Heavy Machinery Corp");
  const [company, setCompany] = useState("L&H Industrial Equipment Division");
  const [email, setEmail] = useState("procurement@larsenheavy.com");
  const [quantity, setQuantity] = useState(500);
  const [unitCost, setUnitCost] = useState(637);
  const [sellingPrice, setSellingPrice] = useState(850);
  const [paymentTerms, setPaymentTerms] = useState("50% Advance, 50% Against Delivery");
  const [deliveryWeeks, setDeliveryWeeks] = useState(3);

  useEffect(() => {
    loadQuotes();
  }, []);

  const loadQuotes = async () => {
    try {
      setLoading(true);
      const data = await getCustomerQuotations();
      setQuotes(data);
    } catch (err) {
      console.error("Failed to load customer quotes:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setGenerating(true);
      await generateCustomerQuotation({
        customer_name: customerName,
        customer_company: company,
        customer_email: email,
        quantity,
        unit_cost: unitCost,
        unit_selling_price: sellingPrice,
        tax_pct: 18.0,
        payment_terms: paymentTerms,
        delivery_weeks: deliveryWeeks,
      });
      setShowModal(false);
      await loadQuotes();
    } catch (err) {
      console.error("Failed to generate quote:", err);
    } finally {
      setGenerating(false);
    }
  };

  const marginPct =
    sellingPrice > 0 ? (((sellingPrice - unitCost) / sellingPrice) * 100).toFixed(1) : "0.0";
  const isLossMaking = sellingPrice < unitCost;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-blue-600" />
            <span>Customer Quotation Generator & Profitability Guard</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Generates commercial customer quotations based on audited manufacturing costs.
            Provides instant PDF rendering and protects against loss-making contracts.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Prepare Customer Quote</span>
        </button>
      </div>

      {/* Quotes Table */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200 shadow-xs">
          Loading customer quotations...
        </div>
      ) : quotes.length === 0 ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200 shadow-xs">
          No customer quotes generated yet. Click "Prepare Customer Quote".
        </div>
      ) : (
        <div className="space-y-3">
          <div className="overflow-x-auto border border-slate-200 rounded-xl bg-white shadow-xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-700 font-bold uppercase text-[10px] border-b border-slate-200">
                <tr>
                  <th className="p-3.5">Quote Ref</th>
                  <th className="p-3.5">Customer & Enterprise</th>
                  <th className="p-3.5 text-right">Batch Qty</th>
                  <th className="p-3.5 text-right">Unit Price</th>
                  <th className="p-3.5 text-right">Unit Cost</th>
                  <th className="p-3.5 text-right">Gross Margin %</th>
                  <th className="p-3.5 text-right">Total Amount (Gross)</th>
                  <th className="p-3.5 text-center">Status</th>
                  <th className="p-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {quotes.map((q) => (
                  <tr key={q.id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-3.5 font-bold font-mono text-blue-700">{q.quote_number}</td>
                    <td className="p-3.5">
                      <div className="font-semibold text-slate-900">{q.customer_name}</div>
                      <div className="text-[11px] text-slate-500">{q.customer_company}</div>
                    </td>
                    <td className="p-3.5 text-right font-mono text-slate-800">
                      {q.quantity.toLocaleString("en-IN")} Nos
                    </td>
                    <td className="p-3.5 text-right font-mono font-bold text-slate-900">
                      ₹{q.unit_selling_price.toFixed(2)}
                    </td>
                    <td className="p-3.5 text-right font-mono text-slate-500">
                      ₹{q.unit_production_cost.toFixed(2)}
                    </td>
                    <td className="p-3.5 text-right font-mono font-bold">
                      <span className={q.is_loss_making ? "text-red-700" : "text-emerald-700"}>
                        {q.margin_pct}%
                      </span>
                    </td>
                    <td className="p-3.5 text-right font-mono font-black text-slate-900">
                      ₹{q.total_amount.toLocaleString("en-IN")}
                    </td>
                    <td className="p-3.5 text-center">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          q.status === "APPROVED"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-amber-50 text-amber-700 border-amber-200"
                        }`}
                      >
                        {q.status}
                      </span>
                    </td>
                    <td className="p-3.5 text-right">
                      <a
                        href={`http://localhost:8000/api/v1/customer-quotes/${q.id}/download-pdf`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-blue-50 text-blue-700 text-xs font-semibold border border-slate-200 transition-all shadow-2xs"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>PDF</span>
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Prepare Quote Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-xl bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900">Generate Commercial Customer Quotation</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-700 text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleGenerate} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-600 block mb-1">Customer Contact Name:</label>
                  <input
                    type="text"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    required
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
                  />
                </div>
                <div>
                  <label className="text-slate-600 block mb-1">Company / Organization:</label>
                  <input
                    type="text"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    required
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-slate-600 block mb-1">Batch Quantity:</label>
                  <input
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(Number(e.target.value))}
                    required
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-600 block mb-1">Unit Cost (₹):</label>
                  <input
                    type="number"
                    value={unitCost}
                    onChange={(e) => setUnitCost(Number(e.target.value))}
                    required
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-600 block mb-1">Selling Price (₹):</label>
                  <input
                    type="number"
                    value={sellingPrice}
                    onChange={(e) => setSellingPrice(Number(e.target.value))}
                    required
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-mono font-bold"
                  />
                </div>
              </div>

              {/* Profitability verification */}
              <div
                className={`p-3 rounded-lg border flex items-center justify-between ${
                  isLossMaking
                    ? "bg-red-50 border-red-200 text-red-700"
                    : "bg-emerald-50 border-emerald-200 text-emerald-800"
                }`}
              >
                <div>
                  <span className="font-bold block">
                    {isLossMaking ? "⚠️ LOSS-MAKING WARNING" : "✓ Profitability Verified"}
                  </span>
                  <span className="text-[11px] opacity-90">
                    Gross Margin: <b>{marginPct}%</b> • Unit Spread: ₹{(sellingPrice - unitCost).toFixed(2)}
                  </span>
                </div>
                <span className="text-sm font-black font-mono">
                  {isLossMaking ? "REJECT" : "PROFITABLE"}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-600 block mb-1">Payment Terms:</label>
                  <input
                    type="text"
                    value={paymentTerms}
                    onChange={(e) => setPaymentTerms(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
                  />
                </div>
                <div>
                  <label className="text-slate-600 block mb-1">Delivery Schedule (Weeks):</label>
                  <input
                    type="number"
                    value={deliveryWeeks}
                    onChange={(e) => setDeliveryWeeks(Number(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-mono"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={generating}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all"
                >
                  {generating ? "Building PDF..." : "Generate PDF & Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
