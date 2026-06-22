# CLEAN WORKING APP.PY STARTS HERE
# (This is a placeholder. I will generate the full correct app.py for you next.)
print("TEMP APP.PY CLEANED. READY FOR FULL REPLACEMENT.")

# -------------------------------------------------------------------------
# ADMIN TASK TEMPLATES ROUTE (fixes url_for('admin_task_templates') BuildError)
# -------------------------------------------------------------------------
@app.route('/admin/task-templates')
@login_required
def admin_task_templates():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    return render_template('admin_task_templates.html')
