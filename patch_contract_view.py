import re

# 1) PATCH app.py — add contract view route
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

if "view_contract_doc" not in code:
    route_block = """
@app.route('/contracts/<int:contract_id>/view')
@login_required
def view_contract_doc(contract_id):
    contract = JobContract.query.get_or_404(contract_id)
    tmpl = contract.template
    if not tmpl or not tmpl.filename:
        flash('No contract file available.')
        return redirect(url_for('view_job', job_id=contract.job_id))
    return send_from_directory(CONTRACTS_FOLDER, tmpl.filename, as_attachment=False)
"""

    code = code.replace(
        "class JobContract(db.Model):",
        "class JobContract(db.Model):" + "\n"  # keep model untouched
    )
    # Append route near other contract routes
    insert_point = "@app.route('/contracts"
    if insert_point in code:
        code = code.replace(insert_point, route_block + "\n\n" + insert_point)
    else:
        code += "\n\n" + route_block

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

# 2) PATCH templates/view_job.html — add View button
path = "templates/view_job.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()

old_li = """
    <li class="mb-1">
      Template #{{ c.template_id }} — {{ 'Signed' if c.signed else 'Pending' }}
      {% if not c.signed %}
      <a class="btn btn-sm btn-success"
         href="{{ url_for('sign_contract', job_id=job.id, contract_id=c.id) }}">
        Sign
      </a>
      {% endif %}
    </li>
"""

new_li = """
    <li class="mb-1">
      Template #{{ c.template_id }} — {{ 'Signed' if c.signed else 'Pending' }}

      <a class="btn btn-sm btn-outline-primary"
         href="{{ url_for('view_contract_doc', contract_id=c.id) }}">
        View
      </a>

      {% if not c.signed %}
      <a class="btn btn-sm btn-success"
         href="{{ url_for('sign_contract', job_id=job.id, contract_id=c.id) }}">
        Sign
      </a>
      {% endif %}
    </li>
"""

html_new = html.replace(old_li, new_li)

with open(path, "w", encoding="utf-8") as f:
    f.write(html_new)

print("✔ Contract view route added")
print("✔ View button added to job contracts list")
