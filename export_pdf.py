
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os

def build_full_pdf(job, path):
    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter

    y = height - 50

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, f"Job Report — {job.job_number}")
    y -= 30

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Title: {job.title}")
    y -= 20
    c.drawString(50, y, f"Client: {job.client_name or 'N/A'}")
    y -= 20
    c.drawString(50, y, f"Address: {job.address or 'N/A'}")
    y -= 20
    c.drawString(50, y, f"Status: {job.status}")
    y -= 40

    # Photos
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Photos:")
    y -= 20

    for p in job.photos:
        try:
            img_path = os.path.join("static", p.filename)
            img = ImageReader(img_path)
            c.drawImage(img, 50, y-120, width=200, preserveAspectRatio=True)
            y -= 140
            if y < 100:
                c.showPage()
                y = height - 50
        except:
            continue

    # Tasks
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Tasks:")
    y -= 20

    for t in job.tasks:
        c.setFont("Helvetica", 12)
        status = "✓" if t.completed else "○"
        c.drawString(50, y, f"{status} {t.label}")
        y -= 18
        if y < 100:
            c.showPage()
            y = height - 50

    c.save()
