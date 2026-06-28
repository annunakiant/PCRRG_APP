import re

path = "templates/job_folder.html"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# We insert the button right under the "Checklists" card title
pattern = r"(<div class=\"card-title\">Checklists<\/div>)"

replacement = r"""\1
{% if is_admin %}
  <a class="btn btn-sm btn-primary mt-1" href="{{ url_for('import_checklist') }}">
    Import Checklist
  </a>
{% endif %}
"""

new_html = re.sub(pattern, replacement, html)

with open(path, "w", encoding="utf-8") as f:
    f.write(new_html)

print("✔ Added Import Checklist button to job_folder.html")
