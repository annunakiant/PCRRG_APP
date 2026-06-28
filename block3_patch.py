import os, re

# --- CREATE static/js/signature.js ---
os.makedirs('static/js', exist_ok=True)
with open('static/js/signature.js', 'w', encoding='utf-8') as f:
    f.write("""document.addEventListener('DOMContentLoaded', function () {
  const canvas = document.getElementById('sig-canvas');

  const ctx = canvas.getContext('2d');
  let drawing = false;

  function start(e) {
    drawing = true;
    ctx.beginPath();
    ctx.moveTo(e.offsetX, e.offsetY);
  }

  function draw(e) {
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#000';
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.stroke();
  }

  function end() {
    drawing = false;
  }

  canvas.addEventListener('mousedown', start);
  canvas.addEventListener('mousemove', draw);
  canvas.addEventListener('mouseup', end);
  canvas.addEventListener('mouseleave', end);

  document.getElementById('sig-clear').addEventListener('click', function () {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  });

  document.getElementById('sig-submit').addEventListener('click', function () {
    const dataURL = canvas.toDataURL('image/png');
    document.getElementById('signature_data').value = dataURL;
    document.getElementById('sig-form').submit();
  });
});""")

# --- PATCH sign_contract.html to include signature canvas ---
sc_path = 'templates/sign_contract.html'
with open(sc_path, 'r', encoding='utf-8') as f:
    html = f.read()

html = """{% extends 'base.html' %}
{% block content %}
<h2>Sign Contract for Job {{ job.job_number }} — {{ job.title }}</h2>

<div class='cc-card mb-3'>
  <p><strong>Template ID:</strong> {{ contract.template_id }}</p>
  <p><strong>Status:</strong> {{ 'Signed' if contract.signed else 'Pending' }}</p>
</div>

<form id='sig-form' method='post' class='cc-card'>
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

  <h4 class='mt-3'>Signature</h4>
  <canvas id='sig-canvas' width='400' height='200' style='border:1px solid #333; border-radius:8px;'></canvas>

  <input type='hidden' id='signature_data' name='signature_data'>

  <div class='mt-2'>
    <button type='button' id='sig-clear' class='btn btn-secondary'>Clear</button>
    <button type='button' id='sig-submit' class='btn btn-primary'>Submit Signature</button>
  </div>
</form>

<script src='/static/js/signature.js'></script>
{% endblock %}"""

with open(sc_path, 'w', encoding='utf-8') as f:
    f.write(html)

# --- PATCH app.py to save signature PNG ---
app_path = 'app.py'
with open(app_path, 'r', encoding='utf-8') as f:
    code = f.read()

pattern = r"def sign_contract\(job_id, contract_id\):[\s\S]*?return render_template\('sign_contract.html', job=job, contract=jc\)"
replacement = """def sign_contract(job_id, contract_id):
    job = Job.query.get_or_404(job_id)
    jc = JobContract.query.get_or_404(contract_id)

    if request.method == 'POST':
        signer_name = request.form.get('signer_name')
        signer_email = request.form.get('signer_email')
        jc.signed = True
        jc.signed_at = datetime.utcnow()
        jc.signer_name = signer_name
        jc.signer_email = signer_email

        signer_lat = request.form.get('lat')
        signer_lon = request.form.get('lon')
        jc.latitude = float(signer_lat) if signer_lat else None
        jc.longitude = float(signer_lon) if signer_lon else None

        # Signature PNG
        sig_data = request.form.get('signature_data')
        if sig_data:
            import base64
            sig_bytes = base64.b64decode(sig_data.split(',')[1])
            os.makedirs(app.config['UPLOAD_FOLDER_CONTRACTS'], exist_ok=True)
            sig_filename = f"signature_{job.id}_{contract_id}_{int(datetime.utcnow().timestamp())}.png"
            sig_path = os.path.join(app.config['UPLOAD_FOLDER_CONTRACTS'], sig_filename)
            with open(sig_path, 'wb') as sig_file:
                sig_file.write(sig_bytes)
            jc.signature_file = sig_filename

        db.session.commit()
        flash('Contract signed.')
        return redirect(url_for('view_job', job_id=job.id))

    return render_template('sign_contract.html', job=job, contract=jc)"""

code = re.sub(pattern, replacement, code)
with open(app_path, 'w', encoding='utf-8') as f:
    f.write(code)

print('✔ BLOCK 3 COMPLETE — Signature canvas, PNG upload, auto-foldering, GPS signatures')

