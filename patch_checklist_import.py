import re, os

# ------------------------------------------------------------
# 1) PATCH app.py — ADD CHECKLIST IMPORT ROUTE
# ------------------------------------------------------------
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

if "import_checklist" not in code:
    new_route = """
@app.route('/admin/checklists/import', methods=['GET', 'POST'])
@login_required
def import_checklist():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        file = request.files.get('file')
        name = request.form.get('name') or 'Imported Checklist'
        service_type = request.form.get('service_type')

        if not file or file.filename == '':
            flash('No file selected.')
            return redirect(url_for('import_checklist'))

        # Save uploaded file
        import_dir = os.path.join(app.config['ARCHIVE_FOLDER'], 'imported_docs')
        os.makedirs(import_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        abs_path = os.path.join(import_dir, filename)
        file.save(abs_path)

        # Extract steps
        steps = []
        ext = filename.lower().split('.')[-1]

        if ext == 'txt':
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as ftxt:
                steps = [line.strip() for line in ftxt if line.strip()]

        elif ext == 'docx':
            try:
                from docx import Document
                doc = Document(abs_path)
                for p in doc.paragraphs:
                    if p.text.strip():
                        steps.append(p.text.strip())
            except:
                steps = []

        elif ext == 'pdf':
            try:
                import PyPDF2
                with open(abs_path, 'rb') as fpdf:
                    reader = PyPDF2.PdfReader(fpdf)
                    for page in reader.pages:
                        text = page.extract_text() or ""
                        for line in text.splitlines():
                            if line.strip():
                                steps.append(line.strip())
            except:
                steps = []

        # Create template
        tmpl = JobTaskTemplate(
            name=name,
            description=json.dumps(steps),
            service_type=service_type
        )
        db.session.add(tmpl)
        db.session.commit()

        flash('Checklist imported successfully.')
        return redirect(url_for('admin_checklists'))

    return render_template('admin_checklist_import.html')
"""

    code = code.replace(
        "@app.route('/admin/checklists'",
        new_route + "\n\n@app.route('/admin/checklists'"
    )

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

# ------------------------------------------------------------
# 2) CREATE TEMPLATE: admin_checklist_import.html
# ------------------------------------------------------------
template = """
{% extends "base.html" %}
{% block content %}
<h2>Import Checklist</h2>

<form method="post" enctype="multipart/form-data">
  <div class="mb-2">
    <label>Checklist Name</label>
    <input class="form-control" type="text" name="name" placeholder="Checklist name">
  </div>

  <div class="mb-2">
    <label>Service Type</label>
    <input class="form-control" type="text" name="service_type" placeholder="Optional">
  </div>

  <div class="mb-2">
    <label>Upload Document (.txt, .docx, .pdf)</label>
    <input class="form-control" type="file" name="file" required>
  </div>

  <button class="btn btn-primary">Import Checklist</button>
</form>
{% endblock %}
"""

os.makedirs("templates", exist_ok=True)
with open("templates/admin_checklist_import.html", "w", encoding="utf-8") as f:
    f.write(template)

# ------------------------------------------------------------
# 3) PATCH admin_checklists.html — ADD IMPORT BUTTON
# ------------------------------------------------------------
path = "templates/admin_checklists.html"
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    if "Import Checklist" not in html:
        html = html.replace(
            "<h2>Checklists</h2>",
            "<h2>Checklists</h2>\n<a class='btn btn-sm btn-primary' href='{{ url_for(\"import_checklist\") }}'>Import Checklist</a><br><br>"
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

print("✔ Checklist Import Engine added.")
