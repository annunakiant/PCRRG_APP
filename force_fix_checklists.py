import re

# ------------------------------------------------------------
# 1) FORCE PATCH view_job to include task_templates
# ------------------------------------------------------------
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Remove any previous broken injection
code = re.sub(r"task_templates\s*=\s*JobTaskTemplate[^\n]*\n", "", code)

# Insert correct block
code = code.replace(
    "tasks = job.tasks.order_by(JobTask.id).all()",
    "tasks = job.tasks.order_by(JobTask.id).all()\n    task_templates = JobTaskTemplate.query.order_by(JobTaskTemplate.name.asc()).all()"
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)


# ------------------------------------------------------------
# 2) FORCE PATCH attach_checklist route
# ------------------------------------------------------------
if "def attach_checklist" not in code:
    with open("app.py", "a", encoding="utf-8") as f:
        f.write("""

@app.route('/jobs/<int:job_id>/attach_checklist', methods=['POST'])
@login_required
def attach_checklist(job_id):
    job = Job.query.get_or_404(job_id)
    tmpl_id = int(request.form.get('template_id'))
    tmpl = JobTaskTemplate.query.get_or_404(tmpl_id)

    try:
        steps = json.loads(tmpl.description or "[]")
    except Exception:
        steps = []

    for step in steps:
        task = JobTask(
            job_id=job.id,
            template_id=tmpl.id,
            label=step
        )
        db.session.add(task)

    db.session.commit()
    flash('Checklist attached.')
    return redirect(url_for('view_job', job_id=job.id))
""")


# ------------------------------------------------------------
# 3) FORCE PATCH view_job.html dropdown
# ------------------------------------------------------------
path = "templates/view_job.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Remove ANY old dropdown block
html = re.sub(r"Choose Job Type Checklist[\s\S]*?Attach Checklist[\s\S]*?</form>", "", html)

# Insert correct block under Tasks header
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

html = html.replace("<h3>Tasks</h3>", "<h3>Tasks</h3>\n" + block)

with open(path, "w", encoding="utf-8") as f:
    f.write(html)

print("✔ FORCE PATCH APPLIED — checklist dropdown + attach now fully wired.")
