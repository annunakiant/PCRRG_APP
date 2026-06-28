import re

with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Remove any previous broken injection
code = re.sub(r"task_templates\s*=\s*JobTaskTemplate[^\n]*\n", "", code)

# Patch view_job() cleanly
pattern = r"def view_job\(job_id\):[\s\S]*?return render_template\("
replacement = (
    "def view_job(job_id):\n"
    "    job = Job.query.get_or_404(job_id)\n"
    "    photos = job.photos.all()\n"
    "    packout_items = job.packout_items.all()\n"
    "    contracts = job.contracts.all()\n"
    "    templates = ContractTemplate.query.all()\n"
    "    tabs = CustomTab.query.order_by(CustomTab.order).all()\n"
    "    tasks = job.tasks.order_by(JobTask.id).all()\n"
    "\n"
    "    # ⭐ FIX: load checklist templates\n"
    "    task_templates = JobTaskTemplate.query.order_by(JobTaskTemplate.name.asc()).all()\n"
    "\n"
    "    values_map = {v.field_id: v.value for v in job.custom_values}\n"
    "\n"
    "    return render_template(\n"
)

code = re.sub(pattern, replacement, code)

# Add task_templates to render() call
code = code.replace(
    "tasks=tasks",
    "tasks=tasks,\n        task_templates=task_templates"
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print(\"✔ view_job() patched — task_templates now passed to template.\")
