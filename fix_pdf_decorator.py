import re

with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Remove the stray decorator line
code = code.replace(
    "@app.route('/jobs/<int:job_id>/export/pdf')\n\n",
    ""
)

# Insert the correct decorator above the function
code = code.replace(
    "@login_required\ndef export_job_pdf",
    "@app.route('/jobs/<int:job_id>/export/pdf')\n@login_required\ndef export_job_pdf"
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("✔ Fixed export_job_pdf decorator placement.")
