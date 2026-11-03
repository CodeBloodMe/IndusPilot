"use client";

import React, { useState, useEffect } from "react";
import {
  Users2,
  Search,
  Star,
  ShieldCheck,
  Clock,
  Phone,
  Mail,
  MapPin,
  CheckCircle2,
  Plus,
  Edit2,
  FileText,
  Building2,
  Filter,
  X,
  TrendingUp,
  AlertCircle,
  Truck,
  DollarSign
} from "lucide-react";
import { getSuppliersDetailed, createSupplier, updateSupplier, deleteSupplier, getSupplierQuotations } from "@/lib/api";

export default function SuppliersView() {
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [minRating, setMinRating] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  // Modals state
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedSupplier, setSelectedSupplier] = useState<any>(null);
  const [quotationHistory, setQuotationHistory] = useState<any[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    company_name: "",
    contact_person: "",
    email: "",
    phone: "",
    address: "",
    city: "",
    state: "",
    country: "India",
    postal_code: "",
    website: "",
    gst_number: "",
    category: "Primary Raw Materials",
    manufacturing_specialisation: "",
    credit_period_days: 30,
    moq_general: 100,
    capacity_monthly_tons: 50,
    lead_time_days: 7,
    quality_rating: 4.5,
    reliability_score: 90,
    on_time_delivery_pct: 92,
    payment_terms_days: 30,
    is_active: true,
    is_simulated: true,
  });

  useEffect(() => {
    loadSuppliers();
  }, [categoryFilter, minRating]);

  const loadSuppliers = async () => {
    try {
      setLoading(true);
      const data = await getSuppliersDetailed({
        category: categoryFilter || undefined,
        minRating: minRating > 0 ? minRating : undefined,
        isActive: true,
      });
      setSuppliers(data);
    } catch (err) {
      console.error("Failed to load suppliers:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);
    try {
      await createSupplier(formData);
      setIsRegisterOpen(false);
      resetForm();
      await loadSuppliers();
    } catch (err: any) {
      setFormError(err.message || "Failed to register supplier.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSupplier) return;
    setFormError(null);
    setIsSubmitting(true);
    try {
      await updateSupplier(selectedSupplier.id, formData);
      setIsEditOpen(false);
      resetForm();
      await loadSuppliers();
    } catch (err: any) {
      setFormError(err.message || "Failed to update supplier.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const openEditModal = (supplier: any) => {
    setSelectedSupplier(supplier);
    setFormData({
      name: supplier.name || "",
      company_name: supplier.company_name || supplier.name || "",
      contact_person: supplier.contact_person || "",
      email: supplier.email || "",
      phone: supplier.phone || "",
      address: supplier.address || "",
      city: supplier.city || "",
      state: supplier.state || "",
      country: supplier.country || "India",
      postal_code: supplier.postal_code || "",
      website: supplier.website || "",
      gst_number: supplier.gst_number || "",
      category: supplier.category || "Primary Raw Materials",
      manufacturing_specialisation: supplier.manufacturing_specialisation || "",
      credit_period_days: supplier.credit_period_days || 30,
      moq_general: supplier.moq_general || 100,
      capacity_monthly_tons: supplier.capacity_monthly_tons || 50,
      lead_time_days: supplier.lead_time_days || 7,
      quality_rating: supplier.quality_rating || 4.2,
      reliability_score: supplier.reliability_score || 85,
      on_time_delivery_pct: supplier.on_time_delivery_pct || 90,
      payment_terms_days: supplier.payment_terms_days || 30,
      is_active: supplier.is_active ?? true,
      is_simulated: supplier.is_simulated ?? true,
    });
    setFormError(null);
    setIsEditOpen(true);
  };

  const openHistoryDrawer = async (supplier: any) => {
    setSelectedSupplier(supplier);
    setIsHistoryOpen(true);
    try {
      const history = await getSupplierQuotations(supplier.id);
      setQuotationHistory(history);
    } catch (err) {
      console.error("Failed to load quotation history:", err);
      setQuotationHistory([]);
    }
  };

  const handleDeactivate = async (supplierId: string) => {
    if (!confirm("Are you sure you want to deactivate this supplier record?")) return;
    try {
      await deleteSupplier(supplierId);
      await loadSuppliers();
    } catch (err) {
      console.error("Failed to deactivate supplier:", err);
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      company_name: "",
      contact_person: "",
      email: "",
      phone: "",
      address: "",
      city: "",
      state: "",
      country: "India",
      postal_code: "",
      website: "",
      gst_number: "",
      category: "Primary Raw Materials",
      manufacturing_specialisation: "",
      credit_period_days: 30,
      moq_general: 100,
      capacity_monthly_tons: 50,
      lead_time_days: 7,
      quality_rating: 4.5,
      reliability_score: 90,
      on_time_delivery_pct: 92,
      payment_terms_days: 30,
      is_active: true,
      is_simulated: true,
    });
    setSelectedSupplier(null);
    setFormError(null);
  };

  const filtered = suppliers.filter((s) => {
    const q = searchTerm.toLowerCase();
    return (
      s.name.toLowerCase().includes(q) ||
      (s.city && s.city.toLowerCase().includes(q)) ||
      (s.gst_number && s.gst_number.toLowerCase().includes(q)) ||
      (s.manufacturing_specialisation && s.manufacturing_specialisation.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Users2 className="w-5 h-5 text-blue-600" />
            <span>Industrial Supplier Intelligence Directory</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Verified vendor profiles, GSTIN validation, commercial credit terms, on-time track records, and price history.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              resetForm();
              setIsRegisterOpen(true);
            }}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            <span>Register Supplier</span>
          </button>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3 flex-1 min-w-[280px]">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by supplier name, city, GSTIN, material specialisation..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-slate-500 font-medium">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span>Category:</span>
          </div>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:outline-none"
          >
            <option value="">All Categories</option>
            <option value="Primary Raw Materials">Primary Raw Materials</option>
            <option value="Aluminium & Non-Ferrous">Aluminium & Non-Ferrous</option>
            <option value="Fasteners & Hardware">Fasteners & Hardware</option>
            <option value="Consumables & Chemicals">Consumables & Chemicals</option>
          </select>

          <select
            value={minRating}
            onChange={(e) => setMinRating(Number(e.target.value))}
            className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:outline-none"
          >
            <option value="0">All Ratings</option>
            <option value="4.0">★ 4.0+ Quality</option>
            <option value="4.5">★ 4.5+ Top Tier</option>
          </select>
        </div>
      </div>

      {/* Suppliers Grid */}
      {loading ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-xs text-slate-400">
          Loading supplier intelligence ledger...
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-xs text-slate-500">
          No suppliers found matching the criteria. Click &quot;Register Supplier&quot; to onboard a vendor.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((s) => (
            <div
              key={s.id}
              className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:shadow-md transition flex flex-col justify-between"
            >
              <div>
                {/* Header row */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm leading-tight">{s.name}</h3>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                        {s.category || "Primary Raw Materials"}
                      </span>
                      {s.is_simulated && (
                        <span className="text-[9px] font-mono font-medium text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded">
                          Simulated
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1 bg-amber-50 text-amber-800 px-2 py-0.5 rounded font-bold text-xs">
                    <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                    <span>{Number(s.quality_rating || 4.2).toFixed(1)}</span>
                  </div>
                </div>

                {/* Specialisation */}
                {s.manufacturing_specialisation && (
                  <p className="text-[11px] text-slate-600 mb-3 line-clamp-1 italic">
                    {s.manufacturing_specialisation}
                  </p>
                )}

                {/* Location & Contact Details */}
                <div className="space-y-1 text-xs text-slate-600 mb-3">
                  {s.city && (
                    <div className="flex items-center gap-1.5 text-slate-500">
                      <MapPin className="w-3 h-3 text-slate-400" />
                      <span>{s.city}, {s.state || "India"}</span>
                    </div>
                  )}
                  {s.contact_person && (
                    <div className="flex items-center gap-1.5">
                      <Building2 className="w-3 h-3 text-slate-400" />
                      <span>{s.contact_person}</span>
                    </div>
                  )}
                  {s.gst_number && (
                    <div className="text-[10px] font-mono text-slate-500 mt-1">
                      GSTIN: <span className="text-slate-800 font-semibold">{s.gst_number}</span>
                    </div>
                  )}
                </div>

                {/* Performance & Commercial terms metrics */}
                <div className="grid grid-cols-3 gap-2 bg-slate-50 p-2.5 rounded-lg text-center mb-3">
                  <div>
                    <span className="text-[9px] text-slate-500 uppercase tracking-wider block">Credit</span>
                    <span className="text-xs font-bold text-slate-800">{s.credit_period_days || 30} Days</span>
                  </div>
                  <div>
                    <span className="text-[9px] text-slate-500 uppercase tracking-wider block">Lead Time</span>
                    <span className="text-xs font-bold text-slate-800">{s.lead_time_days || 7} Days</span>
                  </div>
                  <div>
                    <span className="text-[9px] text-slate-500 uppercase tracking-wider block">On-Time</span>
                    <span className="text-xs font-bold text-emerald-600">{s.on_time_delivery_pct || 90}%</span>
                  </div>
                </div>

                {/* Spend & Quotations Summary */}
                <div className="flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-100 pt-2 mb-3">
                  <span>Quotes: <strong className="text-slate-800">{s.quotation_count || 0}</strong></span>
                  <span>Spend: <strong className="text-slate-800">₹{(s.total_historical_spend || 0).toLocaleString()}</strong></span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
                <button
                  onClick={() => openHistoryDrawer(s)}
                  className="flex-1 flex items-center justify-center gap-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium py-1.5 rounded transition"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Quotes History</span>
                </button>
                <button
                  onClick={() => openEditModal(s)}
                  className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition"
                  title="Edit Supplier"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Register Supplier Modal */}
      {isRegisterOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl border border-slate-200 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                <Plus className="w-4 h-4 text-blue-600" />
                <span>Onboard & Register Industrial Supplier</span>
              </h3>
              <button
                onClick={() => setIsRegisterOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-xs p-3 rounded-lg flex items-center gap-2 mb-4">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleRegisterSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Supplier / Trade Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                    placeholder="e.g. Apex Steel & Alloys Pvt Ltd"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Company Entity Name</label>
                  <input
                    type="text"
                    value={formData.company_name}
                    onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                    placeholder="Full legal company name"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                  >
                    <option value="Primary Raw Materials">Primary Raw Materials</option>
                    <option value="Aluminium & Non-Ferrous">Aluminium & Non-Ferrous</option>
                    <option value="Fasteners & Hardware">Fasteners & Hardware</option>
                    <option value="Consumables & Chemicals">Consumables & Chemicals</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">GSTIN Number</label>
                  <input
                    type="text"
                    value={formData.gst_number}
                    onChange={(e) => setFormData({ ...formData, gst_number: e.target.value.toUpperCase() })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 font-mono text-slate-900 focus:outline-none focus:border-blue-500"
                    placeholder="29AABCS1429B1Z4"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Credit Terms (Days)</label>
                  <input
                    type="number"
                    value={formData.credit_period_days}
                    onChange={(e) => setFormData({ ...formData, credit_period_days: Number(e.target.value) })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Contact Person</label>
                  <input
                    type="text"
                    value={formData.contact_person}
                    onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                    placeholder="Key contact"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                    placeholder="orders@vendor.com"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Phone</label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                    placeholder="+91 98..."
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">City</label>
                  <input
                    type="text"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                    placeholder="e.g. Bengaluru"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">State</label>
                  <input
                    type="text"
                    value={formData.state}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                    placeholder="e.g. Karnataka"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Standard Lead Time (Days)</label>
                  <input
                    type="number"
                    value={formData.lead_time_days}
                    onChange={(e) => setFormData({ ...formData, lead_time_days: Number(e.target.value) })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Manufacturing Specialisation</label>
                <input
                  type="text"
                  value={formData.manufacturing_specialisation}
                  onChange={(e) => setFormData({ ...formData, manufacturing_specialisation: e.target.value })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                  placeholder="e.g. Cold Rolled Stainless Steel 304/316 2B Sheets, Laser Cutting Tolerances"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsRegisterOpen(false)}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-medium transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2 rounded-lg shadow-sm transition disabled:opacity-50"
                >
                  {isSubmitting ? "Registering..." : "Save Supplier"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Supplier Modal */}
      {isEditOpen && selectedSupplier && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl border border-slate-200 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-blue-600" />
                <span>Edit Supplier Profile: {selectedSupplier.name}</span>
              </h3>
              <button
                onClick={() => setIsEditOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-xs p-3 rounded-lg flex items-center gap-2 mb-4">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleEditSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Contact Person</label>
                  <input
                    type="text"
                    value={formData.contact_person}
                    onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Quality Rating (1-5)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="1"
                    max="5"
                    value={formData.quality_rating}
                    onChange={(e) => setFormData({ ...formData, quality_rating: Number(e.target.value) })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Credit Terms (Days)</label>
                  <input
                    type="number"
                    value={formData.credit_period_days}
                    onChange={(e) => setFormData({ ...formData, credit_period_days: Number(e.target.value) })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Standard Lead Time (Days)</label>
                  <input
                    type="number"
                    value={formData.lead_time_days}
                    onChange={(e) => setFormData({ ...formData, lead_time_days: Number(e.target.value) })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => handleDeactivate(selectedSupplier.id)}
                  className="text-red-600 hover:text-red-700 font-semibold px-2 py-1"
                >
                  Deactivate Supplier
                </button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsEditOpen(false)}
                    className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-medium transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2 rounded-lg shadow-sm transition disabled:opacity-50"
                  >
                    {isSubmitting ? "Updating..." : "Update Supplier"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Quotation History Drawer Modal */}
      {isHistoryOpen && selectedSupplier && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-end">
          <div className="bg-white h-full max-w-lg w-full p-6 shadow-2xl border-l border-slate-200 flex flex-col justify-between overflow-y-auto">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
                <div>
                  <h3 className="font-bold text-slate-900 text-base">{selectedSupplier.name}</h3>
                  <p className="text-xs text-slate-500">Historical Quotation Records & Pricing Trends</p>
                </div>
                <button
                  onClick={() => setIsHistoryOpen(false)}
                  className="text-slate-400 hover:text-slate-600 p-1"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {quotationHistory.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400">
                  No historical quotation records found for this vendor.
                </div>
              ) : (
                <div className="space-y-3">
                  {quotationHistory.map((q) => (
                    <div key={q.id} className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-mono font-bold text-slate-900">{q.quotation_number}</span>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                          q.status === "VERIFIED"
                            ? "bg-emerald-50 text-emerald-700"
                            : q.status === "QUARANTINED"
                            ? "bg-rose-50 text-rose-700"
                            : "bg-amber-50 text-amber-700"
                        }`}>
                          {q.status}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-500 mb-2">
                        <span>Date: {q.quotation_date || "N/A"}</span>
                        <span>Total: <strong className="text-slate-900">₹{(q.total_amount || 0).toLocaleString()}</strong></span>
                      </div>

                      {q.items && q.items.length > 0 && (
                        <div className="border-t border-slate-200/60 pt-2 space-y-1">
                          {q.items.map((it: any, idx: number) => (
                            <div key={idx} className="flex items-center justify-between text-[11px] text-slate-600">
                              <span className="truncate max-w-[240px]">{it.material_name}</span>
                              <span className="font-semibold text-slate-900">₹{it.unit_price}/{it.unit}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-slate-100">
              <button
                onClick={() => setIsHistoryOpen(false)}
                className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold py-2 rounded-lg text-xs transition"
              >
                Close History
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
