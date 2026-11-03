import os
import csv
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PIL import Image, ImageDraw, ImageFont

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample_quotations")
os.makedirs(SAMPLE_DIR, exist_ok=True)

DISCLAIMER_TEXT = "SYNTHETIC DEMONSTRATION DATA — NOT A REAL COMMERCIAL OFFER | SYNTHETIC DEMONSTRATION GSTIN"

def generate_pdf_documents():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Title'], fontSize=16, leading=20, textColor=colors.HexColor('#0F172A'))
    h2_style = ParagraphStyle('DocH2', parent=styles['Heading2'], fontSize=12, leading=16, textColor=colors.HexColor('#1E293B'))
    norm_style = ParagraphStyle('DocNorm', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#334155'))
    disclaimer_style = ParagraphStyle('DocDisclaimer', parent=styles['Italic'], fontSize=8, leading=11, textColor=colors.HexColor('#DC2626'))

    pdf_definitions = [
        # 1. Apex Steel SS304
        {
            "filename": "apex_steel_quotation_ss304.pdf",
            "vendor": "Apex Steel & Alloys Pvt Ltd",
            "address": "Plot 42, Peenya Industrial Area Phase II, Bengaluru, Karnataka - 560058",
            "gstin": "29AABCA8891P1ZX (SYNTHETIC)",
            "quote_no": "APX-2026-QTN-8821",
            "date": "2026-10-25",
            "valid_days": "30 Days",
            "items": [
                ["Stainless Steel 304 Sheet Plate (2B Finish)", "SS304 2B (2mm)", "800", "kg", "Rs. 315.00", "Rs. 252,000.00"]
            ],
            "subtotal": "252,000.00",
            "gst": "45,360.00",
            "freight": "4,500.00",
            "total": "301,860.00",
            "moq": "200 kg",
            "lead": "6 Days",
            "terms": "30 Days Net Credit"
        },
        # 2. Bharat Forgings SS304
        {
            "filename": "bharat_forgings_ss304.pdf",
            "vendor": "Bharat Forgings & Metals",
            "address": "Sector 7, MIDC Bhosari, Pune, Maharashtra - 411026",
            "gstin": "27AAABF1234F1Z5 (SYNTHETIC)",
            "quote_no": "BFM-EST-2026-094",
            "date": "2026-10-24",
            "valid_days": "20 Days",
            "items": [
                ["Stainless Steel 304 Hot Rolled Sheet", "SS 304 HR (2.5mm)", "800", "kg", "Rs. 298.00", "Rs. 238,400.00"]
            ],
            "subtotal": "238,400.00",
            "gst": "42,912.00",
            "freight": "6,000.00",
            "total": "287,312.00",
            "moq": "500 kg",
            "lead": "12 Days",
            "terms": "15 Days Credit"
        },
        # 3. Deccan Precision Alloys SS304
        {
            "filename": "deccan_precision_alloys_ss304.pdf",
            "vendor": "Deccan Precision Alloys Pvt Ltd",
            "address": "Balanagar Industrial Estate, Hyderabad, Telangana - 500037",
            "gstin": "36AABCD9876Q1Z2 (SYNTHETIC)",
            "quote_no": "DPA-IND-QUOTE-441",
            "date": "2026-10-26",
            "valid_days": "30 Days",
            "items": [
                ["Stainless Steel 304 Cold Rolled Plate", "SS 304 CR (2mm)", "800", "kg", "Rs. 330.00", "Rs. 264,000.00"]
            ],
            "subtotal": "264,000.00",
            "gst": "47,520.00",
            "freight": "3,000.00",
            "total": "314,520.00",
            "moq": "100 kg",
            "lead": "4 Days",
            "terms": "45 Days Credit"
        },
        # 4. Titan Alloy & Plate Distribution (Fictionalized MS Structural)
        {
            "filename": "titan_alloy_ms_structural.pdf",
            "vendor": "Titan Alloy & Plate Distribution Ltd",
            "address": "Bandra Kurla Complex Industrial Zone, Mumbai, Maharashtra - 400051",
            "gstin": "27AAACT2727Q1ZW (SYNTHETIC)",
            "quote_no": "TAP-MS-2026-781",
            "date": "2026-10-22",
            "valid_days": "30 Days",
            "items": [
                ["Mild Steel Plate IS 2062 E250 (10mm)", "IS 2062 Gr B", "2000", "kg", "Rs. 66.00", "Rs. 132,000.00"]
            ],
            "subtotal": "132,000.00",
            "gst": "23,760.00",
            "freight": "5,000.00",
            "total": "160,760.00",
            "moq": "1000 kg",
            "lead": "10 Days",
            "terms": "60 Days Net Credit"
        },
        # 5. Janata Inox Direct (Fictionalized SS316 Marine)
        {
            "filename": "janata_inox_ss316_marine.pdf",
            "vendor": "Janata Inox Direct Corp",
            "address": "Industrial Commercial Area, New Delhi, Delhi - 110066",
            "gstin": "07AAACJ2411P1ZL (SYNTHETIC)",
            "quote_no": "JSL-SS316-2026-441",
            "date": "2026-10-20",
            "valid_days": "30 Days",
            "items": [
                ["Stainless Steel 316 Marine Plate (5mm)", "SS316 Acid Resistant", "400", "kg", "Rs. 430.00", "Rs. 172,000.00"]
            ],
            "subtotal": "172,000.00",
            "gst": "30,960.00",
            "freight": "4,500.00",
            "total": "207,460.00",
            "moq": "200 kg",
            "lead": "7 Days",
            "terms": "45 Days Credit"
        },
        # 6. Multi-Item Quotation
        {
            "filename": "multi_item_industrial_alloys.pdf",
            "vendor": "Deccan Precision Alloys Pvt Ltd",
            "address": "Balanagar Industrial Estate, Hyderabad, Telangana - 500037",
            "gstin": "36AABCD9876Q1Z2 (SYNTHETIC)",
            "quote_no": "DPA-MULTI-2026-092",
            "date": "2026-10-27",
            "valid_days": "30 Days",
            "items": [
                ["Stainless Steel 304 Sheet Plate (2mm)", "SS304 2B", "500", "kg", "Rs. 325.00", "Rs. 162,500.00"],
                ["Stainless Steel 316 Marine Plate (5mm)", "SS316", "300", "kg", "Rs. 425.00", "Rs. 127,500.00"],
                ["Free Machining Brass Rod C36000", "C36000", "150", "kg", "Rs. 510.00", "Rs. 76,500.00"]
            ],
            "subtotal": "366,500.00",
            "gst": "65,970.00",
            "freight": "7,500.00",
            "total": "439,970.00",
            "moq": "50 kg per item",
            "lead": "5 Days",
            "terms": "45 Days Credit"
        },
        # 7. Incomplete Quotation (For Quality Gate / Quarantine Testing)
        {
            "filename": "incomplete_vendor_quote.pdf",
            "vendor": "Unknown Metal Works",
            "address": "Industrial Suburb",
            "gstin": "UNSPECIFIED",
            "quote_no": "EST-INCOMPLETE-01",
            "date": "2026-10-28",
            "valid_days": "Unstated",
            "items": [
                ["Stainless Steel Sheet", "SS304", "500", "kg", "Rs. 310.00", "Rs. 155,000.00"],
                ["Laser Cutting Consumables", "Consumable", "10", "nos", "Rs. 0.00", "Rs. 0.00"]
            ],
            "subtotal": "155,000.00",
            "gst": "Unstated",
            "freight": "0.00",
            "total": "155,000.00",
            "moq": "Unstated",
            "lead": "Unstated",
            "terms": "Immediate Cash"
        },
        # 8. Ambiguous Specification Quotation
        {
            "filename": "ambiguous_spec_quotation.pdf",
            "vendor": "Bharat Forgings & Metals",
            "address": "Sector 7, MIDC Bhosari, Pune, Maharashtra - 411026",
            "gstin": "27AAABF1234F1Z5 (SYNTHETIC)",
            "quote_no": "BFM-AMB-2026-77",
            "date": "2026-10-29",
            "valid_days": "15 Days",
            "items": [
                ["Commercial Steel Sheet Material", "Generic Steel", "600", "kg", "Rs. 185.00", "Rs. 111,000.00"]
            ],
            "subtotal": "111,000.00",
            "gst": "19,980.00",
            "freight": "3,500.00",
            "total": "134,480.00",
            "moq": "300 kg",
            "lead": "8 Days",
            "terms": "Advance Payment"
        }
    ]

    for q in pdf_definitions:
        pdf_path = os.path.join(SAMPLE_DIR, q["filename"])
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        story = []

        # Synthetic Banner
        story.append(Paragraph(f"<b>*** {DISCLAIMER_TEXT} ***</b>", disclaimer_style))
        story.append(Spacer(1, 8))

        # Vendor Header
        story.append(Paragraph(f"<b>{q['vendor']}</b>", title_style))
        story.append(Paragraph(f"{q['address']} | GSTIN: {q['gstin']}", norm_style))
        story.append(Spacer(1, 10))

        # Commercial Header
        story.append(Paragraph("<b>TAX INVOICE / COMMERCIAL RATE QUOTATION</b>", h2_style))
        story.append(Paragraph(f"Quotation Ref: <b>{q['quote_no']}</b> | Date: {q['date']} | Validity: {q['valid_days']}", norm_style))
        story.append(Spacer(1, 12))

        # Items Table
        table_data = [
            ["Item Description", "Grade / Spec", "Qty", "Unit", "Unit Price", "Line Total"]
        ]
        for it in q["items"]:
            table_data.append(it)

        t = Table(table_data, colWidths=[180, 110, 45, 45, 80, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (0,1), (0,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,0), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

        # Financial Summary
        story.append(Paragraph(f"<b>Financial Breakdown:</b> Subtotal: Rs. {q['subtotal']} | GST @ 18%: Rs. {q['gst']} | Freight: Rs. {q['freight']}", norm_style))
        story.append(Paragraph(f"<b>Total Landed Payable: Rs. {q['total']}</b>", h2_style))
        story.append(Spacer(1, 10))

        # Commercial Terms
        story.append(Paragraph("<b>Commercial Conditions:</b>", h2_style))
        story.append(Paragraph(f"• Minimum Order Quantity (MOQ): {q['moq']}", norm_style))
        story.append(Paragraph(f"• Delivery Lead Time: {q['lead']} from PO date", norm_style))
        story.append(Paragraph(f"• Payment Terms: {q['terms']}", norm_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<i>Disclaimer: This document is an automated synthetic simulation generated for the IndusPilot hackathon demonstration. Not an enforceable legal contract.</i>", disclaimer_style))

        doc.build(story)
        print(f"Generated PDF: {pdf_path}")


def generate_excel_documents():
    # Excel 1: National Aluminium
    xlsx1_path = os.path.join(SAMPLE_DIR, "national_aluminium_pricelist.xlsx")
    wb1 = openpyxl.Workbook()
    ws1 = wb1.active
    ws1.title = "Aluminium Price List"
    ws1.append([f"*** {DISCLAIMER_TEXT} ***"])
    ws1.append(["National Aluminium Fabricators Pvt Ltd"])
    ws1.append(["Peenya Industrial Estate, Bengaluru | GSTIN: 29AAACN8822B1Z3 (SYNTHETIC)"])
    ws1.append(["Quotation Ref: NAF-2026-QTN-512", "Date: 2026-10-25", "Valid Until: 2026-11-25"])
    ws1.append(["Payment Terms: 30 Days Net Credit", "Lead Time: 8 Days", "MOQ: 150 kg"])
    ws1.append([])
    ws1.append(["Item Description", "Grade / Alloy", "Quantity", "Unit", "Unit Price (INR)", "Line Total (INR)"])
    ws1.append(["Aluminium Alloy 6061-T6 Plate 12mm", "AL6061-T6", 400.0, "kg", 295.0, 118000.0])
    ws1.append(["Aluminium 5052-H32 Marine Sheet 3mm", "AL5052-H32", 250.0, "kg", 280.0, 70000.0])
    ws1.append([])
    ws1.append(["Subtotal", "", "", "", "", 188000.0])
    ws1.append(["GST @ 18%", "", "", "", "", 33840.0])
    ws1.append(["Freight Charges", "", "", "", "", 4200.0])
    ws1.append(["Total Landed Amount", "", "", "", "", 226040.0])
    wb1.save(xlsx1_path)
    print(f"Generated Excel: {xlsx1_path}")

    # Excel 2: Konkan Special Steels (Fictionalized Kalyani Steels)
    xlsx2_path = os.path.join(SAMPLE_DIR, "konkan_special_steels_metals.xlsx")
    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2.title = "Specialty Steels Price List"
    ws2.append([f"*** {DISCLAIMER_TEXT} ***"])
    ws2.append(["Konkan Special Steels Depot"])
    ws2.append(["Mundhwa Industrial Area, Pune | GSTIN: 27AAACK3100M1ZF (SYNTHETIC)"])
    ws2.append(["Quotation Ref: KSS-2026-QTN-309", "Date: 2026-10-24", "Valid Until: 2026-11-24"])
    ws2.append(["Payment Terms: 30 Days Net", "Lead Time: 9 Days", "MOQ: 250 kg"])
    ws2.append([])
    ws2.append(["Item Description", "Grade / Spec", "Quantity", "Unit", "Unit Price (INR)", "Line Total (INR)"])
    ws2.append(["Mild Steel Structural Plate IS 2062", "IS2062", 1500.0, "kg", 69.0, 103500.0])
    ws2.append(["Free Machining Brass Rod C36000", "C36000", 200.0, "kg", 520.0, 104000.0])
    ws2.append([])
    ws2.append(["Subtotal", "", "", "", "", 207500.0])
    ws2.append(["GST @ 18%", "", "", "", "", 37350.0])
    ws2.append(["Freight Charges", "", "", "", "", 5000.0])
    ws2.append(["Total Amount", "", "", "", "", 249850.0])
    wb2.save(xlsx2_path)
    print(f"Generated Excel: {xlsx2_path}")


def generate_csv_documents():
    # CSV 1: Mahalaxmi Metals
    csv1_path = os.path.join(SAMPLE_DIR, "mahalaxmi_metals_tubes.csv")
    with open(csv1_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([f"*** {DISCLAIMER_TEXT} ***"])
        writer.writerow(["Mahalaxmi Metals & Tubes Ltd", "GSTIN: 09AAACM4433K1ZG (SYNTHETIC)"])
        writer.writerow(["Quotation Ref: MMT-QTN-2026-9014", "Date: 2026-10-28", "Valid Until: 2026-11-28"])
        writer.writerow(["Payment Terms: 30 Days Net", "Lead Time: 10 Days", "GST: 18%"])
        writer.writerow([])
        writer.writerow(["Item Description", "Grade", "Quantity", "Unit", "Unit Price", "Line Total"])
        writer.writerow(["Mild Steel Plate IS 2062 E250 10mm", "IS2062", 1200.0, "kg", 66.50, 79800.0])
        writer.writerow(["MS Square Hollow Section 50x50x3mm", "IS4923", 450.0, "meter", 305.00, 137250.0])
        writer.writerow([])
        writer.writerow(["Subtotal", "", "", "", "", 217050.0])
        writer.writerow(["GST @ 18%", "", "", "", "", 39069.0])
        writer.writerow(["Freight Charges", "", "", "", "", 6500.0])
        writer.writerow(["Total Amount", "", "", "", "", 262619.0])
    print(f"Generated CSV: {csv1_path}")

    # CSV 2: Deccan Copper Busbars
    csv2_path = os.path.join(SAMPLE_DIR, "deccan_copper_busbars.csv")
    with open(csv2_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([f"*** {DISCLAIMER_TEXT} ***"])
        writer.writerow(["Deccan Precision Alloys Pvt Ltd", "GSTIN: 36AABCD9876Q1Z2 (SYNTHETIC)"])
        writer.writerow(["Quotation Ref: DPA-CU-2026-092", "Date: 2026-10-27", "Valid Until: 2026-11-27"])
        writer.writerow(["Payment Terms: 45 Days Credit", "Lead Time: 4 Days", "MOQ: 50 kg"])
        writer.writerow([])
        writer.writerow(["Item Description", "Grade", "Quantity", "Unit", "Unit Price", "Line Total"])
        writer.writerow(["Electrolytic Tough Pitch Copper Busbar", "C11000 ETP", 200.0, "kg", 780.00, 156000.0])
        writer.writerow([])
        writer.writerow(["Subtotal", "", "", "", "", 156000.0])
        writer.writerow(["GST @ 18%", "", "", "", "", 28080.0])
        writer.writerow(["Freight Charges", "", "", "", "", 2500.0])
        writer.writerow(["Total Landed Amount", "", "", "", "", 186580.0])
    print(f"Generated CSV: {csv2_path}")


def generate_image_documents():
    # Image 1: Scanned Apex Steel
    img1_path = os.path.join(SAMPLE_DIR, "scanned_quotation_apex_steel.png")
    img1 = Image.new("RGB", (1200, 900), color=(250, 252, 255))
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle([30, 30, 1170, 870], outline=(180, 200, 220), width=2)
    draw1.text((50, 40), f"*** {DISCLAIMER_TEXT} ***", fill=(200, 30, 30))
    draw1.text((50, 70), "APEX STEEL & ALLOYS PVT LTD", fill=(15, 30, 60))
    draw1.text((50, 100), "Plot 42, Peenya 2nd Phase, Bengaluru - 560058 | GSTIN: 29AABCA8891P1ZX (SYNTHETIC)", fill=(80, 90, 110))
    draw1.line([(50, 130), (1150, 130)], fill=(200, 210, 225), width=2)
    draw1.text((50, 150), "COMMERCIAL RATE ESTIMATE / QUOTATION", fill=(20, 40, 80))
    draw1.text((50, 180), "Quotation No: APX-2026-QTN-8841        Date: 2026-10-29        Valid Until: 2026-11-29", fill=(30, 40, 60))
    draw1.text((50, 210), "Payment Terms: 30 Days Net Credit       Delivery Lead Time: 6 Days      MOQ: 200 kg", fill=(30, 40, 60))
    draw1.text((50, 260), "ITEMS SPECIFICATION:", fill=(20, 40, 80))
    draw1.text((50, 290), "1. Stainless Steel Grade 304 Sheet 2mm Thk (2B Finish)", fill=(10, 20, 40))
    draw1.text((50, 320), "   Quantity: 800 kg    |    Rate: INR 312.00 / kg    |    Line Total: INR 249,600.00", fill=(10, 20, 40))
    draw1.text((50, 380), "FINANCIAL SUMMARY:", fill=(20, 40, 80))
    draw1.text((50, 410), "Subtotal: Rs. 249,600.00", fill=(10, 20, 40))
    draw1.text((50, 440), "GST @ 18%: Rs. 44,928.00", fill=(10, 20, 40))
    draw1.text((50, 470), "Freight Charges: Rs. 4,200.00", fill=(10, 20, 40))
    draw1.text((50, 510), "TOTAL LANDED AMOUNT: Rs. 298,728.00", fill=(10, 60, 120))
    draw1.text((50, 580), "Authorized Signatory: Suresh Hegde (Sales Director)", fill=(70, 80, 100))
    img1.save(img1_path)
    print(f"Generated Image: {img1_path}")

    # Image 2: Fasteners
    img2_path = os.path.join(SAMPLE_DIR, "vendor_quote_fasteners.png")
    img2 = Image.new("RGB", (1200, 900), color=(255, 255, 255))
    draw2 = ImageDraw.Draw(img2)
    draw2.rectangle([30, 30, 1170, 870], outline=(150, 170, 190), width=2)
    draw2.text((50, 40), f"*** {DISCLAIMER_TEXT} ***", fill=(200, 30, 30))
    draw2.text((50, 70), "PRECISION FASTENERS & HARDWARE LTD", fill=(20, 35, 65))
    draw2.text((50, 100), "GIDC Naroda, Ahmedabad, Gujarat | GSTIN: 24AABCS5544N1ZQ (SYNTHETIC)", fill=(90, 100, 115))
    draw2.line([(50, 130), (1150, 130)], fill=(210, 220, 230), width=2)
    draw2.text((50, 150), "TAX QUOTATION / RATE ESTIMATE", fill=(25, 45, 90))
    draw2.text((50, 180), "Quotation No: PFH-2026-QTN-1092        Date: 2026-10-30        Valid Until: 2026-12-15", fill=(35, 45, 65))
    draw2.text((50, 210), "Payment Terms: 15 Days Net Credit       Delivery Lead Time: 5 Days      MOQ: 500 nos", fill=(35, 45, 65))
    draw2.text((50, 260), "ITEMS BREAKDOWN:", fill=(20, 40, 80))
    draw2.text((50, 290), "1. SS 304 Hex Bolt M8x25 with Nut (A2-70 Grade)", fill=(10, 20, 40))
    draw2.text((50, 320), "   Quantity: 2000 nos   |   Rate: INR 12.20 / pc    |    Line Total: INR 24,400.00", fill=(10, 20, 40))
    draw2.text((50, 360), "2. SS 304 Hex Bolt M10x35 (A2-70 High Tensile)", fill=(10, 20, 40))
    draw2.text((50, 390), "   Quantity: 1000 nos   |   Rate: INR 17.50 / pc    |    Line Total: INR 17,500.00", fill=(10, 20, 40))
    draw2.text((50, 440), "FINANCIALS:", fill=(20, 40, 80))
    draw2.text((50, 470), "Subtotal: Rs. 41,900.00", fill=(10, 20, 40))
    draw2.text((50, 500), "GST @ 18%: Rs. 7,542.00", fill=(10, 20, 40))
    draw2.text((50, 530), "Freight / Courier: Rs. 1,200.00", fill=(10, 20, 40))
    draw2.text((50, 570), "TOTAL PAYABLE: Rs. 50,642.00", fill=(10, 60, 120))
    img2.save(img2_path)
    print(f"Generated Image: {img2_path}")


if __name__ == "__main__":
    print("=== Generating IndusPilot Comprehensive Synthetic Dataset ===")
    generate_pdf_documents()
    generate_excel_documents()
    generate_csv_documents()
    generate_image_documents()
    print("=== Dataset Generation Complete ===")

