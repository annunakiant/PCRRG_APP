import re

with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# ------------------------------------------------------------
# 1. INSERT DELETE TASK ROUTE (only if missing)
# ------------------------------------------------------------
delete_route = """
@app.route('/jobs/<int:job_id>/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_job_task(job_id, task_id):
    job = Job.query.get_or_404(job_id)
    task = JobTask.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.')
    return redirect(url_for('view_job', job_id=job.id))
"""

if "delete_job_task" not in code:
    code = code.replace(
        "@app.route('/jobs/<int:job_id>/tasks/<int:task_id>/toggle'",
        delete_route + "\n\n@app.route('/jobs/<int:job_id>/tasks/<int:task_id>/toggle'"
    )

# ------------------------------------------------------------
# 2. AUTO‑ATTACH TASKS BASED ON JOB TYPE
# Insert inside /jobs/new POST block
# ------------------------------------------------------------
auto_attach_block = """
        # AUTO‑ATTACH TASKS BASED ON JOB TYPE
        templates = JobTaskTemplate.query.filter_by(service_type=job.service_type).all()
        for tmpl in templates:
            task = JobTask(
                job_id=job.id,
                template_id=tmpl.id,
                label=tmpl.name
            )
            db.session.add(task)
        db.session.commit()
"""

pattern_new_job = r"db\.session\.commit\(\)\s*[\r\n]+\s*flash\('Job created\.'\)"
replacement_new_job = "db.session.commit()\n" + auto_attach_block + "\n        flash('Job created.')"

code = re.sub(pattern_new_job, replacement_new_job, code)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("✔ Delete task route added")
print("✔ Auto‑attach tasks by job type added")
print("✔ Now add delete button to view_job.html manually")
