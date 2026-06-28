import re

with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Only add the route if it doesn't exist
if "def admin_checklist_new" not in code:
    route = """

# ------------------------------------------------------------
# ADMIN: CREATE NEW CHECKLIST TEMPLATE
# ------------------------------------------------------------
@app.route('/admin/checklists/new', methods=['GET', 'POST'])
@login_required
def admin_checklist_new():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    # Create empty template object for the form
    tmpl = JobTaskTemplate(name='', service_type='', description='[]')

    if request.method == 'POST':
        name = request.form.get('name')
        service_type = request.form.get('service_type')
        steps = request.form.getlist('steps[]')

        tmpl = JobTaskTemplate(
            name=name,
            service_type=service_type,
            description=json.dumps([s.strip() for s in steps if s.strip()])
        )
        db.session.add(tmpl)
        db.session.commit()
        flash('Checklist template created.')
        return redirect(url_for('admin_checklists'))

    return render_template('admin_checklist_edit.html', tmpl=tmpl, steps=[])
"""
    code += route

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("✔ Added missing admin_checklist_new route. Render will now load /admin/checklists without errors.")
