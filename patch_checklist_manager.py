import os, json, re

# ------------------------------------------------------------
# 1) CREATE admin_checklists.html
# ------------------------------------------------------------
os.makedirs("templates", exist_ok=True)
with open("templates/admin_checklists.html", "w", encoding="utf-8") as f:
    f.write("""
{% extends 'base.html' %}
{% block content %}
<h2>Checklist Templates</h2>

<a class="btn btn-sm btn-primary mb-3" href="{{ url_for('admin_checklist_new') }}">Create Checklist Template</a>
<a class="btn btn-sm btn-outline-primary mb-3" href="{{ url_for('import_checklist') }}">Import Checklist File</a>

<table class="table table-sm">
  <thead><tr><th>Name</th><th>Service Type</th><th>Steps</th><th>Actions</th></tr></thead>
  <tbody>
    {% for t in templates %}
    <tr>
      <td>{{ t.name }}</td>
      <td>{{ t.service_type or 'General' }}</td>
      <td>{{ (t.description | safe | length) if t.description else 0 }}</td>
      <td>
        <a class="btn btn-sm btn-outline-primary" href="{{ url_for('admin_checklist_edit', checklist_id=t.id) }}">Edit</a>
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
""")

# ------------------------------------------------------------
# 2) CREATE admin_checklist_edit.html
# ------------------------------------------------------------
with open("templates/admin_checklist_edit.html", "w", encoding="utf-8") as f:
    f.write("""
{% extends 'base.html' %}
{% block content %}
<h2>Edit Checklist Template</h2>

<form method="post">
  <div class="mb-2">
    <label>Name</label>
    <input name="name" class="form-control" value="{{ tmpl.name }}" required>
  </div>

  <div class="mb-2">
    <label>Service Type</label>
    <input name="service_type" class="form-control" value="{{ tmpl.service_type }}">
  </div>

  <div class="mb-2">
    <label>Steps</label>
    <ul id="steps-list" class="list-group">
      {% for s in steps %}
      <li class="list-group-item d-flex align-items-center" draggable="true">
        <span class="me-2" style="cursor:grab;">⋮⋮</span>
        <input name="steps[]" class="form-control" value="{{ s }}">
      </li>
      {% endfor %}
    </ul>
    <button type="button" class="btn btn-sm btn-outline-secondary mt-2" id="add-step-btn">Add Step</button>
  </div>

  <button class="btn btn-primary btn-sm mt-3">Save Checklist</button>
</form>

<script>
document.getElementById('add-step-btn').addEventListener('click', function() {
  const list = document.getElementById('steps-list');
  const li = document.createElement('li');
  li.className = 'list-group-item d-flex align-items-center';
  li.setAttribute('draggable', 'true');
  li.innerHTML = '<span class="me-2" style="cursor:grab;">⋮⋮</span><input name="steps[]" class="form-control" placeholder="New step">';
  list.appendChild(li);
});

let dragged;
document.addEventListener('dragstart', function(e) {
  dragged = e.target.closest('li');
});
document.addEventListener('dragover', function(e) {
  e.preventDefault();
});
document.addEventListener('drop', function(e) {
  const target = e.target.closest('li');
  if (dragged && target && dragged !== target) {
    const list = document.getElementById('steps-list');
    const items = Array.from(list.children);
    const draggedIndex = items.indexOf(dragged);
    const targetIndex = items.indexOf(target);
    if (draggedIndex < targetIndex) {
      list.insertBefore(dragged, target.nextSibling);
    } else {
      list.insertBefore(dragged, target);
    }
  }
});
</script>
{% endblock %}
""")

# ------------------------------------------------------------
# 3) PATCH app.py — add admin routes
# ------------------------------------------------------------
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

if "def admin_checklists" not in code:
    code += """

@app.route('/admin/checklists')
@login_required
def admin_checklists():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    templates = JobTaskTemplate.query.order_by(JobTaskTemplate.name.asc()).all()
    return render_template('admin_checklists.html', templates=templates)

@app.route('/admin/checklists/new', methods=['GET', 'POST'])
@login_required
def admin_checklist_new():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name')
        service_type = request.form.get('service_type')
        steps = request.form.getlist('steps[]')
        tmpl = JobTaskTemplate(
            name=name,
            service_type=service_type,
            description=json.dumps([s for s in steps if s.strip()])
        )
        db.session.add(tmpl)
        db.session.commit()
        flash('Checklist created.')
        return redirect(url_for('admin_checklists'))
    return render_template('admin_checklist_edit.html', tmpl=JobTaskTemplate(name='', service_type='', description='[]'), steps=[])

@app.route('/admin/checklists/<int:checklist_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_checklist_edit(checklist_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    tmpl = JobTaskTemplate.query.get_or_404(checklist_id)
    steps = json.loads(tmpl.description or "[]")
    if request.method == 'POST':
        tmpl.name = request.form.get('name')
        tmpl.service_type = request.form.get('service_type')
        tmpl.description = json.dumps(request.form.getlist('steps[]'))
        db.session.commit()
        flash('Checklist updated.')
        return redirect(url_for('admin_checklists'))
    return render_template('admin_checklist_edit.html', tmpl=tmpl, steps=steps)
"""

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("✔ Checklist Template Manager installed.")
