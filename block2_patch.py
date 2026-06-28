import os, re

# --- PATCH app.py (upload_photo GPS + category) ---
app_path = 'app.py'
with open(app_path, 'r', encoding='utf-8') as f:
    code = f.read()

pattern = r"@app.route\('/jobs/<int:job_id>/upload_photo'.*?def upload_photo[\s\S]*?return redirect\(url_for\('view_job', job_id=job.id\)\)"
replacement = """@app.route('/jobs/<int:job_id>/upload_photo', methods=['POST'])
@login_required
def upload_photo(job_id):
    job = Job.query.get_or_404(job_id)
    files = request.files.getlist('photo')

    if not files or files == ['']:
        flash('No files selected.')
        return redirect(url_for('view_job', job_id=job.id))

    for file in files:
        if not file or file.filename == '':
            continue

        filename = secure_filename(file.filename)
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"{timestamp}_{filename}"
        abs_path = os.path.join(app.config['UPLOAD_FOLDER_PHOTOS'], filename)
        file.save(abs_path)

        rel_path = os.path.relpath(abs_path, STATIC_DIR).replace('\\\\', '/')

        lat = request.form.get('lat')
        lon = request.form.get('lon')
        category = request.form.get('category')
        location_label = request.form.get('location_label')
        before_after = request.form.get('before_after')

        photo = JobPhoto(
            job_id=job.id,
            user_id=current_user.id,
            filename=rel_path,
            category=category,
            location_label=location_label,
            before_after=before_after,
            latitude=float(lat) if lat else None,
            longitude=float(lon) if lon else None
        )
        db.session.add(photo)

    db.session.commit()
    flash('Photos uploaded.')
    return redirect(url_for('view_job', job_id=job.id))"""

code = re.sub(pattern, replacement, code)
with open(app_path, 'w', encoding='utf-8') as f:
    f.write(code)

# --- PATCH sign_contract.html (GPS fields) ---
sc_path = 'templates/sign_contract.html'
with open(sc_path, 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block content %}
<h2>Sign Contract for Job {{ job.job_number }} — {{ job.title }}</h2>

<div class='cc-card mb-3'>
  <p><strong>Template ID:</strong> {{ contract.template_id }}</p>
  <p><strong>Status:</strong> {{ 'Signed' if contract.signed else 'Pending' }}</p>
</div>

<form method='post' class='cc-card'>
  <div class='mb-2'>
    <label>Signer Name</label>
    <input class='form-control' type='text' name='signer_name' required>
  </div>
  <div class='mb-2'>
    <label>Signer Email</label>
    <input class='form-control' type='email' name='signer_email'>
  </div>
  <div class='mb-2'>
    <label>Latitude (optional)</label>
    <input class='form-control' type='text' name='lat'>
  </div>
  <div class='mb-2'>
    <label>Longitude (optional)</label>
    <input class='form-control' type='text' name='lon'>
  </div>
  <button class='btn btn-primary'>Sign Contract</button>
</form>
{% endblock %}""")

# --- PATCH view_job.html (map container + Leaflet) ---
vj_path = 'templates/view_job.html'
with open(vj_path, 'r', encoding='utf-8') as f:
    vj = f.read()

if 'job-map' not in vj:
    vj += """


<div class='cc-card mt-3'>
  <h3>Job Map</h3>
  <div id='job-map' style='height:300px;border-radius:0.75rem;'></div>
</div>

<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
<script src='/static/js/job_map.js'></script>
"""

with open(vj_path, 'w', encoding='utf-8') as f:
    f.write(vj)

# --- CREATE static/js/job_map.js ---
os.makedirs('static/js', exist_ok=True)
with open('static/js/job_map.js', 'w', encoding='utf-8') as f:
    f.write("""document.addEventListener('DOMContentLoaded', function () {
  var mapEl = document.getElementById('job-map');

  var map = L.map('job-map').setView([39.0, -76.7], 11);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19
  }).addTo(map);

  fetch(mapEl.getAttribute('data-url'))
    .then(r => r.json())
    .then(data => {
      var bounds = [];

      (data.photos || []).forEach(function (p) {
        var m = L.marker([p.lat, p.lon]).addTo(map);
        m.bindPopup('<strong>' + p.label + '</strong><br>' + p.filename);
        bounds.push([p.lat, p.lon]);
      });

      (data.contracts || []).forEach(function (c) {
        var m = L.marker([c.lat, c.lon]).addTo(map);
        m.bindPopup('<strong>' + c.label + '</strong><br>' + c.signer);
        bounds.push([c.lat, c.lon]);
      });

      if (bounds.length) map.fitBounds(bounds);
    })
    .catch(console.error);
});""")

print('✔ BLOCK 2 COMPLETE — GPS, categories, map, signatures updated')

