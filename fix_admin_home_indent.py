import re

with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace the entire admin_home() function with a clean, correct version
fixed_block = """
@app.route('/admin')
@login_required
def admin_home():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    jobs = Job.query.order_by(Job.created_at.desc()).limit(10).all()
    inventory_items = InventoryItem.query.order_by(InventoryItem.name).limit(10).all()
    tabs = CustomTab.query.order_by(CustomTab.order).all()
    theme = ThemeSettings.query.first()
    task_templates = JobTaskTemplate.query.order_by(JobTaskTemplate.name).all()
    active_sessions = EmployeeSession.query.filter(EmployeeSession.clock_out_at.is_(None)).all()

    return render_template(
        'admin.html',
        jobs=jobs,
        inventory_items=inventory_items,
        tabs=tabs,
        theme=theme,
        task_templates=task_templates,
        active_sessions=active_sessions
    )
"""

# Replace old function
code = re.sub(
    r"@app\.route\('/admin'[\s\S]*?return render_template\([\s\S]*?\)",
    fixed_block,
    code
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("✔ admin_home indentation fixed. App will now deploy.")
