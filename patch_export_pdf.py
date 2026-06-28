import re, os

# ------------------------------------------------------------
# 1) ADD NEW PDF EXPORT ROUTE TO app.py
# ------------------------------------------------------------
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

if "export_job_pdf" not in code:
    new_route = """
@app.route('/jobs/<int:job_id>/export/pdf')
@login_required
def export_job_pdf(job_id):
    job = Job.query.get_or_404(job_id)
    from export_pdf import build_full_pdf

    export_dir = os.path.join(app.config['ARCHIVE_FOLDER'], 'exports')
    os.makedirs(export_dir, exist_ok=True)

    filename = f"job_{job.id}_full_report.pdf"
    path = os.path.join(export_dir, filename)

    build_full_pdf(job, path)

    return send_from_directory(export_dir, filename, as_attachment=True)
"""

    # Insert route near existing job_report_pdf
    code = code.replace(
        "@app.route('/jobs/<int:job_id>/report.pdf')",
        new_route + "\n\n@app.route('/jobs/<int:job_id>/report.pdf')"
    )

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

# ------------------------------------------------------------
# 2) CREATE export_pdf.py (PDF BUILDER)
# ------------------------------------------------------------
pdf_builder = """
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
"""

with open("export_pdf.py", "w", encoding="utf-8") as f:
    f.write(pdf_builder)

# ------------------------------------------------------------
# 3) PATCH view_job.html — ADD EXPORT BUTTON
# ------------------------------------------------------------
path = "templates/view_job.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()

export_button = """
<section class="cc-card">
  <h3>Export</h3>
  <a class="btn btn-primary btn-sm"
     href="{{ url_for('export_job_pdf', job_id=job.id) }}">
     Download Full PDF Report
  </a>
</section>
"""

html = html.replace("<!-- SHARE -->", export_button + "\n\n<!-- SHARE -->")

with open(path, "w", encoding="utf-8") as f:
    f.write(html)

print("✔ Full PDF export engine added.")
