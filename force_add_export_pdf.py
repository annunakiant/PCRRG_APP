with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

route = """
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

if "def export_job_pdf" not in code:
    code = code.replace(
        "@app.route('/jobs/<int:job_id>/report.pdf')",
        route + "\n\n@app.route('/jobs/<int:job_id>/report.pdf')"
    )

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("✔ Forced export_job_pdf route into app.py")
