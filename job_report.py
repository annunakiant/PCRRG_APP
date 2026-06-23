from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

def generate_job_pdf(job, file_path):
    c = canvas.Canvas(file_path, pagesize=LETTER)
    width, height = LETTER
    y = height - 50

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"Job Report: {job.job_number} - {job.title}")
    y -= 30

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Client: {job.client_name or ''}")
    y -= 20
    c.drawString(50, y, f"Address: {job.address or ''}")
    y -= 20
    c.drawString(50, y, f"Service Type: {job.service_type or ''}")
    y -= 20
    c.drawString(50, y, f"Status: {job.status}")
    y -= 30

    # Photos
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Photos")
    y -= 20
    c.setFont("Helvetica", 11)
    for p in job.photos.order_by(job.photos.mapper.class_.uploaded_at.desc()).all():
        line = f"- {p.category or 'Uncategorized'} | {p.filename}"
        c.drawString(60, y, line[:100])
        y -= 15
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)

    # Packout items
    y -= 10
    if y < 80:
        c.showPage()
        y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Packout Items")
    y -= 20
    c.setFont("Helvetica", 11)
    for i in job.packout_items.order_by(job.packout_items.mapper.class_.id.desc()).all():
        line = f"- {i.name} x{i.quantity} @ {i.location or ''} ({i.condition or ''})"
        c.drawString(60, y, line[:100])
        y -= 15
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)

    # Contracts
    y -= 10
    if y < 80:
        c.showPage()
        y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Contracts")
    y -= 20
    c.setFont("Helvetica", 11)
    for ctn in job.contracts.order_by(job.contracts.mapper.class_.id.desc()).all():
        status = "Signed" if ctn.signed else "Pending"
        line = f"- {status} by {ctn.signer_name or ''} ({ctn.signer_email or ''})"
        c.drawString(60, y, line[:100])
        y -= 15
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)

    # Tasks
    y -= 10
    if y < 80:
        c.showPage()
        y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Tasks")
    y -= 20
    c.setFont("Helvetica", 11)
    for t in job.tasks.order_by(job.tasks.mapper.class_.id.desc()).all():
        status = "Done" if t.completed else "Pending"
        line = f"- {t.label} [{status}]"
        c.drawString(60, y, line[:100])
        y -= 15
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)

    c.showPage()
    c.save()
