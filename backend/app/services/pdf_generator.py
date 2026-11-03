import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_customer_quotation_pdf(
    quote_number: str,
    customer_name: str,
    customer_company: str,
    product_name: str,
    product_code: str,
    quantity: float,
    unit_selling_price: float,
    unit_cost: float,
    subtotal: float,
    tax_amount: float,
    total_amount: float,
    margin_pct: float,
    payment_terms: str,
    delivery_weeks: int,
    output_dir: str
) -> str:
    """
    Generates an industrial commercial PDF quotation for customer delivery.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"Customer_Quote_{quote_number.replace('/', '_')}.pdf"
    file_path = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(file_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#64748B')
    )
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=6
    )

    story = []

    # Header block
    story.append(Paragraph("APEX PRECISION FABRICATION WORKS", title_style))
    story.append(Paragraph("Plot 42, Peenya Industrial Area Phase II, Bengaluru - 560058 | GSTIN: 29AAACA1122K1Z9", subtitle_style))
    story.append(Paragraph("Email: sales@apexprecisionworks.com | Phone: +91 80 2839 4400", subtitle_style))
    story.append(Spacer(1, 12))

    # Meta banner
    meta_data = [
        [
            Paragraph(f"<b>CUSTOMER DETAILS:</b><br/>{customer_name}<br/>{customer_company}<br/>Terms: {payment_terms}", styles['Normal']),
            Paragraph(f"<b>COMMERCIAL QUOTATION</b><br/>Quote No: <b>{quote_number}</b><br/>Date: {datetime.now().strftime('%d-%b-%Y')}<br/>Delivery: {delivery_weeks} Weeks", styles['Normal'])
        ]
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # Line Item Table
    story.append(Paragraph("Scope of Supply & Specifications", section_title))
    table_data = [
        ['Item Code', 'Product Description', 'Batch Qty', 'Unit Price (INR)', 'Total Amount (INR)'],
        [
            product_code,
            f"{product_name}\nGrade: SS304 Industrial Bracket, Precision CNC Formed, Laser Cut",
            f"{quantity:,.0f} Nos",
            f"Rs. {unit_selling_price:,.2f}",
            f"Rs. {subtotal:,.2f}"
        ]
    ]
    item_table = Table(table_data, colWidths=[80, 220, 60, 90, 90])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (1,1), (1,1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 10))

    # Totals block
    totals_data = [
        ['Subtotal (Ex-Works):', f"Rs. {subtotal:,.2f}"],
        ['GST (18% as applicable):', f"Rs. {tax_amount:,.2f}"],
        ['Total Order Value (Gross):', f"Rs. {total_amount:,.2f}"]
    ]
    tot_table = Table(totals_data, colWidths=[380, 160])
    tot_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,-1), (-1,-1), colors.HexColor('#0F172A')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(tot_table)
    story.append(Spacer(1, 14))

    # Profitability & Internal Cost Safeguard (Watermarked / Audited)
    profit_note = (
        f"Internal Engineering Audit: Unit Cost Rs. {unit_cost:.2f} | "
        f"Unit Price Rs. {unit_selling_price:.2f} | Projected Gross Margin: {margin_pct:.1f}% "
        f"(Audited by IndusPilot Cost Intelligence Engine)"
    )
    story.append(Paragraph(f"<i>{profit_note}</i>", styles['Italic']))
    story.append(Spacer(1, 10))

    # Terms & Conditions
    story.append(Paragraph("Commercial Terms & Conditions", section_title))
    terms = [
        f"1. Payment Terms: {payment_terms}.",
        f"2. Delivery Schedule: Dispatched within {delivery_weeks} weeks from receipt of formal Purchase Order and advance payment.",
        "3. Price Validity: This quotation remains valid for 15 calendar days from the date of issuance.",
        "4. Quality Warranty: All components undergo 100% dimensional inspection and material test certificates (MTC) are provided upon dispatch.",
        "5. Force Majeure: Standard industrial force majeure clauses apply to supply disruptions beyond manufacturer control."
    ]
    for term in terms:
        story.append(Paragraph(term, styles['Normal']))

    doc.build(story)
    return file_path

