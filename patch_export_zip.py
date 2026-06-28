import re, os

# ------------------------------------------------------------
# 1) ADD ZIP EXPORT ROUTE TO app.py
# ------------------------------------------------------------
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

if "export_job_zip" not in code:
    new_route = """
@app.route('/jobs/<int:job_id>/export/zip')
@login_required
def export_job_zip(job_id):
    job = Job.query.get_or_404(job_id)
    from export_zip import build_zip_package

    export_dir = os.path.join(app.config['ARCHIVE_FOLDER'], 'exports')
    os.makedirs(export_dir, exist_ok=True)

    filename = f"job_{job.id}_package.zip"
    path = os.path.join(export_dir, filename)

    build_zip_package(job, path)

    return send_from_directory(export_dir, filename, as_attachment=True)
"""

    code = code.replace(
        "@app.route('/jobs/<int:job_id>/export/pdf')",
        "@app.route('/jobs/<int:job_id>/export/pdf')" + "\n" + new_route
    )

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

# ------------------------------------------------------------
# 2) CREATE export_zip.py — ZIP BUILDER
# ------------------------------------------------------------
zip_builder = """
import os, json, zipfile
from export_pdf import build_full_pdf

def build_zip_package(job, zip_path):
    temp_dir = os.path.dirname(zip_path)
    pdf_path = os.path.join(temp_dir, f"job_{job.id}_full_report.pdf")

    # Build PDF first
    build_full_pdf(job, pdf_path)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:

        # Add PDF
        if os.path.exists(pdf_path):
            z.write(pdf_path, arcname='job_report.pdf')

        # Metadata
        metadata = {
            'job_number': job.job_number,
            'title': job.title,
            'client_name': job.client_name,
            'address': job.address,
            'status': job.status,
            'created_at': str(job.created_at),
            'closed_at': str(job.closed_at)
        }
        z.writestr('metadata.json', json.dumps(metadata, indent=2))

        # Tasks
        tasks = [
            {
                'label': t.label,
                'completed': t.completed,
                'completed_at': str(t.completed_at),
                'template': t.template.name if t.template else None
            }
            for t in job.tasks
        ]
        z.writestr('tasks.json', json.dumps(tasks, indent=2))

        # Packout items
        packout = [
            {
                'name': i.name,
                'quantity': i.quantity,
                'location': i.location,
                'condition': i.condition,
                'notes': i.notes
            }
            for i in job.packout_items
        ]
        z.writestr('packout.json', json.dumps(packout, indent=2))

        # Photos
        for p in job.photos:
            img_path = os.path.join('static', p.filename)
            if os.path.exists(img_path):
                z.write(img_path, arcname=f"photos/{os.path.basename(img_path)}")

        # Packout photos
        for item in job.packout_items:
            for ph in item.photos:
                img_path = os.path.join('static', ph.filename)
                if os.path.exists(img_path):
                    z.write(img_path, arcname=f"packout_photos/{os.path.basename(img_path)}")

        # Contracts
        for c in job.contracts:
            if c.template and c.template.filename:
                c_path = os.path.join('static', 'uploads', 'contracts', c.template.filename)
                if os.path.exists(c_path):
                    z.write(c_path, arcname=f"contracts/{c.template.filename}")
"""

with open("export_zip.py", "w", encoding="utf-8") as f:
    f.write(zip_builder)

# ------------------------------------------------------------
# 3) PATCH view_job.html — ADD ZIP EXPORT BUTTON
# ------------------------------------------------------------
path = "templates/view_job.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()

export_button = """
  <a class="btn btn-secondary btn-sm"
     href="{{ url_for('export_job_zip', job_id=job.id) }}">
     Download Full ZIP Package
  </a>
"""

html = html.replace(
    "Download Full PDF Report",
    "Download Full PDF Report</a>\n  " + export_button
)

with open(path, "w", encoding="utf-8") as f:
    f.write(html)

print("✔ Full ZIP export engine added.")
