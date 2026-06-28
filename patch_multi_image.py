import re

# ------------------------------------------------------------
# 1) PATCH app.py — update upload_photo route to handle multiple files
# ------------------------------------------------------------
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

pattern = r"def upload_photo\(job_id\):[\s\S]*?return redirect\(url_for\('view_job', job_id=job.id\)\)"
replacement = """
def upload_photo(job_id):
    job = Job.query.get_or_404(job_id)
    files = request.files.getlist('photo')

    if not files or files == ['']:
        flash('No files selected.')
        return redirect(url_for('view_job', job_id=job.id))

    for file in files:
        if not file or file.filename == '':
            continue

        filename = secure_filename(file.filename)
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"{timestamp}_{filename}"
        abs_path = os.path.join(app.config['UPLOAD_FOLDER_PHOTOS'], filename)
        file.save(abs_path)

        rel_path = os.path.relpath(abs_path, STATIC_DIR).replace('\\\\', '/')

        photo = JobPhoto(
            job_id=job.id,
            user_id=current_user.id,
            filename=rel_path,
            category=None,
            location_label=request.form.get('location_label'),
            before_after=request.form.get('before_after')
        )
        db.session.add(photo)

    db.session.commit()
    flash('Photos uploaded.')
    return redirect(url_for('view_job', job_id=job.id))
"""

code = re.sub(pattern, replacement, code)

# ------------------------------------------------------------
# 2) PATCH view_job.html — allow multiple photo selection
# ------------------------------------------------------------
path = "templates/view_job.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace(
    '<input class="form-control" type="file" name="photo" accept="image/*" capture="environment" required>',
    '<input class="form-control" type="file" name="photo" accept="image/*" capture="environment" multiple required>'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(html)

print("✔ Multi-image capture enabled for job photos.")
