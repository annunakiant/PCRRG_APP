import re

# 1) Make view_job pass task_templates to the template
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

if "task_templates=JobTaskTemplate" not in code:
    code = code.replace(
        "tasks = job.tasks.order_by(JobTask.id).all()\n\n    values_map = {v.field_id: v.value for v in job.custom_values}\n\n    return render_template(",
        "tasks = job.tasks.order_by(JobTask.id).all()\n"
        "    task_templates = JobTaskTemplate.query.order_by(JobTaskTemplate.name.asc()).all()\n\n"
        "    values_map = {v.field_id: v.value for v in job.custom_values}\n\n"
        "    return render_template("
    )

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

# 2) Fix the checklist attach block in view_job.html
path = "templates/view_job.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Remove any old "Choose Job Type Checklist" block
html = re.sub(r"<label><strong>Choose Job Type Checklist[\s\S]*?</form>\s*</div>", "", html)

# Insert a working block under the Tasks header
block = """
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

html = html.replace("Tasks", "Tasks\n" + block)

with open(path, "w", encoding="utf-8") as f:
    f.write(html)

print("✔ Checklist dropdown wired: task_templates passed + attach_checklist form fixed.")
