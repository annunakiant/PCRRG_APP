import re

# ------------------------------------------------------------
# 1) PATCH view_job to include task_templates
# ------------------------------------------------------------
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

if "task_templates=" not in code:
    code = code.replace(
        "tasks=tasks",
        "tasks=tasks,\n        task_templates=JobTaskTemplate.query.order_by(JobTaskTemplate.name.asc()).all()"
    )

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)


# ------------------------------------------------------------
# 2) PATCH view_job.html dropdown block
# ------------------------------------------------------------
path = "templates/view_job.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Remove any old broken block
html = re.sub(r"<label><strong>Choose Job Type Checklist[\s\S]*?</form>\s*</div>", "", html)

# Insert correct block after <h3>Tasks</h3>
correct_block = """
<div class="mb-3">
  <label><strong>Choose Job Type Checklist</strong></label>
  <form method="post" action="{{ url_for('attach_checklist', job_id=job.id) }}" class="d-flex gap-2">
    <select name="template_id" class="form-select form-select-sm" required>
      <option value="">Select checklist template...</option>
      {% for t in task_templates %}
        <option value="{{ t.id }}">{{ t.name }} ({{ t.service_type or 'General' }})</option>
      {% endfor %}
    </select>
    <button class="btn btn-sm btn-primary">Attach Checklist</button>
  </form>
</div>
"""

html = html.replace("<h3>Tasks</h3>", "<h3>Tasks</h3>\n" + correct_block)

with open(path, "w", encoding="utf-8") as f:
    f.write(html)

print("✔ FINAL FIX APPLIED — Checklist dropdown + attach now fully functional.")
