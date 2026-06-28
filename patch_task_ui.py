import re

path = "templates/view_job.html"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Replace the existing <ul class="list-unstyled"> ... </ul> in the TASKS section
old_block = r"""
  <ul class="list-unstyled">
    {% for t in tasks %}
    <li class="mb-1">
      {{ t.label }} — {{ 'Done' if t.completed else 'Pending' }}
      <form method="post"
            action="{{ url_for('toggle_job_task', job_id=job.id, task_id=t.id) }}"
            style="display:inline;">
        <button class="btn btn-sm btn-outline-secondary">Toggle</button>
      </form>
    </li>
    {% endfor %}
  </ul>
"""

new_block = r"""
  <ul class="list-unstyled">
    {% for t in tasks %}
    <li class="mb-1">
      {% if t.template %}
        <strong>{{ t.template.name }}</strong> — 
      {% endif %}
      {{ t.label }} — {{ 'Done' if t.completed else 'Pending' }}

      <form method="post"
            action="{{ url_for('toggle_job_task', job_id=job.id, task_id=t.id) }}"
            style="display:inline;">
        <button class="btn btn-sm btn-outline-secondary">
          Toggle
        </button>
      </form>

      <form method="post"
            action="{{ url_for('delete_job_task', job_id=job.id, task_id=t.id) }}"
            style="display:inline;margin-left:6px;">
        <button class="btn btn-sm btn-outline-danger">
          Delete
        </button>
      </form>
    </li>
    {% endfor %}
  </ul>
"""

html_new = html.replace(old_block, new_block)

with open(path, "w", encoding="utf-8") as f:
    f.write(html_new)

print("✔ Task UI updated: template label + delete button added.")
