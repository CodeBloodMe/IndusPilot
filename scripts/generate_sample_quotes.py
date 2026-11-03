import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

os.makedirs('data/sample_quotations', exist_ok=True)
styles = getSampleStyleSheet()

quotes = [
    {
        'file': 'data/sample_quotations/apex_steel_quotation_ss304.pdf',
        'supplier': 'Apex Steel & Alloys Pvt Ltd',
        'address': 'Plot 42, Peenya Industrial Area Phase II, Bengaluru - 560058',
        'quote_no': 'APX-2026-QTN-8821',
        'material': 'Stainless Steel 304 Sheet Plate (2B Finish)',
        'grade': 'AISI 304 / DIN 1.4301',
        'qty': '800',
        'unit': 'kg',
        'price': '315.00',
        'freight': '4500.00',
        'moq': '200 kg',
        'lead': '6 Days',
        'terms': '30 Days Net Credit'
    },
    {
        'file': 'data/sample_quotations/bharat_forgings_ss304.pdf',
        'supplier': 'Bharat Forgings & Metals',
        'address': 'Sector 7, MIDC Bhosari, Pune - 411026',
        'quote_no': 'BFM-EST-2026-094',
        'material': 'Stainless Steel 304 Hot Rolled Sheet',
        'grade': 'SS 304 HR Industrial Grade',
        'qty': '800',
        'unit': 'kg',
        'price': '298.00',
        'freight': '6000.00',
        'moq': '500 kg',
        'lead': '12 Days',
        'terms': '15 Days Credit'
    },
    {
        'file': 'data/sample_quotations/deccan_precision_alloys_ss304.pdf',
        'supplier': 'Deccan Precision Alloys',
        'address': 'Balanagar Industrial Estate, Hyderabad - 500037',
        'quote_no': 'DPA-IND-QUOTE-441',
        'material': 'Stainless Steel 304 Cold Rolled Plate',
        'grade': 'SS 304 CR Precision Tolerance',
        'qty': '800',
        'unit': 'kg',
        'price': '330.00',
        'freight': '3000.00',
        'moq': '100 kg',
        'lead': '4 Days',
        'terms': '45 Days Credit'
    }
]

for q in quotes:
    doc = SimpleDocTemplate(q['file'], pagesize=letter)
    story = []
    
    # Header
    story.append(Paragraph(f"<b>{q['supplier']}</b>", styles['Title']))
    story.append(Paragraph(q['address'], styles['Normal']))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>COMMERCIAL QUOTATION / TENDER ESTIMATE</b>", styles['Heading2']))
    story.append(Paragraph(f"Quotation No: {q['quote_no']} | Date: 12-Oct-2026 | Validity: 30 Days", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Table data
    subtotal_val = float(q['price']) * float(q['qty'])
    data = [
        ['Item Description', 'Grade', 'Qty', 'Unit', 'Unit Price (INR)', 'Line Total (INR)'],
        [q['material'], q['grade'], q['qty'], q['unit'], f"Rs. {q['price']}", f"Rs. {subtotal_val:,.2f}"]
    ]
    t = Table(data, colWidths=[180, 100, 45, 45, 90, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    
    # Terms
    story.append(Paragraph("<b>Commercial Terms & Conditions:</b>", styles['Heading3']))
    story.append(Paragraph(f"1. Minimum Order Quantity (MOQ): {q['moq']}", styles['Normal']))
    story.append(Paragraph(f"2. Delivery Lead Time: {q['lead']} from Purchase Order date", styles['Normal']))
    story.append(Paragraph("3. Taxes: GST 18% extra as applicable", styles['Normal']))
    story.append(Paragraph(f"4. Freight Charges: Rs. {q['freight']} extra payable at actuals", styles['Normal']))
    story.append(Paragraph(f"5. Payment Terms: {q['terms']}", styles['Normal']))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>*Note: Synthetic simulated quotation for IndusPilot Tech4Bharat demonstration.</i>", styles['Italic']))
    
    doc.build(story)
    print("Created PDF:", q['file'])

