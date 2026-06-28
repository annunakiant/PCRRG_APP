import re

path = "templates/admin.html"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Only add link if missing
if "admin_checklists" not in html:
    html = html.replace(
        '<a class="btn btn-sm btn-outline-primary" href="{{ url_for(\'admin_task_templates\') }}">Task Templates</a>',
        '<a class="btn btn-sm btn-outline-primary" href="{{ url_for(\'admin_task_templates\') }}">Task Templates</a>\n'
        '<a class="btn btn-sm btn-outline-primary" href="{{ url_for(\'admin_checklists\') }}">Checklist Templates</a>'
    )

with open(path, "w", encoding="utf-8") as f:
    f.write(html)

print("✔ Added Checklist Templates link to Admin Panel.")
