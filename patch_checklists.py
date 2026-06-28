import re

# ------------------------------------------------------------
# 1. PATCH app.py — add checklist routes
# ------------------------------------------------------------
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Add checklist admin route
if "admin_checklists" not in code:
    checklist_admin = """
@app.route('/admin/checklists', methods=['GET', 'POST'])
@login_required
def admin_checklists():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        steps_raw = request.form.get('steps') or ""
        steps = [s.strip() for s in steps_raw.splitlines() if s.strip()]

        tmpl = JobTaskTemplate(
            name=name,
            description=json.dumps(steps),
            service_type=request.form.get('service_type')
        )
        db.session.add(tmpl)
        db.session.commit()
        flash('Checklist created.')
        return redirect(url_for('admin_checklists'))

    templates = JobTaskTemplate.query.order_by(JobTaskTemplate.name).all()
    return render_template('admin_checklists.html', templates=templates)
"""

    code = code.replace(
        "@app.route('/admin/task-templates'",
        checklist_admin + "\n\n@app.route('/admin/task-templates'"
    )

# Add attach-checklist route
if "attach_checklist" not in code:
    attach_route = """
@app.route('/jobs/<int:job_id>/attach_checklist', methods=['POST'])
@login_required
def attach_checklist(job_id):
    job = Job.query.get_or_404(job_id)
    tmpl_id = int(request.form.get('template_id'))
    tmpl = JobTaskTemplate.query.get_or_404(tmpl_id)

    try:
        steps = json.loads(tmpl.description or "[]")
    except:
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
"""

    code = code.replace(
        "@app.route('/jobs/<int:job_id>/tasks/add'",
        attach_route + "\n\n@app.route('/jobs/<int:job_id>/tasks/add'"
    )

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

# ------------------------------------------------------------
# 2. PATCH view_job.html — add checklist attach UI
# ------------------------------------------------------------
path = "templates/view_job.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()

checklist_ui = """
<!-- CHECKLIST ATTACH -->
<section class="cc-card">
  <h3>Attach Checklist</h3>
  <form method="post" action="{{ url_for('attach_checklist', job_id=job.id) }}" class="mb-2">
    <div class="row g-2">
      <div class="col-md-8">
        <select class="form-select" name="template_id" required>
          <option value="">Select checklist...</option>
          {% for t in task_templates %}
            {% if t.description %}
              <option value="{{ t.id }}">{{ t.name }}</option>
            {% endif %}
          {% endfor %}
        </select>
      </div>
      <div class="col-md-4">
        <button class="btn btn-primary btn-sm w-100">Attach Checklist</button>
      </div>
    </div>
  </form>
</section>
"""

# Insert before TASKS section
html = html.replace("<!-- TASKS -->", checklist_ui + "\n\n<!-- TASKS -->")

with open(path, "w", encoding="utf-8") as f:
    f.write(html)

print("✔ Checklist admin + attach + UI added.")
