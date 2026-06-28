import re

# ------------------------------------------------------------
# 1) PATCH view_job route to pass task_templates
# ------------------------------------------------------------
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

if "task_templates = JobTaskTemplate" not in code:
    code = code.replace(
        "return render_template(",
        "task_templates = JobTaskTemplate.query.order_by(JobTaskTemplate.name.asc()).all()\n    return render_template("
    )

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

# ------------------------------------------------------------
# 2) ADD attach_checklist_to_job route
# ------------------------------------------------------------
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

if "def attach_checklist_to_job" not in code:
    route = """
@app.route('/jobs/<int:job_id>/attach-checklist', methods=['POST'])
@login_required
def attach_checklist_to_job(job_id):
    job = Job.query.get_or_404(job_id)
    checklist_id = request.form.get('checklist_id')
    tmpl = JobTaskTemplate.query.get_or_404(checklist_id)

    import json
    steps = []
    try:
        steps = json.loads(tmpl.description or "[]")
    except:
        steps = []

    for s in steps:
        if not s.strip():
            continue
        task = JobTask(
            job_id=job.id,
            description=s.strip(),
            completed=False
        )
        db.session.add(task)

    db.session.commit()
    flash('Checklist attached to job.')
    return redirect(url_for('view_job', job_id=job.id))
"""
    code += "\n" + route

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

# ------------------------------------------------------------
# 3) PATCH view_job.html to add dropdown
# ------------------------------------------------------------
path = "templates/view_job.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()

if "Choose Job Type Checklist" not in html:
    block = """
<div class="mb-3">
  <label><strong>Choose Job Type Checklist</strong></label>
  <form method="post" action="{{ url_for('attach_checklist_to_job', job_id=job.id) }}" class="d-flex gap-2">
    <select name="checklist_id" class="form-select form-select-sm" required>
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

print("✔ Checklist attach system installed.")
