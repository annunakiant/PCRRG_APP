import os
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from collections import defaultdict
from app import STATIC_DIR

def build_full_pdf(job, output_path):
    pdf = canvas.Canvas(output_path, pagesize=landscape(letter))
    page_w, page_h = landscape(letter)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(50, page_h - 50, f"Job Report: {job.job_number}")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, page_h - 70, f"Title: {job.title} | Client: {job.client_name}")
    
    categories = defaultdict(list)
    for p in job.photos.all():
        categories[p.category or "General"].append(p)
    
    per_row, per_page = 4, 8
    thumb_w, thumb_h = 160, 160
    start_x, start_y = 50, page_h - 150
    
    for cat, cat_photos in categories.items():
        pdf.showPage()
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(start_x, page_h - 40, f"Category: {cat}")
        idx = 0
        while idx < len(cat_photos):
            chunk = cat_photos[idx:idx+per_page]
            for i, p in enumerate(chunk):
                x = start_x + (i % per_row) * (thumb_w + 20)
                y = start_y - (i // per_row) * (thumb_h + 60) - thumb_h
                try:
                    img_path = os.path.join(STATIC_DIR, p.filename.lstrip("/"))
                    pdf.drawImage(img_path, x, y, width=thumb_w, height=thumb_h, preserveAspectRatio=True)
                except: pass
            pdf.showPage()
            idx += per_page
    pdf.save()
