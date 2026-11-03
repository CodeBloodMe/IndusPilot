"use client";

import React, { useState, useEffect } from "react";
import {
  UploadCloud,
  FileCheck2,
  AlertCircle,
  CheckCircle,
  FileText,
  ShieldAlert,
  ArrowRight,
  Sparkles,
  RefreshCw,
  FolderOpen,
  Archive,
  Search,
  Check,
  X,
  Edit3,
  Layers,
  ChevronRight,
  ExternalLink,
  Info
} from "lucide-react";
import {
  getDocuments,
  getQuotations,
  uploadDocumentsMulti,
  confirmQuotation,
  getMaterials,
  getSuppliersDetailed,
  retryDocumentExtraction
} from "@/lib/api";

export default function QuotationUploadView({ onQuotationConfirmed }: { onQuotationConfirmed?: () => void }) {
  const [activeTab, setActiveTab] = useState<"upload" | "documents" | "archive">("upload");
  const [uploading, setUploading] = useState(false);
  const [extractionResult, setExtractionResult] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [quotations, setQuotations] = useState<any[]>([]);
  const [materials, setMaterials] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  
  // Review & Correction state
  const [reviewData, setReviewData] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [archiveSearch, setArchiveSearch] = useState("");
  const [archiveStatusFilter, setArchiveStatusFilter] = useState("");

  useEffect(() => {
    loadAuxiliaryData();
    loadDocuments();
    loadQuotations();
  }, []);

  const loadAuxiliaryData = async () => {
    try {
      const [mats, supps] = await Promise.all([
        getMaterials(),
        getSuppliersDetailed({ isActive: true })
      ]);
      setMaterials(mats);
      setSuppliers(supps);
    } catch (err) {
      console.error("Failed to load auxiliary data:", err);
    }
  };

  const loadDocuments = async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to load documents ledger:", err);
    }
  };

  const loadQuotations = async () => {
    try {
      const quotes = await getQuotations();
      setQuotations(quotes);
    } catch (err) {
      console.error("Failed to load quotations archive:", err);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    try {
      setUploading(true);
      setErrorMsg(null);
      setSaveSuccess(false);

      const filesArray = Array.from(fileList);
      const res = await uploadDocumentsMulti(filesArray);
      
      const primaryResult = res.results ? res.results[0] : res;
      setExtractionResult(primaryResult);
      initReviewData(primaryResult);
      await loadDocuments();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to process quotation document.");
    } finally {
      setUploading(false);
    }
  };

  const initReviewData = (extraction: any) => {
    setReviewData({
      document_id: extraction.document_id,
      supplier_name: extraction.supplier_name || "Unknown Supplier",
      supplier_id: extraction.supplier_id || null,
      quotation_number: extraction.quotation_number || "",
      quotation_date: extraction.quotation_date || new Date().toISOString().split("T")[0],
      valid_until: extraction.valid_until || "",
      payment_terms: extraction.payment_terms || "30 Days Net Credit",
      tax_pct: extraction.tax_pct || 18.0,
      freight_cost: extraction.freight_cost || 0.0,
      other_charges: extraction.other_charges || 0.0,
      is_tax_inclusive: extraction.is_tax_inclusive || false,
      review_notes: "Human verified against quotation document.",
      items: (extraction.items || []).map((it: any) => ({
        material_name: it.material_name,
        material_id: it.material_id || (it.suggested_candidates?.[0]?.material_id) || null,
        grade: it.grade || "Standard",
        thickness_mm: it.thickness_mm || null,
        dimensions: it.dimensions || "",
        quantity: it.quantity || 100.0,
        unit: it.unit || "kg",
        unit_price: it.unit_price || 0.0,
        moq: it.moq || 100.0,
        lead_time_days: it.lead_time_days || 7,
        line_total: it.line_total || (it.quantity * it.unit_price),
        match_confidence: it.match_confidence || 0.85,
        suggested_candidates: it.suggested_candidates || [],
        is_quarantined: it.is_quarantined || false,
        quarantine_reason: it.quarantine_reason || null
      }))
    });
  };

  const handleItemFieldChange = (index: number, field: string, val: any) => {
    if (!reviewData) return;
    const newItems = [...reviewData.items];
    newItems[index] = { ...newItems[index], [field]: val };

    if (field === "quantity" || field === "unit_price") {
      const q = field === "quantity" ? Number(val) : newItems[index].quantity;
      const p = field === "unit_price" ? Number(val) : newItems[index].unit_price;
      newItems[index].line_total = Math.round(q * p * 100) / 100;
    }

    if (field === "material_id") {
      const matched = materials.find((m) => m.id === val);
      if (matched) {
        newItems[index].grade = matched.grade || newItems[index].grade;
        newItems[index].match_confidence = 1.0;
      }
    }

    setReviewData({ ...reviewData, items: newItems });
  };

  // Recalculate totals
  const subtotal = reviewData?.items?.reduce((sum: number, it: any) => sum + (it.line_total || 0), 0) || 0;
  const taxAmount = reviewData?.is_tax_inclusive
    ? 0.0
    : Math.round(subtotal * ((reviewData?.tax_pct || 18.0) / 100) * 100) / 100;
  const totalAmount = reviewData?.is_tax_inclusive
    ? subtotal
    : Math.round((subtotal + taxAmount + (Number(reviewData?.freight_cost) || 0) + (Number(reviewData?.other_charges) || 0)) * 100) / 100;

  const handleConfirmAndSave = async () => {
    if (!reviewData) return;

    try {
      setSaving(true);
      setErrorMsg(null);

      const payload = {
        ...reviewData,
        subtotal,
        tax_amount: taxAmount,
        total_amount: totalAmount,
        original_extracted_json: extractionResult,
        user_corrected_json: { ...reviewData, subtotal, tax_amount: taxAmount, total_amount: totalAmount }
      };

      await confirmQuotation(payload);
      setSaveSuccess(true);
      await loadQuotations();
      await loadDocuments();
      if (onQuotationConfirmed) onQuotationConfirmed();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to confirm and save quotation.");
    } finally {
      setSaving(false);
    }
  };

  const handleReExtract = async (docId: string) => {
    try {
      setUploading(true);
      const res = await retryDocumentExtraction(docId);
      setExtractionResult(res);
      initReviewData(res);
      setActiveTab("upload");
      await loadDocuments();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to re-extract document.");
    } finally {
      setUploading(false);
    }
  };

  // Filtered Archive Quotations
  const filteredQuotations = quotations.filter((q) => {
    const term = archiveSearch.toLowerCase();
    const matchesSearch =
      q.quotation_number?.toLowerCase().includes(term) ||
      q.supplier_name?.toLowerCase().includes(term) ||
      q.items?.some((it: any) => it.material_name?.toLowerCase().includes(term));
    const matchesStatus = archiveStatusFilter ? q.status === archiveStatusFilter : true;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            <span>Intelligent Quotation Ingestion & Human Review Hub</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Automated document extraction across PDF, Excel, CSV and scanned images with deterministic Quality Gate validation and material matching.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
          <button
            onClick={() => setActiveTab("upload")}
            className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
              activeTab === "upload" ? "bg-white text-blue-700 shadow-xs" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Upload & Review</span>
          </button>
          <button
            onClick={() => setActiveTab("documents")}
            className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
              activeTab === "documents" ? "bg-white text-blue-700 shadow-xs" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <FolderOpen className="w-3.5 h-3.5" />
            <span>Document Ledger ({documents.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("archive")}
            className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
              activeTab === "archive" ? "bg-white text-blue-700 shadow-xs" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Archive className="w-3.5 h-3.5" />
            <span>Quotation Archive ({quotations.length})</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ================= TAB 1: UPLOAD & REVIEW ================= */}
      {activeTab === "upload" && (
        <div className="space-y-6">
          {/* Upload Dropzone */}
          <div className="p-8 border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-2xl bg-white text-center flex flex-col items-center justify-center transition-all cursor-pointer relative shadow-xs">
            <input
              type="file"
              multiple
              accept=".pdf,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.tiff"
              onChange={handleFileUpload}
              disabled={uploading}
              className="absolute inset-0 opacity-0 cursor-pointer"
            />
            <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 mb-3 shadow-xs">
              <UploadCloud className={`w-6 h-6 ${uploading ? "animate-bounce" : ""}`} />
            </div>
            <div className="text-sm font-bold text-slate-800">
              {uploading ? "Ingesting quotation & running OCR / Quality Gate..." : "Drag & drop vendor quotation documents, or click to browse"}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Supports industrial PDF, Excel (.xlsx, .xls), CSV, Scanned PNG/JPG (Max 25MB each)
            </div>

            {/* Quick Demo Samples Helper */}
            <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-[11px] text-slate-500">
              <span className="font-semibold text-slate-600">Sample Documents available in data/sample_quotations:</span>
              <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">apex_steel_quotation_ss304.pdf</span>
              <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">national_aluminium_pricelist.xlsx</span>
              <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">mahalaxmi_metals_tubes.csv</span>
              <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">scanned_quotation_apex_steel.png</span>
            </div>
          </div>

          {/* Interactive Human Review Interface */}
          {reviewData && (
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
              {/* Review Header Banner */}
              <div className="p-4 bg-slate-50/80 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-9 h-9 rounded-xl flex items-center justify-center border font-bold ${
                      extractionResult?.validation_status === "QUARANTINED"
                        ? "bg-rose-50 text-rose-700 border-rose-200"
                        : extractionResult?.validation_status === "NEEDS_CORRECTION"
                        ? "bg-amber-50 text-amber-700 border-amber-200"
                        : "bg-emerald-50 text-emerald-700 border-emerald-200"
                    }`}
                  >
                    {extractionResult?.validation_status === "QUARANTINED" ? (
                      <ShieldAlert className="w-5 h-5 text-rose-600" />
                    ) : extractionResult?.validation_status === "NEEDS_CORRECTION" ? (
                      <AlertCircle className="w-5 h-5 text-amber-600" />
                    ) : (
                      <CheckCircle className="w-5 h-5 text-emerald-600" />
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-slate-900">
                        Human Verification & Data Audit Interface
                      </h3>
                      <span
                        className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
                          extractionResult?.validation_status === "QUARANTINED"
                            ? "bg-rose-50 text-rose-700 border-rose-200"
                            : extractionResult?.validation_status === "NEEDS_CORRECTION"
                            ? "bg-amber-50 text-amber-700 border-amber-200"
                            : "bg-emerald-50 text-emerald-700 border-emerald-200"
                        }`}
                      >
                        Quality Gate: {extractionResult?.validation_status || "READY_FOR_REVIEW"}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      File: <strong className="text-slate-700">{extractionResult?.filename}</strong> • OCR Extraction Confidence:{" "}
                      <strong className="text-blue-700">{Math.round((extractionResult?.confidence_score || 0.9) * 100)}%</strong>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleConfirmAndSave}
                    disabled={saving || saveSuccess}
                    className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs px-5 py-2 rounded-xl shadow-sm transition disabled:opacity-50"
                  >
                    <FileCheck2 className="w-4 h-4" />
                    <span>{saving ? "Saving to Database..." : saveSuccess ? "Verified & Saved!" : "Sign-Off & Save Quotation"}</span>
                  </button>
                </div>
              </div>

              {/* Quality Gate Warnings & Alerts */}
              {extractionResult?.quarantine_reasons?.length > 0 && (
                <div className="mx-6 mt-4 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
                  <div className="font-bold flex items-center gap-1.5 mb-1 text-rose-900">
                    <ShieldAlert className="w-4 h-4 text-rose-600" />
                    <span>Quality Gate Quarantine Flaws:</span>
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-rose-700">
                    {extractionResult.quarantine_reasons.map((r: string, idx: number) => (
                      <li key={idx}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}

              {extractionResult?.validation_warnings?.length > 0 && (
                <div className="mx-6 mt-4 p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs">
                  <div className="font-bold flex items-center gap-1.5 mb-1 text-amber-900">
                    <AlertCircle className="w-4 h-4 text-amber-600" />
                    <span>Verification Alerts & Discrepancies:</span>
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-amber-700">
                    {extractionResult.validation_warnings.map((w: string, idx: number) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Side-by-Side Review Section */}
              <div className="p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left 4 Cols: Commercial Parameters Form */}
                <div className="lg:col-span-4 space-y-4 bg-slate-50/70 p-4 rounded-xl border border-slate-200/80 text-xs">
                  <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
                    <Edit3 className="w-3.5 h-3.5 text-blue-600" />
                    <span>Header Terms & Commercials</span>
                  </h4>

                  <div>
                    <label className="block text-slate-600 font-semibold mb-1">Identified Supplier</label>
                    <select
                      value={reviewData.supplier_id || ""}
                      onChange={(e) => {
                        const sId = e.target.value;
                        const found = suppliers.find((s) => s.id === sId);
                        setReviewData({
                          ...reviewData,
                          supplier_id: sId,
                          supplier_name: found ? found.name : reviewData.supplier_name
                        });
                      }}
                      className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-900 font-medium focus:outline-none focus:border-blue-500"
                    >
                      <option value="">{reviewData.supplier_name} (New / Extracted)</option>
                      {suppliers.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name} ({s.city || "India"})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-slate-600 font-semibold mb-1">Quotation Ref No</label>
                      <input
                        type="text"
                        value={reviewData.quotation_number}
                        onChange={(e) => setReviewData({ ...reviewData, quotation_number: e.target.value })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 font-mono text-slate-900 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-slate-600 font-semibold mb-1">Quotation Date</label>
                      <input
                        type="date"
                        value={reviewData.quotation_date}
                        onChange={(e) => setReviewData({ ...reviewData, quotation_date: e.target.value })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-900 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-slate-600 font-semibold mb-1">Validity Period</label>
                      <input
                        type="date"
                        value={reviewData.valid_until}
                        onChange={(e) => setReviewData({ ...reviewData, valid_until: e.target.value })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-900 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-slate-600 font-semibold mb-1">Payment Terms</label>
                      <input
                        type="text"
                        value={reviewData.payment_terms}
                        onChange={(e) => setReviewData({ ...reviewData, payment_terms: e.target.value })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-900 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-slate-600 font-semibold mb-1">GST Tax Rate (%)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={reviewData.tax_pct}
                        onChange={(e) => setReviewData({ ...reviewData, tax_pct: Number(e.target.value) })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-900 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-slate-600 font-semibold mb-1">Freight Charges (₹)</label>
                      <input
                        type="number"
                        value={reviewData.freight_cost}
                        onChange={(e) => setReviewData({ ...reviewData, freight_cost: Number(e.target.value) })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-900 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-slate-600 font-semibold mb-1">Review Notes / Audit Log</label>
                    <textarea
                      rows={2}
                      value={reviewData.review_notes}
                      onChange={(e) => setReviewData({ ...reviewData, review_notes: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-900 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  {/* Real-time Financial Breakdown */}
                  <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1.5">
                    <div className="flex justify-between text-slate-600">
                      <span>Subtotal:</span>
                      <span className="font-mono font-semibold">₹{subtotal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>GST ({reviewData.tax_pct}%):</span>
                      <span className="font-mono font-semibold">₹{taxAmount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>Freight & Handling:</span>
                      <span className="font-mono font-semibold">₹{Number(reviewData.freight_cost || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between text-sm font-bold text-blue-700 border-t border-slate-100 pt-1.5">
                      <span>Total Landed:</span>
                      <span className="font-mono">₹{totalAmount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                    </div>
                  </div>
                </div>

                {/* Right 8 Cols: Editable Extracted Line Items & Material Matcher */}
                <div className="lg:col-span-8 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-blue-600" />
                      <span>Extracted Line Items & Material Matching ({reviewData.items.length})</span>
                    </h4>
                    <span className="text-[11px] text-slate-500">
                      Select catalog material to bind with BOM costing & inventory.
                    </span>
                  </div>

                  <div className="space-y-3">
                    {reviewData.items.map((it: any, idx: number) => (
                      <div
                        key={idx}
                        className={`p-4 rounded-xl border transition ${
                          it.is_quarantined
                            ? "bg-rose-50/40 border-rose-200"
                            : it.material_id
                            ? "bg-slate-50/60 border-slate-200 hover:border-blue-300"
                            : "bg-amber-50/40 border-amber-200"
                        }`}
                      >
                        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 text-xs mb-3">
                          {/* Raw material desc */}
                          <div className="md:col-span-6">
                            <label className="block text-slate-500 font-semibold text-[10px] uppercase mb-0.5">
                              Quoted Material Description
                            </label>
                            <input
                              type="text"
                              value={it.material_name}
                              onChange={(e) => handleItemFieldChange(idx, "material_name", e.target.value)}
                              className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 font-medium text-slate-900 focus:outline-none focus:border-blue-500"
                            />
                          </div>

                          {/* Grade */}
                          <div className="md:col-span-2">
                            <label className="block text-slate-500 font-semibold text-[10px] uppercase mb-0.5">
                              Grade / Spec
                            </label>
                            <input
                              type="text"
                              value={it.grade}
                              onChange={(e) => handleItemFieldChange(idx, "grade", e.target.value)}
                              className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-900 focus:outline-none"
                            />
                          </div>

                          {/* Quantity & Unit */}
                          <div className="md:col-span-2">
                            <label className="block text-slate-500 font-semibold text-[10px] uppercase mb-0.5">
                              Quantity
                            </label>
                            <div className="flex">
                              <input
                                type="number"
                                value={it.quantity}
                                onChange={(e) => handleItemFieldChange(idx, "quantity", Number(e.target.value))}
                                className="w-full bg-white border border-slate-200 rounded-l-lg px-2 py-1.5 text-slate-900 font-mono focus:outline-none"
                              />
                              <span className="bg-slate-100 border border-l-0 border-slate-200 rounded-r-lg px-2 py-1.5 text-[10px] text-slate-600 flex items-center font-bold">
                                {it.unit}
                              </span>
                            </div>
                          </div>

                          {/* Unit price */}
                          <div className="md:col-span-2">
                            <label className="block text-slate-500 font-semibold text-[10px] uppercase mb-0.5">
                              Unit Price (₹)
                            </label>
                            <input
                              type="number"
                              step="0.1"
                              value={it.unit_price}
                              onChange={(e) => handleItemFieldChange(idx, "unit_price", Number(e.target.value))}
                              className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 font-bold text-slate-900 font-mono focus:outline-none"
                            />
                          </div>
                        </div>

                        {/* Material Matcher Selector Row */}
                        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-200/60 text-xs">
                          <div className="flex items-center gap-2 flex-1 min-w-[280px]">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                              <Sparkles className="w-3 h-3 text-blue-600" />
                              <span>Catalogue Match:</span>
                            </span>

                            <select
                              value={it.material_id || ""}
                              onChange={(e) => handleItemFieldChange(idx, "material_id", e.target.value || null)}
                              className="flex-1 bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-800 text-xs font-semibold focus:outline-none focus:border-blue-500"
                            >
                              <option value="">-- Unlinked Raw Item (Manual Match) --</option>
                              {materials.map((m) => (
                                <option key={m.id} value={m.id}>
                                  [{m.code}] {m.name} ({m.grade || "Standard"})
                                </option>
                              ))}
                            </select>

                            {it.material_id && (
                              <span className="bg-emerald-50 text-emerald-700 font-bold text-[10px] px-2 py-0.5 rounded border border-emerald-200 shrink-0">
                                {Math.round((it.match_confidence || 0.85) * 100)}% Match
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-3 text-slate-600 font-mono text-xs">
                            <span>MOQ: <strong>{it.moq} {it.unit}</strong></span>
                            <span>Lead: <strong>{it.lead_time_days}d</strong></span>
                            <span>Total: <strong className="text-blue-700 font-bold">₹{it.line_total?.toLocaleString("en-IN")}</strong></span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ================= TAB 2: DOCUMENT LEDGER ================= */}
      {activeTab === "documents" && (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between text-xs">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Uploaded Documents Ledger</h3>
              <p className="text-slate-500 text-xs">Full physical audit trail of ingested quotation documents and OCR confidence.</p>
            </div>
            <button
              onClick={loadDocuments}
              className="flex items-center gap-1 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold px-3 py-1.5 rounded-lg transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-700 font-bold uppercase text-[10px] border-b border-slate-200">
                <tr>
                  <th className="p-3">File Name</th>
                  <th className="p-3">Format</th>
                  <th className="p-3">Recognized Supplier</th>
                  <th className="p-3">Validation Status</th>
                  <th className="p-3 text-right">Confidence</th>
                  <th className="p-3 text-right">File Size</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {documents.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50 transition">
                    <td className="p-3 font-semibold text-slate-900 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                      <span>{d.filename}</span>
                    </td>
                    <td className="p-3">
                      <span className="font-mono text-[10px] font-bold text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">
                        {d.file_type}
                      </span>
                    </td>
                    <td className="p-3 text-slate-700 font-medium">
                      {d.supplier_name || "Unknown Supplier"}
                    </td>
                    <td className="p-3">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          d.validation_status === "VERIFIED"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : d.validation_status === "QUARANTINED"
                            ? "bg-rose-50 text-rose-700 border-rose-200"
                            : "bg-amber-50 text-amber-700 border-amber-200"
                        }`}
                      >
                        {d.validation_status}
                      </span>
                    </td>
                    <td className="p-3 text-right font-mono font-bold text-blue-700">
                      {Math.round(d.confidence_score * 100)}%
                    </td>
                    <td className="p-3 text-right text-slate-500 font-mono">
                      {(d.file_size / 1024).toFixed(1)} KB
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => handleReExtract(d.id)}
                        className="text-xs text-blue-600 hover:text-blue-800 font-semibold px-2 py-1 rounded hover:bg-blue-50 transition"
                      >
                        Re-Extract
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ================= TAB 3: QUOTATION ARCHIVE ================= */}
      {activeTab === "archive" && (
        <div className="space-y-4">
          {/* Search & Filters */}
          <div className="bg-white border border-slate-200 rounded-2xl p-3 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="relative flex-1 min-w-[280px]">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search archive by quote number, vendor name, or material..."
                value={archiveSearch}
                onChange={(e) => setArchiveSearch(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-slate-500 font-medium">Status:</span>
              <select
                value={archiveStatusFilter}
                onChange={(e) => setArchiveStatusFilter(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:outline-none"
              >
                <option value="">All Statuses</option>
                <option value="VERIFIED">VERIFIED</option>
                <option value="READY_FOR_REVIEW">READY_FOR_REVIEW</option>
                <option value="NEEDS_CORRECTION">NEEDS_CORRECTION</option>
                <option value="QUARANTINED">QUARANTINED</option>
                <option value="ARCHIVED">ARCHIVED</option>
              </select>
            </div>
          </div>

          {/* Quotations List */}
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-bold uppercase text-[10px] border-b border-slate-200">
                  <tr>
                    <th className="p-3">Quotation Number</th>
                    <th className="p-3">Supplier Name</th>
                    <th className="p-3">Date</th>
                    <th className="p-3">Items</th>
                    <th className="p-3 text-right">Landed Total</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Verified By</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {filteredQuotations.map((q) => (
                    <tr key={q.id} className="hover:bg-slate-50 transition">
                      <td className="p-3 font-mono font-bold text-slate-900">
                        {q.quotation_number}
                      </td>
                      <td className="p-3 font-semibold text-slate-800">
                        {q.supplier_name}
                      </td>
                      <td className="p-3 text-slate-500">
                        {q.quotation_date || "N/A"}
                      </td>
                      <td className="p-3 text-slate-600">
                        <span className="font-semibold text-slate-800">{q.items_count}</span> items
                        {q.items?.[0] && (
                          <span className="text-[11px] text-slate-400 block truncate max-w-[200px]">
                            {q.items[0].material_name}
                          </span>
                        )}
                      </td>
                      <td className="p-3 text-right font-mono font-bold text-blue-700 text-sm">
                        ₹{(q.total_amount || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="p-3">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                            q.status === "VERIFIED"
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : q.status === "QUARANTINED"
                              ? "bg-rose-50 text-rose-700 border-rose-200"
                              : q.status === "ARCHIVED"
                              ? "bg-slate-100 text-slate-600 border-slate-200"
                              : "bg-amber-50 text-amber-700 border-amber-200"
                          }`}
                        >
                          {q.status}
                        </span>
                      </td>
                      <td className="p-3 text-slate-500 text-[11px]">
                        {q.verified_by || "Pending Review"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
