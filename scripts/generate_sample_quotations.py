import os
import csv
import openpyxl
from PIL import Image, ImageDraw

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample_quotations")
os.makedirs(SAMPLE_DIR, exist_ok=True)

def generate_samples():
    print(f"Generating sample quotation documents in: {SAMPLE_DIR}")

    # 1. Excel Quotation: National Aluminium Fabricators
    xlsx_path = os.path.join(SAMPLE_DIR, "national_aluminium_pricelist.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Commercial Quotation"

    ws.append(["National Aluminium Fabricators Pvt Ltd"])
    ws.append(["Address: Peenya Industrial Estate, Bengaluru | GSTIN: 29AAACN8822B1Z3"])
    ws.append(["Quotation Ref: NAF-2026-QTN-512", "Date: 2026-10-25", "Valid Until: 2026-11-25"])
    ws.append(["Payment Terms: 30 Days Net Credit", "Delivery Lead Time: 8 Days", "MOQ: 150 kg"])
    ws.append([])
    ws.append(["Item Description", "Grade / Alloy", "Quantity", "Unit", "Unit Price (INR)", "Line Total (INR)"])
    ws.append(["Aluminium Alloy 6061-T6 Plate 12mm", "AL6061-T6", 400.0, "kg", 295.0, 118000.0])
    ws.append(["Aluminium 5052-H32 Marine Sheet 3mm", "AL5052-H32", 250.0, "kg", 280.0, 70000.0])
    ws.append([])
    ws.append(["Subtotal", "", "", "", "", 188000.0])
    ws.append(["GST @ 18%", "", "", "", "", 33840.0])
    ws.append(["Freight Charges", "", "", "", "", 4200.0])
    ws.append(["Total Landed Amount", "", "", "", "", 226040.0])
    wb.save(xlsx_path)
    print(f"Created: {xlsx_path}")

    # 2. CSV Quotation: Mahalaxmi Metals & Tubes
    csv_path = os.path.join(SAMPLE_DIR, "mahalaxmi_metals_tubes.csv")
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Mahalaxmi Metals & Tubes Ltd"])
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
    print(f"Created: {csv_path}")

    # 3. Image Quotation 1: Scanned Apex Steel Quotation
    img1_path = os.path.join(SAMPLE_DIR, "scanned_quotation_apex_steel.png")
    img1 = Image.new("RGB", (1200, 900), color=(250, 252, 255))
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle([30, 30, 1170, 870], outline=(180, 200, 220), width=2)
    draw1.text((50, 50), "APEX STEEL & ALLOYS PVT LTD", fill=(15, 30, 60))
    draw1.text((50, 80), "Plot 42, Peenya 2nd Phase, Bengaluru - 560058 | GSTIN: 29AABCA8891P1ZX", fill=(80, 90, 110))
    draw1.line([(50, 110), (1150, 110)], fill=(200, 210, 225), width=2)
    draw1.text((50, 130), "COMMERCIAL QUOTATION", fill=(20, 40, 80))
    draw1.text((50, 160), "Quotation No: APX-2026-QTN-8841        Date: 2026-10-29        Valid Until: 2026-11-29", fill=(30, 40, 60))
    draw1.text((50, 190), "Payment Terms: 30 Days Net Credit       Delivery Lead Time: 6 Days      MOQ: 200 kg", fill=(30, 40, 60))
    draw1.text((50, 240), "ITEMS:", fill=(20, 40, 80))
    draw1.text((50, 270), "1. Stainless Steel Grade 304 Sheet 2mm Thk (2B Finish)", fill=(10, 20, 40))
    draw1.text((50, 300), "   Quantity: 800 kg    |    Rate: INR 312.00 / kg    |    Line Total: INR 249,600.00", fill=(10, 20, 40))
    draw1.text((50, 360), "FINANCIAL SUMMARY:", fill=(20, 40, 80))
    draw1.text((50, 390), "Subtotal: Rs. 249,600.00", fill=(10, 20, 40))
    draw1.text((50, 420), "GST @ 18%: Rs. 44,928.00", fill=(10, 20, 40))
    draw1.text((50, 450), "Freight Charges: Rs. 4,200.00", fill=(10, 20, 40))
    draw1.text((50, 490), "TOTAL LANDED AMOUNT: Rs. 298,728.00", fill=(10, 60, 120))
    draw1.text((50, 560), "Authorized Signatory: Suresh Hegde (Sales Director)", fill=(70, 80, 100))
    img1.save(img1_path)
    print(f"Created: {img1_path}")

    # 4. Image Quotation 2: Precision Fasteners
    img2_path = os.path.join(SAMPLE_DIR, "vendor_quote_fasteners.png")
    img2 = Image.new("RGB", (1200, 900), color=(255, 255, 255))
    draw2 = ImageDraw.Draw(img2)
    draw2.rectangle([30, 30, 1170, 870], outline=(150, 170, 190), width=2)
    draw2.text((50, 50), "PRECISION FASTENERS & HARDWARE LTD", fill=(20, 35, 65))
    draw2.text((50, 80), "GIDC Naroda, Ahmedabad, Gujarat | GSTIN: 24AABCS5544N1ZQ", fill=(90, 100, 115))
    draw2.line([(50, 110), (1150, 110)], fill=(210, 220, 230), width=2)
    draw2.text((50, 130), "TAX QUOTATION / RATE ESTIMATE", fill=(25, 45, 90))
    draw2.text((50, 160), "Quotation No: PFH-2026-QTN-1092        Date: 2026-10-30        Valid Until: 2026-12-15", fill=(35, 45, 65))
    draw2.text((50, 190), "Payment Terms: 15 Days Net Credit       Delivery Lead Time: 5 Days      MOQ: 500 nos", fill=(35, 45, 65))
    draw2.text((50, 240), "ITEMS BREAKDOWN:", fill=(20, 40, 80))
    draw2.text((50, 270), "1. SS 304 Hex Bolt M8x25 with Nut (A2-70 Grade)", fill=(10, 20, 40))
    draw2.text((50, 300), "   Quantity: 2000 nos   |   Rate: INR 12.20 / pc    |    Line Total: INR 24,400.00", fill=(10, 20, 40))
    draw2.text((50, 340), "2. SS 304 Hex Bolt M10x35 (A2-70 High Tensile)", fill=(10, 20, 40))
    draw2.text((50, 370), "   Quantity: 1000 nos   |   Rate: INR 17.50 / pc    |    Line Total: INR 17,500.00", fill=(10, 20, 40))
    draw2.text((50, 420), "FINANCIALS:", fill=(20, 40, 80))
    draw2.text((50, 450), "Subtotal: Rs. 41,900.00", fill=(10, 20, 40))
    draw2.text((50, 480), "GST @ 18%: Rs. 7,542.00", fill=(10, 20, 40))
    draw2.text((50, 510), "Freight / Courier: Rs. 1,200.00", fill=(10, 20, 40))
    draw2.text((50, 550), "TOTAL PAYABLE: Rs. 50,642.00", fill=(10, 60, 120))
    img2.save(img2_path)
    print(f"Created: {img2_path}")

    print("All sample files generated successfully!")

if __name__ == "__main__":
    generate_samples()

