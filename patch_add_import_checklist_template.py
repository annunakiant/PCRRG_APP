import os

path = "templates/admin_checklist_import.html"

content = """
{% extends 'base.html' %}
{% block content %}
<h2>Import Checklist Template</h2>

<form method="post" enctype="multipart/form-data">
  <div class="mb-3">
    <label class="form-label">Upload Checklist File</label>
    <input type="file" name="file" class="form-control" required>
    <small class="text-muted">Accepted formats: TXT, PDF, DOCX</small>
  </div>

  <button class="btn btn-primary btn-sm">Import Checklist</button>
</form>

{% endblock %}
"""

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("✔ Created admin_checklist_import.html template.")
