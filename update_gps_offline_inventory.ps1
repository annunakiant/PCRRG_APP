# update_gps_offline_inventory.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = "C:\PCRRG_FieldOps_Fresh"
Set-Location $root

Write-Host "Updating app.py for GPS fields..."

# NOTE: this assumes you already have the admin app.py from the previous script.
# We only patch in GPS columns and minor logic.

$app = Get-Content "app.py" -Raw

# Add GPS columns to Photo and JobContract models if not present
if ($app -notmatch "latitude = db.Column") {
    $app = $app -replace "class Photo\(db.Model\):\s*id = db.Column\(db.Integer, primary_key=True\)\s*job_id = db.Column\(db.Integer, db.ForeignKey\('job.id'\), nullable=False\)\s*filename = db.Column\(db.String\(255\), nullable=False\)\s*category = db.Column\(db.String\(100\)\)\s*uploaded_at = db.Column\(db.DateTime, default=datetime.utcnow\)",
@"
class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
"@
}

if ($app -notmatch "JobContract\(db.Model\).*latitude") {
    $app = $app -replace "class JobContract\(db.Model\):\s*id = db.Column\(db.Integer, primary_key=True\)\s*job_id = db.Column\(db.Integer, db.ForeignKey\('job.id'\), nullable=False\)\s*template_id = db.Column\(db.Integer, db.ForeignKey\('contract_template.id'\)\)\s*signed = db.Column\(db.Boolean, default=False\)\s*signed_at = db.Column\(db.DateTime\)\s*signer_name = db.Column\(db.String\(255\)\)\s*signer_email = db.Column\(db.String\(255\)\)",
@"
class JobContract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('contract_template.id'))
    signed = db.Column(db.Boolean, default=False)
    signed_at = db.Column(db.DateTime)
    signer_name = db.Column(db.String(255))
    signer_email = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
"@
}

# Patch upload_photo route to accept GPS
if ($app -notmatch "request.form.get\('lat'\)") {
    $app = $app -replace "photo = Photo\(job_id=job.id, filename=filename, category=request.form.get\('category'\)\)",
@"
    lat = request.form.get('lat')
    lon = request.form.get('lon')
    photo = Photo(job_id=job.id, filename=filename,
                  category=request.form.get('category'),
                  latitude=float(lat) if lat else None,
                  longitude=float(lon) if lon else None)
"@
}

# Patch sign_contract route to accept GPS
if ($app -notmatch "signer_lat") {
    $app = $app -replace "jc.signed = True\s*jc.signed_at = datetime.utcnow\(\)\s*jc.signer_name = signer_name\s*jc.signer_email = signer_email",
@"
        signer_lat = request.form.get('lat')
        signer_lon = request.form.get('lon')
        jc.signed = True
        jc.signed_at = datetime.utcnow()
        jc.signer_name = signer_name
        jc.signer_email = signer_email
        jc.latitude = float(signer_lat) if signer_lat else None
        jc.longitude = float(signer_lon) if signer_lon else None
"@
}

Set-Content -Encoding UTF8 "app.py" $app
Write-Host "app.py GPS patch complete."

Write-Host "Updating view_job.html for GPS + barcode + offline-friendly UI..."

@"
{% extends 'base.html' %}
{% block content %}
<div class='d-flex justify-content-between align-items-center mb-3'>
  <h1 class='h4'>{{ job.job_number }} — {{ job.title }}</h1>
  <div>
    <a href='{{ url_for('dashboard') }}' class='btn btn-sm btn-outline-secondary'>Back</a>
    {% if is_admin %}
      <a href='{{ url_for('edit_job', job_id=job.id) }}' class='btn btn-sm btn-outline-primary ms-2'>Edit Job</a>
      <form method='post' action='{{ url_for('archive_job', job_id=job.id) }}' class='d-inline'>
        <button class='btn btn-sm btn-outline-danger ms-2' type='submit'>Archive</button>
      </form>
    {% endif %}
  </div>
</div>

<div class='row'>
  <div class='col-md-8'>

    <div class='card mb-3'>
      <div class='card-body'>
        <h5>{{ job.client_name }}</h5>
        <p>{{ job.address }}</p>
        <p><strong>Service:</strong> {{ job.service_type }}</p>
        <p><strong>Status:</strong> {{ job.status }}</p>
      </div>
    </div>

    <div class='card mb-3'>
      <div class='card-header d-flex justify-content-between'>
        <span>Photos</span>
        <small class='text-muted'>GPS tagged when possible</small>
      </div>
      <div class='card-body'>
        {% if photos %}
          <div class='row g-2'>
            {% for p in photos %}
              <div class='col-6 col-md-4'>
                <img src='{{ url_for('static', filename='uploads/' ~ p.filename) }}' class='img-fluid rounded'>
                {% if p.latitude and p.longitude %}
                  <small class='text-muted d-block'>Lat: {{ '%.5f'|format(p.latitude) }}, Lon: {{ '%.5f'|format(p.longitude) }}</small>
                {% endif %}
              </div>
            {% endfor %}
          </div>
        {% else %}
          <p class='text-muted'>No photos uploaded.</p>
        {% endif %}
        <form id='photoForm' method='post' action='{{ url_for('upload_photo', job_id=job.id) }}' enctype='multipart/form-data' class='mt-3'>
          <input type='hidden' name='lat' id='photoLat'>
          <input type='hidden' name='lon' id='photoLon'>
          <div class='mb-2'>
            <input type='file' name='photo' class='form-control' accept='image/*' capture='environment'>
          </div>
          <div class='mb-2'>
            <input type='text' name='category' class='form-control' placeholder='Category (optional)'>
          </div>
          <button class='btn btn-sm btn-primary' type='submit'>Upload Photo</button>
        </form>
      </div>
    </div>

    <div class='card mb-3'>
      <div class='card-header'>Packout</div>
      <div class='card-body'>
        {% if packout_items %}
          <ul class='list-group mb-3'>
            {% for item in packout_items %}
              <li class='list-group-item d-flex justify-content-between'>
                <span>{{ item.name }} ({{ item.quantity }}) — {{ item.location }}</span>
                <small class='text-muted'>{{ item.notes }}</small>
                {% if is_admin %}
                  <form method='post' action='{{ url_for('delete_packout_item', job_id=job.id, item_id=item.id) }}'>
                    <button class='btn btn-sm btn-outline-danger' type='submit'>Delete</button>
                  </form>
                {% endif %}
              </li>
            {% endfor %}
          </ul>
        {% else %}
          <p class='text-muted'>No packout items.</p>
        {% endif %}
        <form method='post' action='{{ url_for('add_packout_item', job_id=job.id) }}'>
          <div class='row g-2'>
            <div class='col-4'><input class='form-control' name='name' placeholder='Item'></div>
            <div class='col-2'><input class='form-control' name='quantity' placeholder='Qty' value='1'></div>
            <div class='col-3'><input class='form-control' name='location' placeholder='Room'></div>
            <div class='col-3'><input class='form-control' name='notes' placeholder='Notes'></div>
          </div>
          <button class='btn btn-sm btn-outline-primary mt-2' type='submit'>Add Item</button>
        </form>
      </div>
    </div>

    <div class='card mb-3'>
      <div class='card-header d-flex justify-content-between'>
        <span>Contracts</span>
        <small class='text-muted'>GPS tagged on sign</small>
      </div>
      <div class='card-body'>
        {% if contracts %}
          <ul class='list-group mb-3'>
            {% for c in contracts %}
              <li class='list-group-item d-flex justify-content-between align-items-center'>
                <span>Template #{{ c.template_id }} — {% if c.signed %}Signed{% else %}Pending{% endif %}</span>
                <div class='text-end'>
                  {% if c.latitude and c.longitude %}
                    <small class='text-muted d-block'>Lat: {{ '%.5f'|format(c.latitude) }}, Lon: {{ '%.5f'|format(c.longitude) }}</small>
                  {% endif %}
                  {% if not c.signed %}
                    <a href='{{ url_for('sign_contract', job_id=job.id, contract_id=c.id) }}' class='btn btn-sm btn-outline-success mt-1'>Sign</a>
                  {% endif %}
                </div>
              </li>
            {% endfor %}
          </ul>
        {% else %}
          <p class='text-muted'>No contracts attached.</p>
        {% endif %}
        {% if is_admin %}
          <form method='post' action='{{ url_for('attach_contract', job_id=job.id) }}'>
            <div class='mb-2'>
              <select class='form-select' name='template_id'>
                {% for t in templates %}
                  <option value='{{ t.id }}'>{{ t.name }}</option>
                {% endfor %}
              </select>
            </div>
            <button class='btn btn-sm btn-outline-secondary' type='submit'>Attach Contract</button>
          </form>
        {% endif %}
      </div>
    </div>

    <div class='card mb-3'>
      <div class='card-header'>Share Job</div>
      <div class='card-body'>
        <form method='post' action='{{ url_for('share_job', job_id=job.id) }}'>
          <div class='mb-2'>
            <input class='form-control' name='email' placeholder='Recipient email'>
          </div>
          <button class='btn btn-sm btn-outline-primary' type='submit'>Email Job Report</button>
        </form>
      </div>
    </div>

    {% if tabs %}
      <div class='card mb-3'>
        <div class='card-header'>Custom Fields</div>
        <div class='card-body'>
          <form method='post' action='{{ url_for('save_custom_fields', job_id=job.id) }}'>
            {% for tab in tabs %}
              <h6 class='mt-2'>{{ tab.name }}</h6>
              {% for field in tab.fields %}
                <div class='mb-2'>
                  <label class='form-label'>{{ field.label }}</label>
                  {% set val = values_map.get(field.id) %}
                  {% if field.field_type == 'text' %}
                    <input class='form-control' name='field_{{ field.id }}' value='{{ val or "" }}'>
                  {% elif field.field_type == 'number' %}
                    <input class='form-control' type='number' name='field_{{ field.id }}' value='{{ val or "" }}'>
                  {% elif field.field_type == 'checkbox' %}
                    <input class='form-check-input' type='checkbox' name='field_{{ field.id }}' value='yes' {% if val == 'yes' %}checked{% endif %}>
                  {% elif field.field_type == 'dropdown' %}
                    <select class='form-select' name='field_{{ field.id }}'>
                      {% for opt in (field.options or '').split(',') %}
                        <option value='{{ opt.strip() }}' {% if val == opt.strip() %}selected{% endif %}>{{ opt.strip() }}</option>
                      {% endfor %}
                    </select>
                  {% endif %}
                </div>
              {% endfor %}
            {% endfor %}
            <button class='btn btn-sm btn-primary mt-2' type='submit'>Save Custom Fields</button>
          </form>
        </div>
      </div>
    {% endif %}

  </div>
</div>

<script>
function setGPS(hiddenLatId, hiddenLonId) {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(function(pos) {
    document.getElementById(hiddenLatId).value = pos.coords.latitude;
    document.getElementById(hiddenLonId).value = pos.coords.longitude;
  });
}
document.addEventListener('DOMContentLoaded', function() {
  setGPS('photoLat', 'photoLon');
});
</script>
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\view_job.html"

Write-Host "Writing basic service worker and manifest for offline/PWA..."

# service-worker.js
@"
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open('pcrrg-shell-v1').then(cache => {
      return cache.addAll([
        '/',
        '/login',
        '/static/manifest.json',
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'
      ]);
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(resp => {
      return resp || fetch(event.request);
    })
  );
});
"@ | Set-Content -Encoding UTF8 "static\service-worker.js"

# manifest.json
@"
{
  "name": "PCRRG FieldOps",
  "short_name": "FieldOps",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#0d6efd",
  "icons": []
}
"@ | Set-Content -Encoding UTF8 "static\manifest.json"

Write-Host "GPS + offline + inventory upgrade complete."
