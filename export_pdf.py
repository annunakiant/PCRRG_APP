import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def get_image(path, max_width, max_height):
    try:
        from PIL import Image as PILImage
        img = PILImage.open(path)
        w, h = img.size
        ratio = min(max_width/w, max_height/h)
        return RLImage(path, width=w*ratio, height=h*ratio)
    except Exception as e:
        return Paragraph(f"<i>[Image Unavailable]</i>", getSampleStyleSheet()['Normal'])

def build_full_pdf(job, output_path):
    from app import ThemeSettings, BASE_DIR, STATIC_DIR, app
    
    with app.app_context():
        theme = ThemeSettings.query.first()
        primary_hex = theme.primary_color if theme and theme.primary_color else "#1E88E5"
        logo_url = theme.logo_url if theme and theme.logo_url else None
        
    primary_color = colors.HexColor(primary_hex)

    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('TitleCustom', parent=styles['Heading1'], alignment=1, fontSize=20, spaceAfter=12, textColor=primary_color)
    h2 = ParagraphStyle('H2Custom', parent=styles['Heading2'], spaceBefore=15, spaceAfter=10, textColor=colors.white, backColor=primary_color, borderPadding=5)
    normal = styles['Normal']

    # --- 1. COVER PAGE ---
    if logo_url:
        logo_path = os.path.join(BASE_DIR, logo_url.lstrip('/'))
        if os.path.exists(logo_path):
            elements.append(get_image(logo_path, 2.5*inch, 1.2*inch))
            elements.append(Spacer(1, 0.2*inch))

    elements.append(Paragraph("Professional Service & Claim Report", title_style))
    elements.append(Spacer(1, 0.5 * inch))

    info_data = [
        [Paragraph("<b>Job Number:</b>", normal), job.job_number or "N/A"],
        [Paragraph("<b>Claim / Title:</b>", normal), job.title or "N/A"],
        [Paragraph("<b>Client Name:</b>", normal), job.client_name or "N/A"],
        [Paragraph("<b>Property Address:</b>", normal), job.address or "N/A"],
        [Paragraph("<b>Service Type:</b>", normal), job.service_type or "N/A"],
        [Paragraph("<b>Current Status:</b>", normal), job.status.upper() if job.status else "N/A"],
        [Paragraph("<b>Report Generated:</b>", normal), datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')]
    ]
    info_table = Table(info_data, colWidths=[2.0*inch, 4.0*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("This document contains verified field service reporting, photographic evidence logs, and authorized agreements required for compliance and adjustment purposes.", normal))
    elements.append(PageBreak())

    # --- 2. TASKS & CHECKLISTS ---
    tasks = job.tasks.all()
    if tasks:
        elements.append(Paragraph("Task & Service Checklist", h2))
        task_data = [["Task Description", "Status", "Completed By", "Date"]]
        for t in tasks:
            status = "Completed" if t.completed else "Pending"
            user = t.completed_by.name if t.completed and getattr(t, 'completed_by', None) else "N/A"
            date_str = t.completed_at.strftime('%Y-%m-%d %H:%M') if t.completed_at else "-"
            task_data.append([Paragraph(t.label, normal), status, user, date_str])
        
        t_table = Table(task_data, colWidths=[3.0*inch, 1.0*inch, 1.5*inch, 1.5*inch])
        t_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#333333")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('PADDING', (0,0), (-1,-1), 6)
        ]))
        elements.append(t_table)
        elements.append(Spacer(1, 0.3*inch))

    # --- 3. WORK AUTHORIZATIONS & SIGNATURES ---
    elements.append(Paragraph("Work Authorizations & Signatures", h2))
    contracts = job.contracts.all()
    if not contracts:
        elements.append(Paragraph("No contracts associated with this job.", normal))
    else:
        for c in contracts:
            elements.append(Paragraph(f"<b>Document ID:</b> {c.template_id} - {'SIGNED' if c.signed else 'PENDING'}", normal))
            if c.signed:
                elements.append(Paragraph(f"<b>Authorized By:</b> {c.signer_name} ({c.signer_email}) on {c.signed_at.strftime('%Y-%m-%d %H:%M') if c.signed_at else 'Unknown'}", normal))
                if c.latitude and c.longitude:
                    elements.append(Paragraph(f"<b>Signing Location (GPS):</b> {c.latitude}, {c.longitude}", normal))
                if getattr(c, 'signature_file', None):
                    sig_path = os.path.join(STATIC_DIR, 'uploads', 'contracts', c.signature_file)
                    if os.path.exists(sig_path):
                        elements.append(Spacer(1, 0.1*inch))
                        elements.append(get_image(sig_path, 2.5*inch, 1.0*inch))
            elements.append(Spacer(1, 0.2*inch))
    elements.append(PageBreak())

    # --- 4. PACKOUT INVENTORY ---
    elements.append(Paragraph("Contents & Packout Manifest", h2))
    items = job.packout_items.all()
    if items:
        p_data = [["Item", "Qty", "Location", "Condition", "Notes"]]
        for i in items:
            p_data.append([
                Paragraph(i.name, normal), str(i.quantity), Paragraph(i.location or "", normal),
                Paragraph(i.condition or "", normal), Paragraph(i.notes or "", normal)
            ])
        p_table = Table(p_data, colWidths=[2.0*inch, 0.5*inch, 1.5*inch, 1.0*inch, 2.0*inch])
        p_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#333333")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP')
        ]))
        elements.append(p_table)
    else:
        elements.append(Paragraph("No packout items recorded.", normal))
    elements.append(PageBreak())

    # --- 5. PHOTO EVIDENCE LOG ---
    elements.append(Paragraph("Photographic Evidence Log", h2))
    photos = job.photos.order_by(job.photos.property('uploaded_at')).all()
    
    photo_grid_data = []
    row_images, row_text = [], []
    
    for idx, p in enumerate(photos):
        clean_filename = p.filename.replace("\\\\", "/").replace("\\", "/").lstrip("/")
        img_path = os.path.join(STATIC_DIR, clean_filename)
        img_obj = get_image(img_path, 3.2*inch, 3.0*inch)
        
        meta_text = f"<b>Date:</b> {p.uploaded_at.strftime('%Y-%m-%d %H:%M') if p.uploaded_at else 'N/A'}<br/>"
        meta_text += f"<b>Category:</b> {p.category or 'N/A'}<br/>"
        if p.latitude and p.longitude:
            meta_text += f"<b>GPS:</b> {p.latitude}, {p.longitude}"
            
        row_images.append(img_obj)
        row_text.append(Paragraph(meta_text, normal))
        
        if len(row_images) == 2 or idx == len(photos) - 1:
            while len(row_images) < 2:
                row_images.append(Paragraph("", normal))
                row_text.append(Paragraph("", normal))
            photo_grid_data.append(row_images)
            photo_grid_data.append(row_text)
            row_images, row_text = [], []

    if photo_grid_data:
        grid_table = Table(photo_grid_data, colWidths=[3.5*inch, 3.5*inch])
        grid_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ]))
        elements.append(grid_table)
    else:
        elements.append(Paragraph("No field photos recorded.", normal))

    doc.build(elements)
