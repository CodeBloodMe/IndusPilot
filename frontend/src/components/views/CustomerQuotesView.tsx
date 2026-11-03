"use client";

import React, { useState, useEffect } from "react";
import {
  FileCheck2,
  Download,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Plus,
  ShieldCheck,
  Building,
  User,
  ArrowDownToLine,
  TrendingUp,
  Percent,
  RefreshCw,
  AlertOctagon,
  FileText,
  Clock,
  ThumbsUp,
  ThumbsDown,
  Calculator,
  ShieldAlert,
} from "lucide-react";
import {
  getCustomerQuotations,
  getCustomerQuotation,
  createCustomerQuotation,
  recalculateCustomerQuotation,
  requestCustomerQuoteApproval,
  approveCustomerQuotation,
  recordCustomerQuoteResponse,
  getCustomers,
  getCustomerQuotePdfUrl,
  getProducts,
  getCostEstimates,
} from "@/lib/api";

export default function CustomerQuotesView() {
  const [quotes, setQuotes] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [showRecalcModal, setShowRecalcModal] = useState<boolean>(false);
  const [showResponseModal, setShowResponseModal] = useState<boolean>(false);
  const [selectedQuote, setSelectedQuote] = useState<any>(null);
  const [filterMode, setFilterMode] = useState<"ALL" | "PROFITABLE" | "LOSS_MAKING">("ALL");
  const [notice, setNotice] = useState<{ type: "success" | "error" | "info"; message: string } | null>(null);

  // Form State for New Customer Quote
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>("");
  const [customerName, setCustomerName] = useState("Larsen Heavy Machinery Corp");
  const [company, setCompany] = useState("L&H Industrial Equipment Division");
  const [email, setEmail] = useState("procurement@larsenheavy.com");
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [quantity, setQuantity] = useState<number>(500);
  const [unitCost, setUnitCost] = useState<number>(637.0);
  const [pricingMode, setPricingMode] = useState<"PRICE" | "MARGIN" | "MARKUP">("MARGIN");
  const [sellingPrice, setSellingPrice] = useState<number>(850.0);
  const [targetMarginPct, setTargetMarginPct] = useState<number>(25.0);
  const [targetMarkupPct, setTargetMarkupPct] = useState<number>(33.4);
  const [discountPct, setDiscountPct] = useState<number>(0.0);
  const [taxPct, setTaxPct] = useState<number>(18.0);
  const [paymentTerms, setPaymentTerms] = useState("50% Advance, 50% Against Delivery");
  const [deliveryWeeks, setDeliveryWeeks] = useState<number>(3);

  // Recalculate State
  const [recalcPrice, setRecalcPrice] = useState<number>(850.0);
  const [recalcMargin, setRecalcMargin] = useState<number>(25.0);

  // Customer Response State
  const [custResponse, setCustResponse] = useState<string>("ACCEPTED");
  const [custNotes, setCustNotes] = useState<string>("");

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    try {
      setLoading(true);
      const [quotesData, custData, prodData] = await Promise.all([
        getCustomerQuotations(),
        getCustomers().catch(() => []),
        getProducts().catch(() => []),
      ]);
      setQuotes(quotesData || []);
      setCustomers(custData || []);
      setProducts(prodData || []);
      if (prodData && prodData.length > 0) {
        setSelectedProductId(prodData[0].id);
      }
    } catch (err: any) {
      console.error("Failed to load customer quotes:", err);
      showNotice("error", err.message || "Failed to load quotations.");
    } finally {
      setLoading(false);
    }
  };

  const showNotice = (type: "success" | "error" | "info", message: string) => {
    setNotice({ type, message });
    setTimeout(() => setNotice(null), 6000);
  };

  // Recalculate pricing on input changes
  const updateBySellingPrice = (price: number) => {
    setSellingPrice(price);
    if (price > 0 && unitCost > 0) {
      const margin = ((price - unitCost) / price) * 100;
      const markup = ((price - unitCost) / unitCost) * 100;
      setTargetMarginPct(parseFloat(margin.toFixed(2)));
      setTargetMarkupPct(parseFloat(markup.toFixed(2)));
    }
  };

  const updateByMargin = (margin: number) => {
    setTargetMarginPct(margin);
    if (margin < 100 && margin > -100 && unitCost > 0) {
      const price = unitCost / (1 - margin / 100);
      setSellingPrice(parseFloat(price.toFixed(2)));
      const markup = ((price - unitCost) / unitCost) * 100;
      setTargetMarkupPct(parseFloat(markup.toFixed(2)));
    }
  };

  const updateByMarkup = (markup: number) => {
    setTargetMarkupPct(markup);
    if (unitCost > 0) {
      const price = unitCost * (1 + markup / 100);
      setSellingPrice(parseFloat(price.toFixed(2)));
      const margin = ((price - unitCost) / price) * 100;
      setTargetMarginPct(parseFloat(margin.toFixed(2)));
    }
  };

  const isLossMaking = sellingPrice < unitCost;
  const isBelowMinMargin = !isLossMaking && targetMarginPct < 15.0;

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setActionLoading(true);
      await createCustomerQuotation({
        customer_id: selectedCustomerId || undefined,
        customer_name: customerName,
        customer_company: company,
        customer_email: email,
        product_id: selectedProductId || undefined,
        quantity,
        unit_cost: unitCost,
        unit_selling_price: sellingPrice,
        target_margin_pct: targetMarginPct,
        discount_pct: discountPct,
        tax_pct: taxPct,
        payment_terms: paymentTerms,
        delivery_weeks: deliveryWeeks,
      });
      setShowModal(false);
      await loadAllData();
      showNotice("success", "Customer quotation generated and official PDF created!");
    } catch (err: any) {
      showNotice("error", err.message || "Failed to generate customer quote.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestApproval = async (quoteId: string) => {
    try {
      setActionLoading(true);
      await requestCustomerQuoteApproval(quoteId);
      await loadAllData();
      showNotice("success", "Quotation submitted for commercial director authorization.");
    } catch (err: any) {
      showNotice("error", err.message || "Failed to request approval.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleApprove = async (quoteId: string) => {
    try {
      setActionLoading(true);
      await approveCustomerQuotation(quoteId, "Commercial Director");
      await loadAllData();
      showNotice("success", "Quotation approved! Authorized for dispatch to client.");
    } catch (err: any) {
      showNotice("error", err.message || "Approval failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const openRecalculate = (quote: any) => {
    setSelectedQuote(quote);
    setRecalcPrice(quote.unit_selling_price);
    setRecalcMargin(quote.margin_pct);
    setShowRecalcModal(true);
  };

  const handleRecalculateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedQuote) return;
    try {
      setActionLoading(true);
      await recalculateCustomerQuotation(selectedQuote.id, {
        unit_selling_price: recalcPrice,
        target_margin_pct: recalcMargin,
      });
      setShowRecalcModal(false);
      await loadAllData();
      showNotice("success", `Quotation recalculated! Revision v${(selectedQuote.version || 1) + 1} generated.`);
    } catch (err: any) {
      showNotice("error", err.message || "Recalculation failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const openRecordResponse = (quote: any) => {
    setSelectedQuote(quote);
    setCustResponse("ACCEPTED");
    setCustNotes("");
    setShowResponseModal(true);
  };

  const handleResponseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedQuote) return;
    try {
      setActionLoading(true);
      await recordCustomerQuoteResponse(selectedQuote.id, custResponse, custNotes);
      setShowResponseModal(false);
      await loadAllData();
      showNotice("success", `Customer decision recorded: ${custResponse}.`);
    } catch (err: any) {
      showNotice("error", err.message || "Failed to record customer response.");
    } finally {
      setActionLoading(false);
    }
  };

  const filteredQuotes = quotes.filter((q) => {
    if (filterMode === "PROFITABLE") return !q.is_loss_making;
    if (filterMode === "LOSS_MAKING") return q.is_loss_making;
    return true;
  });

  const totalPipeline = quotes.reduce((acc, q) => acc + (q.total_amount || 0), 0);
  const lossMakingCount = quotes.filter((q) => q.is_loss_making).length;
  const profitableCount = quotes.filter((q) => !q.is_loss_making).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-blue-600" />
            <span>Customer Quotation Engine & Commercial Margin Guard</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Formulates deterministic customer quotations linked to manufacturing cost audits. Features gross margin vs.
            markup math, loss-making contract protection, discount/tax schedules, and ReportLab PDF rendering.
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
              <FileCheck2 className="w-4 h-4 text-blue-600 shrink-0" />
            )}
            <span>{notice.message}</span>
          </div>
          <button onClick={() => setNotice(null)} className="text-xs font-bold opacity-70 hover:opacity-100">
            ✕
          </button>
        </div>
      )}

      {/* Top Commercial KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-slate-500 block">Total Pipeline Value</span>
          <div className="text-xl font-black font-mono text-slate-900 mt-1">
            ₹{totalPipeline.toLocaleString("en-IN")}
          </div>
          <span className="text-[11px] text-slate-500">{quotes.length} total quotations issued</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-slate-500 block">Profitable Contracts</span>
          <div className="text-xl font-black font-mono text-emerald-700 mt-1">{profitableCount}</div>
          <span className="text-[11px] text-emerald-600">Healthy commercial margins</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-slate-500 block">Loss-Making Flagged</span>
          <div className="text-xl font-black font-mono text-red-700 mt-1">{lossMakingCount}</div>
          <span className="text-[11px] text-red-600">Requires executive override</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-slate-500 block">Pricing Math Standard</span>
          <div className="text-sm font-bold text-blue-900 mt-1.5 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-blue-600" />
            <span>Python Decimal (ROUND_HALF_UP)</span>
          </div>
          <span className="text-[10px] text-slate-400">Zero floating point discrepancy</span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2 text-xs">
        <button
          onClick={() => setFilterMode("ALL")}
          className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
            filterMode === "ALL"
              ? "bg-blue-600 text-white shadow-2xs"
              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
          }`}
        >
          All Quotes ({quotes.length})
        </button>
        <button
          onClick={() => setFilterMode("PROFITABLE")}
          className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
            filterMode === "PROFITABLE"
              ? "bg-emerald-600 text-white shadow-2xs"
              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
          }`}
        >
          Profitable Only ({profitableCount})
        </button>
        <button
          onClick={() => setFilterMode("LOSS_MAKING")}
          className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
            filterMode === "LOSS_MAKING"
              ? "bg-red-600 text-white shadow-2xs"
              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
          }`}
        >
          Loss-Making Alerts ({lossMakingCount})
        </button>
      </div>

      {/* Quotations Table */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200 shadow-xs">
          Loading commercial customer quotations...
        </div>
      ) : filteredQuotes.length === 0 ? (
        <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200 shadow-xs">
          No customer quotes match this filter. Click "Prepare Customer Quote" to draft one.
        </div>
      ) : (
        <div className="space-y-3">
          <div className="overflow-x-auto border border-slate-200 rounded-xl bg-white shadow-xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-700 font-bold uppercase text-[10px] border-b border-slate-200">
                <tr>
                  <th className="p-3.5">Quote Ref & Rev</th>
                  <th className="p-3.5">Customer & Enterprise</th>
                  <th className="p-3.5 text-right">Batch Qty</th>
                  <th className="p-3.5 text-right">Unit Price</th>
                  <th className="p-3.5 text-right">Unit Cost</th>
                  <th className="p-3.5 text-right">Margin % / Markup %</th>
                  <th className="p-3.5 text-right">Total (Incl. Tax)</th>
                  <th className="p-3.5 text-center">Profitability</th>
                  <th className="p-3.5 text-center">Approval</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredQuotes.map((q) => {
                  const pdfUrl = getCustomerQuotePdfUrl(q.id);
                  const isApproved = q.approval_status === "APPROVED";
                  const isPending = q.approval_status === "PENDING_APPROVAL";

                  return (
                    <tr key={q.id} className="hover:bg-slate-50 transition-colors">
                      <td className="p-3.5">
                        <div className="font-bold font-mono text-blue-700">{q.quote_number}</div>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                          v{q.version || 1}
                        </span>
                      </td>
                      <td className="p-3.5">
                        <div className="font-semibold text-slate-900">{q.customer_name}</div>
                        <div className="text-[11px] text-slate-500">{q.customer_company}</div>
                      </td>
                      <td className="p-3.5 text-right font-mono text-slate-800">
                        {q.quantity?.toLocaleString("en-IN")} Nos
                      </td>
                      <td className="p-3.5 text-right font-mono font-bold text-slate-900">
                        ₹{q.unit_selling_price?.toFixed(2)}
                      </td>
                      <td className="p-3.5 text-right font-mono text-slate-500">
                        ₹{q.unit_production_cost?.toFixed(2)}
                      </td>
                      <td className="p-3.5 text-right font-mono">
                        <div className={`font-bold ${q.is_loss_making ? "text-red-700" : "text-emerald-700"}`}>
                          {q.margin_pct}% margin
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {q.markup_pct?.toFixed(1)}% markup
                        </div>
                      </td>
                      <td className="p-3.5 text-right font-mono font-black text-slate-900">
                        ₹{q.total_amount?.toLocaleString("en-IN")}
                      </td>
                      <td className="p-3.5 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                            q.is_loss_making
                              ? "bg-red-50 text-red-700 border-red-300"
                              : q.profitability_status === "BELOW_TARGET_MARGIN"
                              ? "bg-amber-50 text-amber-700 border-amber-300"
                              : "bg-emerald-50 text-emerald-700 border-emerald-300"
                          }`}
                        >
                          {q.profitability_status || (q.is_loss_making ? "LOSS_MAKING" : "PROFITABLE")}
                        </span>
                      </td>
                      <td className="p-3.5 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                            isApproved
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : isPending
                              ? "bg-amber-50 text-amber-700 border-amber-200"
                              : "bg-slate-50 text-slate-600 border-slate-200"
                          }`}
                        >
                          {q.approval_status || "DRAFT"}
                        </span>
                      </td>
                      <td className="p-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* PDF Download */}
                          <a
                            href={pdfUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 hover:bg-blue-50 text-blue-700 text-xs font-semibold border border-slate-200 transition-all shadow-2xs"
                            title="Download Official PDF Quote"
                          >
                            <Download className="w-3.5 h-3.5" />
                            <span>PDF</span>
                          </a>

                          {/* Approval Trigger */}
                          {isPending && (
                            <button
                              onClick={() => handleApprove(q.id)}
                              disabled={actionLoading}
                              className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-all shadow-2xs"
                              title="Approve Commercial Quotation"
                            >
                              Approve
                            </button>
                          )}
                          {!isApproved && !isPending && (
                            <button
                              onClick={() => handleRequestApproval(q.id)}
                              disabled={actionLoading}
                              className="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-all shadow-2xs"
                              title="Submit for Commercial Director Approval"
                            >
                              Request
                            </button>
                          )}

                          {/* Recalculate */}
                          <button
                            onClick={() => openRecalculate(q)}
                            className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold border border-slate-200"
                            title="Recalculate Margins / New Revision"
                          >
                            <RefreshCw className="w-3.5 h-3.5" />
                          </button>

                          {/* Record Response */}
                          <button
                            onClick={() => openRecordResponse(q)}
                            className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold border border-slate-200"
                            title="Record Customer Decision"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Prepare Quote Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-slate-200 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Calculator className="w-5 h-5 text-blue-600" />
                  <span>Prepare Commercial Customer Quotation</span>
                </h3>
                <p className="text-[11px] text-slate-500">
                  Backed by audited manufacturing costing and guaranteed Python Decimal rounding.
                </p>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-700 text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleGenerate} className="space-y-4 text-xs">
              {/* Customer Selector / Input */}
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-3">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 block">
                  Customer & Account Identification
                </span>
                {customers.length > 0 && (
                  <div>
                    <label className="text-slate-600 block mb-1 font-semibold">Choose Existing Customer:</label>
                    <select
                      value={selectedCustomerId}
                      onChange={(e) => {
                        setSelectedCustomerId(e.target.value);
                        const found = customers.find((c) => c.id === e.target.value);
                        if (found) {
                          setCustomerName(found.name);
                          setCompany(found.company_name);
                          setEmail(found.email || "");
                        }
                      }}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-900"
                    >
                      <option value="">-- Manual Entry / New Customer --</option>
                      {customers.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.company_name} ({c.name})
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-slate-600 block mb-1 font-semibold">Customer Contact Name:</label>
                    <input
                      type="text"
                      value={customerName}
                      onChange={(e) => setCustomerName(e.target.value)}
                      required
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-900"
                    />
                  </div>
                  <div>
                    <label className="text-slate-600 block mb-1 font-semibold">Company / Enterprise:</label>
                    <input
                      type="text"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      required
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-900"
                    />
                  </div>
                </div>
              </div>

              {/* Product & Volume */}
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-slate-600 block mb-1 font-semibold">Manufactured Product:</label>
                  <select
                    value={selectedProductId}
                    onChange={(e) => setSelectedProductId(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-medium"
                  >
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.code} - {p.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-slate-600 block mb-1 font-semibold">Batch Quantity (Nos):</label>
                  <input
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
                    required
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-600 block mb-1 font-semibold">Unit Production Cost (₹):</label>
                  <input
                    type="number"
                    step="0.01"
                    value={unitCost}
                    onChange={(e) => {
                      const cost = parseFloat(e.target.value) || 0;
                      setUnitCost(cost);
                      if (pricingMode === "MARGIN") {
                        const price = cost / (1 - targetMarginPct / 100);
                        setSellingPrice(parseFloat(price.toFixed(2)));
                      }
                    }}
                    required
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-mono font-bold"
                  />
                </div>
              </div>

              {/* Pricing Mode & Margin Calculator */}
              <div className="p-3.5 rounded-xl bg-blue-50/50 border border-blue-200 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-blue-900">
                    Pricing & Commercial Profitability Formulation
                  </span>
                  <div className="flex gap-1 text-[11px]">
                    <button
                      type="button"
                      onClick={() => setPricingMode("MARGIN")}
                      className={`px-2.5 py-1 rounded font-bold transition-all ${
                        pricingMode === "MARGIN"
                          ? "bg-blue-600 text-white shadow-2xs"
                          : "bg-white text-slate-700 border border-slate-200"
                      }`}
                    >
                      Target Gross Margin %
                    </button>
                    <button
                      type="button"
                      onClick={() => setPricingMode("MARKUP")}
                      className={`px-2.5 py-1 rounded font-bold transition-all ${
                        pricingMode === "MARKUP"
                          ? "bg-blue-600 text-white shadow-2xs"
                          : "bg-white text-slate-700 border border-slate-200"
                      }`}
                    >
                      Target Markup %
                    </button>
                    <button
                      type="button"
                      onClick={() => setPricingMode("PRICE")}
                      className={`px-2.5 py-1 rounded font-bold transition-all ${
                        pricingMode === "PRICE"
                          ? "bg-blue-600 text-white shadow-2xs"
                          : "bg-white text-slate-700 border border-slate-200"
                      }`}
                    >
                      Fixed Unit Selling Price
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-slate-600 block mb-1 font-semibold">Unit Selling Price (₹):</label>
                    <input
                      type="number"
                      step="0.01"
                      value={sellingPrice}
                      onChange={(e) => updateBySellingPrice(parseFloat(e.target.value) || 0)}
                      required
                      className="w-full bg-white border border-blue-300 rounded-lg p-2 text-slate-900 font-mono font-black text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-slate-600 block mb-1 font-semibold">Gross Margin % (on Price):</label>
                    <input
                      type="number"
                      step="0.1"
                      value={targetMarginPct}
                      onChange={(e) => updateByMargin(parseFloat(e.target.value) || 0)}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-900 font-mono font-bold"
                    />
                  </div>
                  <div>
                    <label className="text-slate-600 block mb-1 font-semibold">Markup % (on Cost):</label>
                    <input
                      type="number"
                      step="0.1"
                      value={targetMarkupPct}
                      onChange={(e) => updateByMarkup(parseFloat(e.target.value) || 0)}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-900 font-mono"
                    />
                  </div>
                </div>

                {/* Educational distinction reminder */}
                <p className="text-[10px] text-slate-500 italic">
                  💡 Note: Gross Margin = (Price − Cost) / Price. Markup = (Price − Cost) / Cost. A 25% margin equates to a 33.3% markup.
                </p>
              </div>

              {/* Profitability Guard Warning Banner */}
              <div
                className={`p-3.5 rounded-lg border flex items-center justify-between ${
                  isLossMaking
                    ? "bg-red-50 border-red-300 text-red-800"
                    : isBelowMinMargin
                    ? "bg-amber-50 border-amber-300 text-amber-800"
                    : "bg-emerald-50 border-emerald-300 text-emerald-800"
                }`}
              >
                <div className="flex items-center gap-2">
                  {isLossMaking ? (
                    <AlertOctagon className="w-5 h-5 text-red-600 shrink-0" />
                  ) : isBelowMinMargin ? (
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  )}
                  <div>
                    <span className="font-bold block text-xs">
                      {isLossMaking
                        ? "⚠️ CRITICAL: LOSS-MAKING CONTRACT DETECTED"
                        : isBelowMinMargin
                        ? "⚠️ NOTICE: BELOW TARGET MINIMUM MARGIN (15.0%)"
                        : "✓ COMMERCIAL PROFITABILITY VERIFIED"}
                    </span>
                    <span className="text-[11px] opacity-90">
                      Margin: <b>{targetMarginPct}%</b> • Unit Spread: ₹{(sellingPrice - unitCost).toFixed(2)} / unit •
                      Gross Profit: ₹{((sellingPrice - unitCost) * quantity).toLocaleString("en-IN")}
                    </span>
                  </div>
                </div>
                <span className="text-xs font-black font-mono px-2 py-1 rounded bg-white/80 border">
                  {isLossMaking ? "REJECTED" : isBelowMinMargin ? "REVIEW NEEDED" : "PROFITABLE"}
                </span>
              </div>

              {/* Commercial Terms & Taxes */}
              <div className="grid grid-cols-4 gap-3">
                <div>
                  <label className="text-slate-600 block mb-1 font-semibold">Volume Discount %:</label>
                  <input
                    type="number"
                    step="0.5"
                    value={discountPct}
                    onChange={(e) => setDiscountPct(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-600 block mb-1 font-semibold">GST Rate %:</label>
                  <select
                    value={taxPct}
                    onChange={(e) => setTaxPct(parseFloat(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-mono"
                  >
                    <option value={0}>0% (Exempt)</option>
                    <option value={5}>5% GST</option>
                    <option value={12}>12% GST</option>
                    <option value={18}>18% GST (Standard)</option>
                    <option value={28}>28% GST</option>
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="text-slate-600 block mb-1 font-semibold">Delivery Schedule (Weeks):</label>
                  <input
                    type="number"
                    value={deliveryWeeks}
                    onChange={(e) => setDeliveryWeeks(parseInt(e.target.value) || 1)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-600 block mb-1 font-semibold">Payment Terms Clause:</label>
                <input
                  type="text"
                  value={paymentTerms}
                  onChange={(e) => setPaymentTerms(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
                />
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
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-50"
                >
                  {actionLoading ? "Generating PDF Quote..." : "Generate Official PDF Quote"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Recalculate Modal */}
      {showRecalcModal && selectedQuote && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900">
                Recalculate Quotation ({selectedQuote.quote_number})
              </h3>
              <button
                onClick={() => setShowRecalcModal(false)}
                className="text-slate-400 hover:text-slate-700 text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleRecalculateSubmit} className="space-y-4 text-xs">
              <p className="text-slate-600">
                Adjusting prices or target margins will create revision <b>v{(selectedQuote.version || 1) + 1}</b> and
                render an updated official PDF quotation without destroying historical records.
              </p>

              <div>
                <label className="text-slate-600 block mb-1 font-semibold">New Unit Selling Price (₹):</label>
                <input
                  type="number"
                  step="0.01"
                  value={recalcPrice}
                  onChange={(e) => setRecalcPrice(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900"
                />
              </div>

              <div>
                <label className="text-slate-600 block mb-1 font-semibold">Target Margin %:</label>
                <input
                  type="number"
                  step="0.1"
                  value={recalcMargin}
                  onChange={(e) => setRecalcMargin(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowRecalcModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm"
                >
                  {actionLoading ? "Updating..." : "Recalculate & Bump Version"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Record Customer Response Modal */}
      {showResponseModal && selectedQuote && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900">
                Record Client Decision ({selectedQuote.quote_number})
              </h3>
              <button
                onClick={() => setShowResponseModal(false)}
                className="text-slate-400 hover:text-slate-700 text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleResponseSubmit} className="space-y-4 text-xs">
              <div>
                <label className="text-slate-600 block mb-1 font-semibold">Customer Commercial Response:</label>
                <select
                  value={custResponse}
                  onChange={(e) => setCustResponse(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-bold"
                >
                  <option value="ACCEPTED">ACCEPTED (Customer approved commercial terms)</option>
                  <option value="REJECTED">REJECTED (Customer declined tender rate)</option>
                  <option value="COUNTER_PROPOSED">COUNTER_PROPOSED (Client requested rate adjustment)</option>
                </select>
              </div>

              <div>
                <label className="text-slate-600 block mb-1 font-semibold">Client Feedback / Notes:</label>
                <textarea
                  rows={3}
                  value={custNotes}
                  onChange={(e) => setCustNotes(e.target.value)}
                  placeholder="e.g. PO #PO-9821 issued by Larsen heavy engineering."
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowResponseModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-sm"
                >
                  {actionLoading ? "Recording..." : "Save Commercial Decision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
