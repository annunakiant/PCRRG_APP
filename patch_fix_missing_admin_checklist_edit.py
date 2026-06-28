import re

with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Only add the route if missing
if "def admin_checklist_edit" not in code:
    route = """

# ------------------------------------------------------------
# ADMIN: EDIT CHECKLIST TEMPLATE
# ------------------------------------------------------------
@app.route('/admin/checklists/<int:checklist_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_checklist_edit(checklist_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    tmpl = JobTaskTemplate.query.get_or_404(checklist_id)

    import json
    try:
        steps = json.loads(tmpl.description or "[]")
    except:
        steps = []

    if request.method == 'POST':
        tmpl.name = request.form.get('name')
        tmpl.service_type = request.form.get('service_type')
        new_steps = request.form.getlist('steps[]')
        tmpl.description = json.dumps([s.strip() for s in new_steps if s.strip()])
        db.session.commit()
        flash('Checklist updated.')
        return redirect(url_for('admin_checklists'))

    return render_template('admin_checklist_edit.html', tmpl=tmpl, steps=steps)
"""
    code += route

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("✔ Added missing admin_checklist_edit route. /admin/checklists will now load without errors.")
