import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.entities import (
    Organization, Factory, User, Supplier, SupplierMaterial,
    Material, Inventory, InventoryMovement, Product,
    BillOfMaterials, BOMItem, SupplierQuotation, QuotationItem,
    PurchaseRequisition, NegotiationSession, NegotiationMessage,
    CustomerQuotation, ApprovalRequest, UploadedDocument
)

def seed_induspilot_demonstration_data(db: Session, force_reset: bool = False) -> dict:
    """
    Seeds comprehensive, reproducible synthetic demonstration data for IndusPilot
    addressing Tech4Bharat 2026 Problem Statement 4.1.
    Populates 10 industrial suppliers, 20 materials with engineering specs,
    30+ historical quotations across metals and consumables, and document ingestion ledgers.
    """
    existing_org = db.query(Organization).filter_by(slug="apex-precision-fab").first()
    if existing_org and not force_reset:
        return {"status": "ALREADY_SEEDED", "organization_id": existing_org.id}

    if existing_org and force_reset:
        # Clear existing demo entities in reverse dependency order
        db.query(ApprovalRequest).delete()
        db.query(NegotiationMessage).delete()
        db.query(NegotiationSession).delete()
        db.query(CustomerQuotation).delete()
        db.query(PurchaseRequisition).delete()
        db.query(QuotationItem).delete()
        db.query(SupplierQuotation).delete()
        db.query(UploadedDocument).delete()
        db.query(BOMItem).delete()
        db.query(BillOfMaterials).delete()
        db.query(InventoryMovement).delete()
        db.query(Inventory).delete()
        db.query(SupplierMaterial).delete()
        db.query(Product).delete()
        db.query(Material).delete()
        db.query(Supplier).delete()
        db.query(User).delete()
        db.query(Factory).delete()
        db.query(Organization).delete()
        db.commit()

    # 1. Organization & Factory
    org = Organization(
        id="org_tech4bharat_induspilot_demo",
        name="Apex Precision Fabrication Works Pvt Ltd",
        slug="apex-precision-fab",
        manufacturing_category="Metal Fabrication & Industrial Assemblies",
        currency="INR",
        currency_symbol="₹",
        tax_id="29AAACA1122K1Z9", # Karnataka GSTIN
        default_overhead_pct=12.0
    )
    db.add(org)
    db.flush()

    factory = Factory(
        id="factory_bengaluru_peenya",
        organization_id=org.id,
        name="Peenya Fabrication Plant 1",
        location="Plot 42, 2nd Phase, Peenya Industrial Area, Bengaluru, Karnataka - 560058",
        capacity_monthly_hours=1400.0,
        electricity_tariff_kwh=8.50,
        default_labor_rate_hr=180.0
    )
    db.add(factory)

    # 2. Demo User
    demo_user = User(
        id="user_rajesh_sharma",
        organization_id=org.id,
        email="owner@apexprecisionworks.com",
        hashed_password="demo_hashed_password_induspilot_2026",
        full_name="Rajesh Sharma",
        role="OWNER"
    )
    db.add(demo_user)

    # 3. 20 Industrial Materials with Engineering Specifications & Physical Forms
    materials_specs = [
        ("MAT-SS-304", "Stainless Steel 304 Sheet Plate", "Sheet Metal", "SS304 2B", "ASTM A240 / ASME SA240", "Sheet, Plate, Coil", "kg", 7.93, 310.0, "Cold rolled 2B finish sheet for brackets and industrial enclosures"),
        ("MAT-SS-316", "Stainless Steel 316 Marine Plate", "Sheet Metal", "SS316 Acid Resistant", "ASTM A240 / DIN 1.4401", "Plate, Sheet", "kg", 8.00, 420.0, "Molybdenum-bearing austenitic steel for high corrosion resistance"),
        ("MAT-MS-IS2062", "Mild Steel Plate IS 2062 E250", "Structural Steel", "IS 2062 Gr B", "IS 2062:2011", "Plate, Sheet, Coil", "kg", 7.85, 68.0, "Structural quality hot-rolled carbon steel plates"),
        ("MAT-AL-6061", "Aluminium Alloy 6061-T6 Plate", "Aluminium", "6061-T6", "ASTM B209 / AMS 4027", "Plate, Bar, Extrusion", "kg", 2.70, 290.0, "Precipitation-hardened aluminium alloy with excellent machinability"),
        ("MAT-AL-5052", "Aluminium 5052-H32 Sheet", "Aluminium", "5052-H32", "ASTM B209 / AMS 4016", "Sheet, Coil", "kg", 2.68, 275.0, "Marine grade aluminium sheet with high formability"),
        ("MAT-CU-C11000", "Electrolytic Tough Pitch Copper Busbar", "Copper", "C11000 ETP", "ASTM B187 / IS 191", "Bar, Busbar, Strip", "kg", 8.89, 780.0, "High electrical conductivity copper for busbars and terminals"),
        ("MAT-BR-C36000", "Free Machining Brass Rod", "Brass", "C36000", "ASTM B16 / IS 319", "Rod, Hex Bar, Round Bar", "kg", 8.50, 520.0, "Standard free-cutting brass rod for turned fasteners and bushes"),
        ("MAT-FAST-M8", "SS 304 Hex Bolt M8x25 with Nut", "Fasteners", "A2-70", "DIN 933 / ISO 4017", "Bolt, Fastener, Nut", "nos", 0.05, 12.50, "Stainless steel high tensile hex flange bolt and nylon locknut"),
        ("MAT-FAST-M10", "SS 304 Hex Bolt M10x35", "Fasteners", "A2-70", "DIN 933 / ISO 4017", "Bolt, Fastener", "nos", 0.08, 18.00, "Heavy-duty structural mounting fastener"),
        ("MAT-WELD-308L", "SS 308L TIG Welding Filler Wire 2.4mm", "Consumables", "AWS A5.9 ER308L", "AWS A5.9 / ASME SFA 5.9", "Wire, Rod", "kg", 7.90, 480.0, "Low-carbon austenitic welding wire for SS304 fabrication"),
        ("MAT-WELD-E7018", "Low Hydrogen Arc Welding Electrode 3.15mm", "Consumables", "E7018", "AWS A5.1 / IS 814", "Electrode, Rod", "kg", 7.85, 140.0, "Basic coated low-hydrogen electrode for mild steel structures"),
        ("MAT-COAT-POWDER", "Pure Polyester Powder Coating - Grey 7035", "Finishing", "RAL 7035 Textured", "Qualicoat Class 1", "Powder", "kg", 1.20, 320.0, "Industrial thermosetting electrostatic powder coating"),
        ("MAT-COAT-PASS", "Chemical Passivation & Pickling Acid Gel", "Chemicals", "ASTM A967", "ASTM A380 / A967", "Gel, Liquid", "kg", 1.15, 180.0, "Pickling solution for restoring chromium oxide layer on welds"),
        ("MAT-PIPE-SS304", "SS 304 Seamless Pipe 2 inch NB Sch 40", "Pipes", "ASTM A312 TP304", "ASTM A312 / ASME SA312", "Pipe, Tube", "meter", 5.40, 950.0, "Industrial fluid and structural piping"),
        ("MAT-SEAL-NBR", "NBR Nitrile Rubber Gasket Sheet 3mm", "Rubber", "Shore 70A", "ASTM D2000", "Sheet, Gasket", "sqm", 3.60, 450.0, "Oil resistant sealing sheet for flanges"),
        ("MAT-BOX-CORR", "Heavy Duty 7-Ply Corrugated Packing Carton", "Packaging", "Kraft 300 GSM", "IS 2771 Part 1", "Box, Packaging", "nos", 0.80, 85.0, "Custom export packaging carton for bracket assemblies"),
        ("MAT-MS-TUBE", "MS Square Hollow Section 50x50x3mm", "Structural Steel", "IS 4923 YSt 240", "IS 4923:1997", "Tube, Section", "meter", 4.30, 310.0, "Square tube section for machine base frames"),
        ("MAT-CUT-DISC", "Abrasive Cutting Disc 4 inch for Inox", "Consumables", "Alumina Inox", "EN 12413", "Disc, Consumables", "nos", 0.10, 45.0, "High-speed thin cutting wheel for stainless steel sheets"),
        ("MAT-PALLET-PIN", "Treated Pine Wood Pallet 1200x1000mm", "Packaging", "ISPM-15 Certified", "IPPC ISPM-15", "Pallet", "nos", 15.0, 650.0, "Heat treated four-way industrial transport pallet"),
        ("MAT-RIVET-POP", "Blind Rivet 4.8mm Aluminium / Steel", "Fasteners", "Dome Head", "DIN 7337", "Rivet, Fastener", "nos", 0.01, 2.80, "Structural blind rivet for panel joining")
    ]

    material_objects: Dict[str, Material] = {}
    for code, name, cat, grade, spec, forms, unit, density, cost, desc in materials_specs:
        m = Material(
            organization_id=org.id,
            code=code,
            name=name,
            category=cat,
            grade=grade,
            specifications=spec,
            manufacturing_forms=forms,
            unit=unit,
            density_g_cm3=density,
            standard_cost=cost,
            description=desc,
            is_active=True
        )
        db.add(m)
        material_objects[code] = m
    db.flush()

    # 4. Warehouse Inventory Levels
    inventory_data = [
        ("MAT-SS-304", 250.0, 50.0, 0.0, 50.0, 100.0, "Bay 1, Rack A-04"),
        ("MAT-SS-316", 120.0, 0.0, 0.0, 40.0, 80.0, "Bay 1, Rack A-06"),
        ("MAT-MS-IS2062", 1500.0, 200.0, 500.0, 300.0, 500.0, "Yard 2, Heavy Stacks"),
        ("MAT-AL-6061", 85.0, 10.0, 0.0, 25.0, 50.0, "Bay 2, Rack B-02"),
        ("MAT-AL-5052", 110.0, 20.0, 0.0, 30.0, 60.0, "Bay 2, Rack B-04"),
        ("MAT-CU-C11000", 45.0, 0.0, 0.0, 15.0, 30.0, "Secure Vault C-1"),
        ("MAT-BR-C36000", 60.0, 0.0, 0.0, 20.0, 40.0, "Secure Vault C-2"),
        ("MAT-FAST-M8", 2400.0, 400.0, 1000.0, 500.0, 1000.0, "Bin 14, Small Parts"),
        ("MAT-FAST-M10", 850.0, 0.0, 0.0, 200.0, 400.0, "Bin 15, Small Parts"),
        ("MAT-WELD-308L", 35.0, 5.0, 0.0, 15.0, 25.0, "Stores, Weld Cage"),
        ("MAT-WELD-E7018", 80.0, 10.0, 0.0, 25.0, 50.0, "Stores, Weld Cage"),
        ("MAT-COAT-POWDER", 60.0, 0.0, 20.0, 20.0, 40.0, "Paint Shop Rack P-1"),
        ("MAT-PIPE-SS304", 45.0, 0.0, 0.0, 15.0, 30.0, "Pipe Yard P-3"),
        ("MAT-BOX-CORR", 180.0, 0.0, 0.0, 50.0, 100.0, "Packaging Area"),
        ("MAT-MS-TUBE", 90.0, 0.0, 0.0, 30.0, 60.0, "Yard 1, Tube Racks"),
        ("MAT-CUT-DISC", 150.0, 20.0, 50.0, 40.0, 80.0, "Tool Crib T-2"),
        ("MAT-PALLET-PIN", 25.0, 5.0, 0.0, 10.0, 20.0, "Dispatch Bay D-1"),
        ("MAT-RIVET-POP", 3500.0, 500.0, 0.0, 1000.0, 2000.0, "Bin 16, Small Parts"),
    ]
    for code, cur, res, inc, saf, reord, loc in inventory_data:
        m = material_objects[code]
        inv = Inventory(
            organization_id=org.id,
            material_id=m.id,
            current_stock=cur,
            reserved_stock=res,
            incoming_stock=inc,
            safety_stock=saf,
            reorder_level=reord,
            warehouse_location=loc
        )
        db.add(inv)
    db.flush()

    # 5. 10 Verified Simulated Suppliers with Diverse Profiles
    suppliers_specs = [
        ("Apex Steel & Alloys Pvt Ltd", "Apex Steel & Alloys Pvt Ltd", "Suresh Hegde", "sales@apexsteelalloys.com", "+91 80 2839 8811", "Plot 42, Peenya 2nd Phase", "Bengaluru", "Karnataka", "India", "560058", "https://apexsteelalloys.com", "29AABCA8891P1ZX", "Primary Raw Materials", "Precision Stainless Steel Plates & Sheets", 30, 200.0, 150.0, 6, 4.6, 92.0, 94.0, 30, 1850000.0, 14, 0.4),
        ("Bharat Forgings & Metals", "Bharat Forgings & Metals Ltd", "Manoj Kulkarni", "quotes@bharatforgings.co.in", "+91 20 2712 4433", "Sector 7, MIDC Bhosari", "Pune", "Maharashtra", "India", "411026", "https://bharatforgings.co.in", "27AAABF1234F1Z5", "Primary Raw Materials", "Heavy Forgings & Mild Steel Structural Sections", 15, 500.0, 300.0, 12, 4.0, 78.0, 80.0, 15, 1420000.0, 9, 1.2),
        ("Deccan Precision Alloys", "Deccan Precision Alloys Pvt Ltd", "Venkatesh Rao", "commercials@deccanalloys.in", "+91 40 2377 1199", "Balanagar Industrial Area", "Hyderabad", "Telangana", "India", "500037", "https://deccanalloys.in", "36AABCD9876Q1Z2", "Primary Raw Materials", "Specialty Stainless & Nickel Alloy Cold Rolled Stock", 45, 100.0, 80.0, 4, 4.8, 96.0, 98.0, 45, 2350000.0, 18, 0.2),
        ("Tata Steel Industrial Distribution", "Tata Steel Industrial Distribution Ltd", "Praveen Nair", "industrial@tatasteel-channel.com", "+91 22 6665 8282", "Bandra Kurla Complex", "Mumbai", "Maharashtra", "India", "400051", "https://tatasteel.com", "27AAACT2727Q1ZW", "Primary Raw Materials", "HR/CR Coils, Heavy Plates & Structural Beams", 60, 1000.0, 500.0, 10, 4.9, 98.0, 97.0, 60, 4200000.0, 22, 0.1),
        ("Jindal Stainless Direct Sales", "Jindal Stainless Direct Sales Corp", "Anil Singhal", "inox.direct@jindalstainless.com", "+91 11 4146 2000", "Jindal Centre, Bhikaiji Cama Place", "New Delhi", "Delhi", "India", "110066", "https://jindalstainless.com", "07AAACJ2411P1ZL", "Primary Raw Materials", "Austenitic & Ferritic Stainless Steel Sheets & Strips", 45, 300.0, 200.0, 8, 4.7, 94.0, 92.0, 45, 3100000.0, 16, 0.3),
        ("Kalyani Steels Regional Depot", "Kalyani Steels Regional Depot", "Sunil Deshmukh", "depot.pune@kalyanisteels.com", "+91 20 6621 5000", "Mundhwa Industrial Area", "Pune", "Maharashtra", "India", "411036", "https://kalyanisteels.com", "27AAACK3100M1ZF", "Primary Raw Materials", "Engineering Carbon & Alloy Steels, Round Bars", 30, 250.0, 120.0, 9, 4.3, 85.0, 88.0, 30, 980000.0, 8, 0.8),
        ("National Aluminium Fabricators", "National Aluminium Fabricators Pvt Ltd", "Karthik Swaminathan", "sales@nationalalum.in", "+91 80 2836 1144", "Peenya Industrial Area, Phase 1", "Bengaluru", "Karnataka", "India", "560058", "https://nationalalum.in", "29AAACN8822B1Z3", "Aluminium & Non-Ferrous", "Aircraft & Marine Grade Aluminium Plates (6061, 5052)", 30, 150.0, 60.0, 8, 4.6, 91.0, 93.0, 30, 1120000.0, 11, 0.5),
        ("Mahalaxmi Metals & Tubes", "Mahalaxmi Metals & Tubes Ltd", "Dinesh Aggarwal", "orders@mahalaxmimetals.com", "+91 120 456 7890", "Site IV Industrial Area, Sahibabad", "Ghaziabad", "Uttar Pradesh", "India", "201010", "https://mahalaxmimetals.com", "09AAACM4433K1ZG", "Primary Raw Materials", "Mild Steel Pipes, ERW Tubes & Hollow Sections", 30, 400.0, 180.0, 10, 4.2, 83.0, 85.0, 30, 890000.0, 7, 0.9),
        ("Precision Fasteners & Components Ltd", "Precision Fasteners & Components Ltd", "Kiran Patel", "sales@precisionfasteners.in", "+91 79 2583 0011", "GIDC Naroda", "Ahmedabad", "Gujarat", "India", "382330", "https://precisionfasteners.in", "24AABCS5544N1ZQ", "Fasteners & Hardware", "High-Tensile A2-70/A4-80 Stainless Fasteners & Bolts", 30, 500.0, 40.0, 5, 4.5, 90.0, 95.0, 30, 650000.0, 15, 0.4),
        ("Industrial Gases & Welding Sol.", "Industrial Gases & Welding Solutions LLP", "Mohan Das", "welding@indgas.co.in", "+91 44 2624 3311", "Ambattur Industrial Estate", "Chennai", "Tamil Nadu", "India", "600058", "https://indgas.co.in", "33AABCP7766J1ZV", "Consumables & Chemicals", "Argon Gas, TIG/MIG Welding Wires & Passivation Chemicals", 30, 50.0, 30.0, 4, 4.6, 93.0, 91.0, 30, 740000.0, 13, 0.3)
    ]

    supplier_objects: Dict[str, Supplier] = {}
    for (
        name, comp_name, contact, email, phone, addr, city, state, country, postal, web, gst,
        cat, spec, cred_days, moq, cap, lt_days, q_rat, rel, ot_pct, pay_terms, spend, orders, rej
    ) in suppliers_specs:
        s = Supplier(
            organization_id=org.id,
            name=name,
            company_name=comp_name,
            contact_person=contact,
            email=email,
            phone=phone,
            address=addr,
            city=city,
            state=state,
            country=country,
            postal_code=postal,
            website=web,
            gst_number=gst,
            category=cat,
            manufacturing_specialisation=spec,
            credit_period_days=cred_days,
            moq_general=moq,
            capacity_monthly_tons=cap,
            lead_time_days=lt_days,
            quality_rating=q_rat,
            reliability_score=rel,
            on_time_delivery_pct=ot_pct,
            payment_terms_days=pay_terms,
            total_historical_spend=spend,
            total_orders_count=orders,
            rejection_rate_pct=rej,
            is_active=True,
            is_simulated=True
        )
        db.add(s)
        supplier_objects[name] = s
    db.flush()

    # 6. Supplier Material Catalogs
    sup_apex = supplier_objects["Apex Steel & Alloys Pvt Ltd"]
    sup_bharat = supplier_objects["Bharat Forgings & Metals"]
    sup_deccan = supplier_objects["Deccan Precision Alloys"]
    sup_tata = supplier_objects["Tata Steel Industrial Distribution"]
    sup_jindal = supplier_objects["Jindal Stainless Direct Sales"]
    sup_nat_alum = supplier_objects["National Aluminium Fabricators"]
    sup_fasteners = supplier_objects["Precision Fasteners & Components Ltd"]
    sup_gases = supplier_objects["Industrial Gases & Welding Sol."]

    db.add(SupplierMaterial(supplier_id=sup_apex.id, material_name=material_objects["MAT-SS-304"].name, material_grade="SS304 2B", standard_unit_price=315.0, unit="kg", moq=200.0, typical_lead_time_days=6, capacity_monthly_units=15000.0))
    db.add(SupplierMaterial(supplier_id=sup_bharat.id, material_name=material_objects["MAT-SS-304"].name, material_grade="SS304 HR", standard_unit_price=298.0, unit="kg", moq=500.0, typical_lead_time_days=12, capacity_monthly_units=12000.0))
    db.add(SupplierMaterial(supplier_id=sup_deccan.id, material_name=material_objects["MAT-SS-304"].name, material_grade="SS304 CR", standard_unit_price=330.0, unit="kg", moq=100.0, typical_lead_time_days=4, capacity_monthly_units=20000.0))
    db.add(SupplierMaterial(supplier_id=sup_jindal.id, material_name=material_objects["MAT-SS-304"].name, material_grade="SS304 2B", standard_unit_price=318.0, unit="kg", moq=300.0, typical_lead_time_days=7, capacity_monthly_units=25000.0))
    db.add(SupplierMaterial(supplier_id=sup_tata.id, material_name=material_objects["MAT-MS-IS2062"].name, material_grade="IS 2062 Gr B", standard_unit_price=66.0, unit="kg", moq=1000.0, typical_lead_time_days=10, capacity_monthly_units=50000.0))
    db.add(SupplierMaterial(supplier_id=sup_nat_alum.id, material_name=material_objects["MAT-AL-6061"].name, material_grade="6061-T6", standard_unit_price=295.0, unit="kg", moq=150.0, typical_lead_time_days=8, capacity_monthly_units=8000.0))
    db.add(SupplierMaterial(supplier_id=sup_fasteners.id, material_name=material_objects["MAT-FAST-M8"].name, material_grade="A2-70", standard_unit_price=12.20, unit="nos", moq=500.0, typical_lead_time_days=5, capacity_monthly_units=50000.0))
    db.add(SupplierMaterial(supplier_id=sup_gases.id, material_name=material_objects["MAT-WELD-308L"].name, material_grade="AWS A5.9 ER308L", standard_unit_price=475.0, unit="kg", moq=50.0, typical_lead_time_days=4, capacity_monthly_units=3000.0))
    db.flush()

    # 7. Products & Bill of Materials (BOM)
    product = Product(
        organization_id=org.id,
        code="SS304-BRK-500",
        name="Stainless Steel Industrial Bracket (500mm)",
        category="Heavy Mounting Brackets",
        description="High-load cantilever support bracket for industrial electrical cabinets and pumps."
    )
    db.add(product)
    db.flush()

    bom = BillOfMaterials(
        organization_id=org.id,
        product_id=product.id,
        version="v2.1",
        is_active=True,
        batch_quantity=1.0
    )
    db.add(bom)
    db.flush()

    db.add(BOMItem(bom_id=bom.id, material_id=material_objects["MAT-SS-304"].id, quantity_per_unit=2.0, unit="kg", wastage_pct=5.0, process_stage="CNC Laser Cutting & Press Brake"))
    db.add(BOMItem(bom_id=bom.id, material_id=material_objects["MAT-FAST-M8"].id, quantity_per_unit=4.0, unit="nos", wastage_pct=2.0, process_stage="Hardware Sub-Assembly"))
    db.add(BOMItem(bom_id=bom.id, material_id=material_objects["MAT-WELD-308L"].id, quantity_per_unit=0.15, unit="kg", wastage_pct=10.0, process_stage="TIG Robotic Welding"))
    db.add(BOMItem(bom_id=bom.id, material_id=material_objects["MAT-BOX-CORR"].id, quantity_per_unit=0.10, unit="nos", wastage_pct=1.0, process_stage="Final Packaging"))
    db.flush()

    # 8. Seed Uploaded Documents Ledger (Real demonstrator documents)
    doc_specs = [
        ("apex_steel_quotation_ss304.pdf", "PDF", 2903, sup_apex.id, "READY_FOR_REVIEW", 0.96),
        ("bharat_forgings_ss304.pdf", "PDF", 2872, sup_bharat.id, "READY_FOR_REVIEW", 0.94),
        ("deccan_precision_alloys_ss304.pdf", "PDF", 2876, sup_deccan.id, "READY_FOR_REVIEW", 0.97),
        ("national_aluminium_pricelist.xlsx", "XLSX", 5200, sup_nat_alum.id, "READY_FOR_REVIEW", 0.95),
        ("mahalaxmi_metals_tubes.csv", "CSV", 890, supplier_objects["Mahalaxmi Metals & Tubes"].id, "READY_FOR_REVIEW", 0.93),
        ("scanned_quotation_apex_steel.png", "PNG", 18500, sup_apex.id, "READY_FOR_REVIEW", 0.91),
        ("vendor_quote_fasteners.png", "PNG", 16800, sup_fasteners.id, "READY_FOR_REVIEW", 0.92),
    ]

    doc_objects: Dict[str, UploadedDocument] = {}
    for fname, ftype, fsize, s_id, v_status, conf in doc_specs:
        fpath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "sample_quotations", fname)
        doc = UploadedDocument(
            organization_id=org.id,
            supplier_id=s_id,
            filename=fname,
            file_path=fpath,
            file_type=ftype,
            file_size=fsize,
            processing_status="COMPLETED",
            validation_status=v_status,
            status=v_status,
            confidence_score=conf,
            raw_text=f"Sample quotation document for {fname}"
        )
        db.add(doc)
        doc_objects[fname] = doc
    db.flush()

    # 9. 32 Structured Quotation Records (Covering Multiple Materials, Dates, Suppliers & Edge Cases)
    quotes_data = [
        # --- Current Batch for 800 kg SS304 Shortage ---
        (sup_apex.id, "apex_steel_quotation_ss304.pdf", "APX-2026-QTN-8821", -2, 28, 252000.0, 45360.0, 18.0, 4500.0, False, 301860.0, "VERIFIED", [
            ("MAT-SS-304", "Stainless Steel 304 Sheet Plate (2B Finish)", "AISI 304 / DIN 1.4301", 2.0, 800.0, "kg", 315.0, 200.0, 6, 252000.0)
        ]),
        (sup_bharat.id, "bharat_forgings_ss304.pdf", "BFM-EST-2026-094", -3, 12, 238400.0, 42912.0, 18.0, 6000.0, False, 287312.0, "VERIFIED", [
            ("MAT-SS-304", "Stainless Steel 304 Hot Rolled Sheet", "SS 304 HR Industrial Grade", 2.5, 800.0, "kg", 298.0, 500.0, 12, 238400.0)
        ]),
        (sup_deccan.id, "deccan_precision_alloys_ss304.pdf", "DPA-IND-QUOTE-441", -1, 29, 264000.0, 47520.0, 18.0, 3000.0, False, 314520.0, "VERIFIED", [
            ("MAT-SS-304", "Stainless Steel 304 Cold Rolled Plate", "SS 304 CR Precision Tolerance", 2.0, 800.0, "kg", 330.0, 100.0, 4, 264000.0)
        ]),
        (sup_jindal.id, None, "JSL-DIRECT-2026-902", -4, 26, 254400.0, 45792.0, 18.0, 5500.0, False, 305692.0, "VERIFIED", [
            ("MAT-SS-304", "Stainless Steel 304 2B Finish Sheet", "SS304", 2.0, 800.0, "kg", 318.0, 300.0, 7, 254400.0)
        ]),
        (sup_tata.id, None, "TATA-IND-2026-781", -5, 25, 257600.0, 46368.0, 18.0, 4000.0, False, 307968.0, "VERIFIED", [
            ("MAT-SS-304", "Tata Inox SS 304 Commercial Sheet", "SS304", 2.0, 800.0, "kg", 322.0, 400.0, 8, 257600.0)
        ]),

        # --- Historical Quotations for SS304 (Price trend over last 6 months) ---
        (sup_apex.id, None, "APX-2026-QTN-7104", -35, -5, 155000.0, 27900.0, 18.0, 3500.0, False, 186400.0, "ARCHIVED", [
            ("MAT-SS-304", "Stainless Steel 304 Sheet 2mm", "SS304", 2.0, 500.0, "kg", 310.0, 200.0, 6, 155000.0)
        ]),
        (sup_bharat.id, None, "BFM-EST-2026-042", -60, -30, 177000.0, 31860.0, 18.0, 4800.0, False, 213660.0, "ARCHIVED", [
            ("MAT-SS-304", "SS 304 Hot Rolled Sheet", "SS304", 2.5, 600.0, "kg", 295.0, 500.0, 14, 177000.0)
        ]),
        (sup_deccan.id, None, "DPA-IND-QUOTE-312", -90, -60, 131200.0, 23616.0, 18.0, 2500.0, False, 157316.0, "ARCHIVED", [
            ("MAT-SS-304", "SS 304 CR Sheet Precision", "SS304", 2.0, 400.0, "kg", 328.0, 100.0, 4, 131200.0)
        ]),
        (sup_apex.id, None, "APX-2025-QTN-5591", -120, -90, 305000.0, 54900.0, 18.0, 5000.0, False, 364900.0, "ARCHIVED", [
            ("MAT-SS-304", "Stainless Steel 304 Sheet 2mm", "SS304", 2.0, 1000.0, "kg", 305.0, 200.0, 7, 305000.0)
        ]),
        (sup_bharat.id, None, "BFM-EST-2025-881", -150, -120, 232000.0, 41760.0, 18.0, 6200.0, False, 279960.0, "ARCHIVED", [
            ("MAT-SS-304", "SS 304 Sheet Plate", "SS304", 2.0, 800.0, "kg", 290.0, 500.0, 15, 232000.0)
        ]),

        # --- Stainless Steel 316 Quotations ---
        (sup_deccan.id, None, "DPA-SS316-2026-101", -8, 22, 168000.0, 30240.0, 18.0, 3200.0, False, 201440.0, "VERIFIED", [
            ("MAT-SS-316", "Stainless Steel 316 Marine Plate 5mm", "SS316 Acid Resistant", 5.0, 400.0, "kg", 420.0, 100.0, 5, 168000.0)
        ]),
        (sup_jindal.id, None, "JSL-SS316-2026-441", -10, 20, 172000.0, 30960.0, 18.0, 4500.0, False, 207460.0, "VERIFIED", [
            ("MAT-SS-316", "Jindal Inox SS 316 Plate 5mm", "SS316", 5.0, 400.0, "kg", 430.0, 200.0, 7, 172000.0)
        ]),

        # --- Mild Steel IS2062 Quotations ---
        (sup_tata.id, None, "TATA-MS-2026-551", -7, 23, 132000.0, 23760.0, 18.0, 5000.0, False, 160760.0, "VERIFIED", [
            ("MAT-MS-IS2062", "Tata Steel Mild Steel Plate IS 2062 E250", "IS 2062 Gr B", 10.0, 2000.0, "kg", 66.0, 1000.0, 10, 132000.0)
        ]),
        (supplier_objects["Mahalaxmi Metals & Tubes"].id, "mahalaxmi_metals_tubes.csv", "MMT-QTN-2026-9014", -6, 24, 217050.0, 39069.0, 18.0, 6500.0, False, 262619.0, "VERIFIED", [
            ("MAT-MS-IS2062", "Mild Steel Plate IS 2062 E250 10mm", "IS2062", 10.0, 1200.0, "kg", 66.50, 400.0, 10, 79800.0),
            ("MAT-MS-TUBE", "MS Square Hollow Section 50x50x3mm", "IS4923", 3.0, 450.0, "meter", 305.0, 100.0, 10, 137250.0)
        ]),
        (supplier_objects["Kalyani Steels Regional Depot"].id, None, "KLY-MS-2026-309", -9, 21, 103500.0, 18630.0, 18.0, 4200.0, False, 126330.0, "VERIFIED", [
            ("MAT-MS-IS2062", "Kalyani Mild Steel Structural Plate", "IS 2062", 8.0, 1500.0, "kg", 69.0, 500.0, 8, 103500.0)
        ]),

        # --- Aluminium 6061 and 5052 Quotations ---
        (sup_nat_alum.id, "national_aluminium_pricelist.xlsx", "NAF-2026-QTN-512", -5, 25, 188000.0, 33840.0, 18.0, 4200.0, False, 226040.0, "VERIFIED", [
            ("MAT-AL-6061", "Aluminium Alloy 6061-T6 Plate 12mm", "6061-T6", 12.0, 400.0, "kg", 295.0, 150.0, 8, 118000.0),
            ("MAT-AL-5052", "Aluminium 5052-H32 Marine Sheet 3mm", "5052-H32", 3.0, 250.0, "kg", 280.0, 100.0, 8, 70000.0)
        ]),
        (sup_deccan.id, None, "DPA-AL-2026-881", -6, 24, 152500.0, 27450.0, 18.0, 3000.0, False, 182950.0, "VERIFIED", [
            ("MAT-AL-6061", "Deccan Precision Al 6061-T6 Plate", "6061-T6", 10.0, 500.0, "kg", 305.0, 100.0, 5, 152500.0)
        ]),

        # --- Copper and Brass Quotations ---
        (sup_deccan.id, None, "DPA-CU-2026-092", -4, 26, 156000.0, 28080.0, 18.0, 2500.0, False, 186580.0, "VERIFIED", [
            ("MAT-CU-C11000", "Electrolytic Tough Pitch Copper Busbar", "C11000 ETP", 5.0, 200.0, "kg", 780.0, 50.0, 4, 156000.0)
        ]),
        (supplier_objects["Kalyani Steels Regional Depot"].id, None, "KLY-BR-2026-414", -7, 23, 104000.0, 18720.0, 18.0, 2200.0, False, 124920.0, "VERIFIED", [
            ("MAT-BR-C36000", "Free Machining Brass Rod C36000", "C36000", 25.0, 200.0, "kg", 520.0, 50.0, 7, 104000.0)
        ]),

        # --- Fasteners & Hardware Quotations ---
        (sup_fasteners.id, "vendor_quote_fasteners.png", "PFH-2026-QTN-1092", -3, 27, 41900.0, 7542.0, 18.0, 1200.0, False, 50642.0, "VERIFIED", [
            ("MAT-FAST-M8", "SS 304 Hex Bolt M8x25 with Nut (A2-70 Grade)", "A2-70", None, 2000.0, "nos", 12.20, 500.0, 5, 24400.0),
            ("MAT-FAST-M10", "SS 304 Hex Bolt M10x35 (A2-70 High Tensile)", "A2-70", None, 1000.0, "nos", 17.50, 200.0, 5, 17500.0)
        ]),
        (sup_apex.id, None, "APX-FAST-2026-302", -5, 25, 45500.0, 8190.0, 18.0, 1500.0, False, 55190.0, "VERIFIED", [
            ("MAT-FAST-M8", "SS 304 Hex Bolt M8x25 with Nut", "A2-70", None, 2000.0, "nos", 13.00, 500.0, 6, 26000.0),
            ("MAT-FAST-M10", "SS 304 Hex Bolt M10x35", "A2-70", None, 1000.0, "nos", 19.50, 200.0, 6, 19500.0)
        ]),

        # --- Consumables & Welding Quotations ---
        (sup_gases.id, None, "IGW-2026-QTN-801", -2, 28, 47500.0, 8550.0, 18.0, 1500.0, False, 57550.0, "VERIFIED", [
            ("MAT-WELD-308L", "SS 308L TIG Welding Filler Wire 2.4mm", "AWS A5.9 ER308L", None, 100.0, "kg", 475.0, 20.0, 3, 47500.0)
        ]),
        (sup_gases.id, None, "IGW-2026-QTN-802", -8, 22, 14000.0, 2520.0, 18.0, 1000.0, False, 17520.0, "VERIFIED", [
            ("MAT-WELD-E7018", "Low Hydrogen Arc Welding Electrode 3.15mm", "E7018", None, 100.0, "kg", 140.0, 25.0, 3, 14000.0)
        ]),

        # --- Packaging & Auxiliary Quotations ---
        (sup_fasteners.id, None, "PFH-PACK-2026-051", -11, 19, 25500.0, 4590.0, 18.0, 1800.0, False, 31890.0, "VERIFIED", [
            ("MAT-BOX-CORR", "Heavy Duty 7-Ply Corrugated Packing Carton", "Kraft 300 GSM", None, 300.0, "nos", 85.0, 100.0, 7, 25500.0)
        ]),

        # --- DRAFT & PENDING REVIEW Quotations ---
        (sup_apex.id, "scanned_quotation_apex_steel.png", "APX-2026-QTN-8841", -1, 30, 249600.0, 44928.0, 18.0, 4200.0, False, 298728.0, "READY_FOR_REVIEW", [
            ("MAT-SS-304", "Stainless Steel Grade 304 Sheet 2mm Thk (2B Finish)", "SS304", 2.0, 800.0, "kg", 312.0, 200.0, 6, 249600.0)
        ]),
        (sup_jindal.id, None, "JSL-DRAFT-2026-01", 0, 30, 192000.0, 34560.0, 18.0, 3800.0, False, 230360.0, "NEEDS_CORRECTION", [
            ("MAT-SS-304", "SS 304 Sheet 2B Finish", "SS304", 2.0, 600.0, "kg", 320.0, 300.0, 7, 192000.0)
        ]),
        (sup_bharat.id, None, "BFM-REV-2026-099", 0, 14, 147500.0, 26550.0, 18.0, 3500.0, False, 177550.0, "NEEDS_CORRECTION", [
            ("MAT-SS-304", "SS304 Plate Commercial", "SS304", 3.0, 500.0, "kg", 295.0, 500.0, 12, 147500.0)
        ]),

        # --- QUARANTINED Edge Case Quotations ---
        (sup_bharat.id, None, "BFM-ERR-2026-999", -1, 10, 0.0, 0.0, 18.0, 0.0, False, 0.0, "QUARANTINED", [
            ("MAT-SS-304", "Unverified Raw Material SS304", "Unknown", None, 500.0, "kg", 0.0, 100.0, 7, 0.0)
        ]),
        (sup_apex.id, None, "APX-DUP-2026-8821", -2, 28, 252000.0, 45360.0, 18.0, 4500.0, False, 301860.0, "QUARANTINED", [
            ("MAT-SS-304", "Duplicate Submission of APX-2026-QTN-8821", "SS304", 2.0, 800.0, "kg", 315.0, 200.0, 6, 252000.0)
        ]),

        # --- Pipes & Finishing Quotes ---
        (supplier_objects["Mahalaxmi Metals & Tubes"].id, None, "MMT-PIPE-2026-118", -12, 18, 95000.0, 17100.0, 18.0, 3500.0, False, 115600.0, "VERIFIED", [
            ("MAT-PIPE-SS304", "SS 304 Seamless Pipe 2 inch NB Sch 40", "ASTM A312 TP304", None, 100.0, "meter", 950.0, 20.0, 8, 95000.0)
        ]),
        (sup_fasteners.id, None, "PFH-RIVET-2026-820", -14, 16, 28000.0, 5040.0, 18.0, 800.0, False, 33840.0, "VERIFIED", [
            ("MAT-RIVET-POP", "Blind Rivet 4.8mm Aluminium / Steel", "Dome Head", None, 10000.0, "nos", 2.80, 2000.0, 5, 28000.0)
        ]),
        (sup_gases.id, None, "IGW-COAT-2026-302", -15, 15, 32000.0, 5760.0, 18.0, 1200.0, False, 38960.0, "VERIFIED", [
            ("MAT-COAT-POWDER", "Pure Polyester Powder Coating - Grey 7035", "RAL 7035", None, 100.0, "kg", 320.0, 20.0, 4, 32000.0)
        ])
    ]

    seeded_quotations_count = 0
    for (
        s_id, doc_key, q_no, days_offset, validity_offset,
        subtot, tax_amt, tax_p, freight, is_tax_inc, tot, stat, items_list
    ) in quotes_data:
        q_date = datetime.utcnow() + timedelta(days=days_offset)
        v_date = datetime.utcnow() + timedelta(days=validity_offset)
        d_id = doc_objects[doc_key].id if doc_key and doc_key in doc_objects else None

        sq = SupplierQuotation(
            organization_id=org.id,
            supplier_id=s_id,
            document_id=d_id,
            quotation_number=q_no,
            quotation_date=q_date,
            valid_until=v_date,
            subtotal=subtot,
            tax_amount=tax_amt,
            tax_pct=tax_p,
            freight_cost=freight,
            other_charges=0.0,
            is_tax_inclusive=is_tax_inc,
            total_amount=tot,
            currency="INR",
            status=stat,
            review_notes="Demonstration verified quotation record." if stat == "VERIFIED" else ("Quarantined: Pricing/Duplicate flaw." if stat == "QUARANTINED" else "Pending human verification."),
            original_extracted_json={"quotation_number": q_no, "subtotal": subtot, "total": tot, "items_count": len(items_list)},
            user_corrected_json={"quotation_number": q_no, "subtotal": subtot, "total": tot, "items_count": len(items_list)},
            verified_at=datetime.utcnow() if stat == "VERIFIED" else None,
            verified_by="Estimator / Reviewer" if stat == "VERIFIED" else None
        )
        db.add(sq)
        db.flush()

        for m_code, raw_name, grade, thk, qty, unit, price, moq, lt, l_tot in items_list:
            mat = material_objects.get(m_code)
            is_quar = (price <= 0 or stat == "QUARANTINED")
            quar_r = "Zero or invalid unit price." if price <= 0 else (None if stat != "QUARANTINED" else "Duplicate or flawed extraction.")

            db.add(QuotationItem(
                quotation_id=sq.id,
                material_id=mat.id if mat else None,
                material_name_raw=raw_name,
                grade=grade,
                thickness_mm=thk,
                quantity=qty,
                unit=unit,
                unit_price=price,
                moq=moq,
                lead_time_days=lt,
                line_total=l_tot,
                tax_pct=tax_p,
                match_confidence=0.95 if mat else 0.40,
                is_quarantined=is_quar,
                quarantine_reason=quar_r
            ))
        seeded_quotations_count += 1

    # 10. Active Purchase Requisition
    pr = PurchaseRequisition(
        organization_id=org.id,
        requisition_number="PR-2026-OCT-001",
        material_id=material_objects["MAT-SS-304"].id,
        required_quantity=800.0,
        unit="kg",
        required_by_date=datetime.utcnow() + timedelta(days=14),
        reason="Order #ORD-771: 500 SS304 Industrial Brackets Shortage",
        budget_limit=320000.0,
        status="PENDING"
    )
    db.add(pr)

    # 11. Negotiation Session
    first_apex_quote = db.query(SupplierQuotation).filter(
        SupplierQuotation.quotation_number == "APX-2026-QTN-8821"
    ).first()

    neg_session = NegotiationSession(
        organization_id=org.id,
        supplier_id=sup_apex.id,
        quotation_id=first_apex_quote.id if first_apex_quote else None,
        material_name="Stainless Steel 304 Sheet Plate",
        quantity=800.0,
        original_unit_price=315.0,
        target_unit_price=295.0,
        current_offered_price=315.0,
        status="READY_FOR_APPROVAL",
        simulation_mode=True
    )
    db.add(neg_session)
    db.flush()

    db.add(NegotiationMessage(
        session_id=neg_session.id,
        round_number=1,
        sender_type="BUYER_AGENT",
        message_text="Draft counteroffer proposing revised unit price of ₹295.00/kg with 15 days prompt payment terms.",
        proposed_unit_price=295.0,
        payment_terms="15 Days Net",
        delivery_days=6,
        is_simulated=True
    ))

    # 12. Customer Quotation Sample
    cq = CustomerQuotation(
        organization_id=org.id,
        quote_number="CQ-2026-OCT-5001",
        customer_name="Larsen Heavy Engineering",
        customer_company="Larsen & Heavy Corp Industrial Systems",
        customer_email="procurement@larsenheavy.com",
        product_id=product.id,
        quantity=500.0,
        unit_production_cost=637.0,
        unit_selling_price=850.0,
        subtotal=425000.0,
        tax_pct=18.0,
        tax_amount=76500.0,
        total_amount=501500.0,
        margin_pct=25.06,
        payment_terms="50% Advance, 50% Against Delivery",
        validity_days=15,
        delivery_weeks=3,
        status="APPROVED",
        is_loss_making=False
    )
    db.add(cq)

    # 13. Pending Approval Requests
    appr1 = ApprovalRequest(
        organization_id=org.id,
        request_type="NEGOTIATION_DISPATCH",
        entity_id=neg_session.id,
        requested_by="Negotiation Agent",
        details_json={
            "supplier_name": "Apex Steel & Alloys Pvt Ltd",
            "material": "Stainless Steel 304 Sheet Plate",
            "quantity": 800.0,
            "opening_rate": 315.0,
            "target_counter": 295.0,
            "projected_savings": 16000.0
        },
        status="PENDING"
    )
    db.add(appr1)

    db.commit()

    return {
        "status": "SUCCESS",
        "organization_id": org.id,
        "suppliers_count": len(supplier_objects),
        "materials_count": len(material_objects),
        "product_id": product.id,
        "quotations_seeded": seeded_quotations_count,
        "documents_seeded": len(doc_objects),
        "negotiation_session_id": neg_session.id,
        "customer_quote_id": cq.id
    }
