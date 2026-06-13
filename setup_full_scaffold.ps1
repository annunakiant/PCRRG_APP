# setup_full_scaffold.ps1
# Save this file and run it from PowerShell: .\setup_full_scaffold.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = "C:\PCRRG_FieldOps_Fresh"
if (!(Test-Path $root)) { New-Item -ItemType Directory -Path $root | Out-Null }
Set-Location $root

Write-Host "Creating virtualenv..."
python -m venv .venv

Write-Host "Activating venv and installing dependencies..."
$activate = Join-Path $root ".venv\Scripts\Activate.ps1"
# Use pip from venv
& "$root\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$root\.venv\Scripts\python.exe" -m pip install flask flask_sqlalchemy flask_login flask_wtf email-validator gunicorn python-dotenv

# Create folders
Write-Host "Creating folders..."
$dirs = @("templates","static","static\uploads","static\contracts","static\packouts","data")
foreach ($d in $dirs) { if (!(Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null } }

# Write .gitignore
@"
venv/
.venv/
__pycache__/
*.pyc
instance/
*.db
.env
.env.*
"@ | Set-Content -Encoding UTF8 ".gitignore"

# requirements
@"
Flask
Flask-SQLAlchemy
Flask-Login
Flask-WTF
email-validator
gunicorn
python-dotenv
"@ | Set-Content -Encoding UTF8 "requirements.txt"

# README
@"
PCRRG FieldOps - Fresh Scaffold
--------------------------------
Run:
  .\.venv\Scripts\activate
  python app.py

Admin login:
  username: admin
  pin: 1234

This scaffold includes:
- Flask app with jobs, photos, packout, contracts, roles, PIN login
- Templates and static files (PWA placeholders)
- Use this as the base to add e-sign, email share, archive, search, and more.
"@ | Set-Content -Encoding UTF8 "README.md"

# app.py
@"
import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'data', 'pcrrg_fieldops.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER_PHOTOS'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER_CONTRACTS'] = os.path.join(BASE_DIR, 'static', 'contracts')
app.config['UPLOAD_FOLDER_PACKOUT'] = os.path.join(BASE_DIR, 'static', 'packouts')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    pin = db.Column(db.String(4), nullable=False)
    name = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255))
    role = db.Column(db.String(50), default='tech')
    def is_admin(self):
        return self.role == 'admin'

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    client_name = db.Column(db.String(255))
    address = db.Column(db.String(255))
    status = db.Column(db.String(50), default='open')
    service_type = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    photos = db.relationship('Photo', backref='job', lazy='dynamic')
    packout_items = db.relationship('PackoutItem', backref='job', lazy='dynamic')
    contracts = db.relationship('JobContract', backref='job', lazy='dynamic')

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class PackoutItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    location = db.Column(db.String(255))
    notes = db.Column(db.String(255))

class ContractTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)

class JobContract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('contract_template.id'))
    signed = db.Column(db.Boolean, default=False)
    signed_at = db.Column(db.DateTime)
    signer_name = db.Column(db.String(255))
    signer_email = db.Column(db.String(255))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_admin():
    return current_user.is_authenticated and current_user.is_admin()

@app.context_processor
def inject_globals():
    return {'is_admin': is_admin(), 'current_user': current_user}

# Routes
@app.route('/')
@login_required
def dashboard():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return render_template('dashboard.html', jobs=jobs)

@app.route('/jobs/<int:job_id>')
@login_required
def view_job(job_id):
    job = Job.query.get_or_404(job_id)
    photos = job.photos.all()
    packout_items = job.packout_items.all()
    contracts = job.contracts.all()
    templates = ContractTemplate.query.all()
    return render_template('view_job.html', job=job, photos=photos, packout_items=packout_items, contracts=contracts, templates=templates)

@app.route('/jobs/new', methods=['GET','POST'])
@login_required
def new_job():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        job = Job(job_number=request.form.get('job_number') or 'JOB-0001', title=request.form.get('title') or 'Untitled', client_name=request.form.get('client_name'), address=request.form.get('address'), service_type=request.form.get('service_type'))
        db.session.add(job)
        db.session.commit()
        flash('Job created.')
        return redirect(url_for('view_job', job_id=job.id))
    return render_template('new_job.html')

@app.route('/jobs/<int:job_id>/upload_photo', methods=['POST'])
@login_required
def upload_photo(job_id):
    job = Job.query.get_or_404(job_id)
    file = request.files.get('photo')
    if not file or file.filename == '':
        flash('No file selected.')
        return redirect(url_for('view_job', job_id=job.id))
    os.makedirs(app.config['UPLOAD_FOLDER_PHOTOS'], exist_ok=True)
    filename = f\"{job.id}_{int(datetime.utcnow().timestamp())}_{file.filename}\"
    path = os.path.join(app.config['UPLOAD_FOLDER_PHOTOS'], filename)
    file.save(path)
    photo = Photo(job_id=job.id, filename=filename, category=request.form.get('category'))
    db.session.add(photo)
    db.session.commit()
    flash('Photo uploaded.')
    return redirect(url_for('view_job', job_id=job.id))

@app.route('/jobs/<int:job_id>/packout/add', methods=['POST'])
@login_required
def add_packout_item(job_id):
    job = Job.query.get_or_404(job_id)
    item = PackoutItem(job_id=job.id, name=request.form.get('name'), quantity=int(request.form.get('quantity') or 1), location=request.form.get('location'), notes=request.form.get('notes'))
    db.session.add(item)
    db.session.commit()
    flash('Packout item added.')
    return redirect(url_for('view_job', job_id=job.id))

@app.route('/contracts/templates', methods=['GET','POST'])
@login_required
def manage_contracts():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        file = request.files.get('contract_file')
        name = request.form.get('name') or (file.filename if file else '')
        if file and file.filename:
            os.makedirs(app.config['UPLOAD_FOLDER_CONTRACTS'], exist_ok=True)
            filename = f\"{int(datetime.utcnow().timestamp())}_{file.filename}\"
            path = os.path.join(app.config['UPLOAD_FOLDER_CONTRACTS'], filename)
            file.save(path)
            tmpl = ContractTemplate(name=name, filename=filename)
            db.session.add(tmpl)
            db.session.commit()
            flash('Contract template uploaded.')
    templates = ContractTemplate.query.all()
    return render_template('contracts.html', templates=templates)

@app.route('/jobs/<int:job_id>/contracts/attach', methods=['POST'])
@login_required
def attach_contract(job_id):
    job = Job.query.get_or_404(job_id)
    template_id = int(request.form.get('template_id'))
    jc = JobContract(job_id=job.id, template_id=template_id)
    db.session.add(jc)
    db.session.commit()
    flash('Contract attached to job.')
    return redirect(url_for('view_job', job_id=job.id))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        pin = request.form.get('pin')
        user = User.query.filter_by(username=username, pin=pin).first()
        if user:
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or PIN.')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        pin = request.form.get('pin')
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
        user = User(username=username, pin=pin, name=name, phone=phone, email=email, role='tech')
        db.session.add(user)
        db.session.commit()
        flash('User registered. Ask admin to assign role.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def init_db():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', pin='1234', name='Admin', role='admin')
        db.session.add(admin)
        db.session.commit()
    if Job.query.count() == 0:
        job = Job(job_number='PCRRG-1001', title='Sample Job', client_name='Acme Corp', address='123 Main St', service_type='Water Mitigation')
        db.session.add(job)
        db.session.commit()

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER_PHOTOS'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_CONTRACTS'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_PACKOUT'], exist_ok=True)
    with app.app_context():
        init_db()
    app.run(debug=True)
"@ | Set-Content -Encoding UTF8 "app.py"

# templates/base.html
@"
<!doctype html>
<html lang='en'>
  <head>
    <meta charset='utf-8'>
    <title>PCRRG FieldOps</title>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>
    <link rel='manifest' href='{{ url_for('static', filename='manifest.json') }}'>
  </head>
  <body>
    <nav class='navbar navbar-light bg-light'>
      <div class='container-fluid'>
        <a class='navbar-brand' href='{{ url_for('dashboard') }}'>PCRRG</a>
        <div class='d-flex'>
          {% if current_user.is_authenticated %}
            <span class='me-2'>{{ current_user.name or current_user.username }}</span>
            <a class='btn btn-outline-secondary me-2' href='{{ url_for('dashboard') }}'>Dashboard</a>
            <a class='btn btn-outline-danger' href='{{ url_for('logout') }}'>Logout</a>
          {% else %}
            <a class='btn btn-outline-primary me-2' href='{{ url_for('login') }}'>Login</a>
            <a class='btn btn-outline-secondary' href='{{ url_for('register') }}'>Register</a>
          {% endif %}
        </div>
      </div>
    </nav>
    <main class='container mt-3 mb-5'>
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <div class='alert alert-info'>
            {% for m in messages %}{{ m }}{% endfor %}
          </div>
        {% endif %}
      {% endwith %}
      {% block content %}{% endblock %}
    </main>
    <script src='{{ url_for('static', filename='service-worker.js') }}'></script>
  </body>
</html>
"@ | Set-Content -Encoding UTF8 "templates\base.html"

# templates/login.html
@"
{% extends 'base.html' %}
{% block content %}
<div class='row justify-content-center'>
  <div class='col-md-4'>
    <div class='card'>
      <div class='card-body'>
        <h5 class='card-title'>Login</h5>
        <form method='post'>
          <div class='mb-3'>
            <label class='form-label'>Username</label>
            <input class='form-control' name='username'>
          </div>
          <div class='mb-3'>
            <label class='form-label'>4-digit PIN</label>
            <input class='form-control' name='pin' maxlength='4'>
          </div>
          <button class='btn btn-primary w-100' type='submit'>Login</button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\login.html"

# templates/register.html
@"
{% extends 'base.html' %}
{% block content %}
<div class='row justify-content-center'>
  <div class='col-md-5'>
    <div class='card'>
      <div class='card-body'>
        <h5 class='card-title'>Register</h5>
        <form method='post'>
          <div class='mb-3'><label class='form-label'>Name</label><input class='form-control' name='name'></div>
          <div class='mb-3'><label class='form-label'>Phone</label><input class='form-control' name='phone'></div>
          <div class='mb-3'><label class='form-label'>Email</label><input class='form-control' name='email'></div>
          <div class='mb-3'><label class='form-label'>Username</label><input class='form-control' name='username'></div>
          <div class='mb-3'><label class='form-label'>4-digit PIN</label><input class='form-control' name='pin' maxlength='4'></div>
          <button class='btn btn-primary w-100' type='submit'>Register</button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\register.html"

# templates/dashboard.html
@"
{% extends 'base.html' %}
{% block content %}
<div class='d-flex justify-content-between align-items-center mb-3'>
  <h1 class='h4'>Jobs</h1>
  {% if is_admin %}
    <a href='{{ url_for('new_job') }}' class='btn btn-primary'>New Job</a>
    <a href='{{ url_for('manage_contracts') }}' class='btn btn-outline-secondary ms-2'>Contracts</a>
  {% endif %}
</div>
{% if jobs %}
  <div class='row g-3'>
    {% for job in jobs %}
      <div class='col-md-4'>
        <div class='card h-100'>
          <div class='card-body d-flex flex-column'>
            <h5 class='card-title'>{{ job.job_number }} — {{ job.title }}</h5>
            <p class='card-text text-muted'>{{ job.client_name }} · {{ job.address }}</p>
            <p class='card-text'><small>Status: {{ job.status }}</small></p>
            <a href='{{ url_for('view_job', job_id=job.id) }}' class='btn btn-sm btn-outline-primary mt-auto'>Open</a>
          </div>
        </div>
      </div>
    {% endfor %}
  </div>
{% else %}
  <p>No jobs yet.</p>
{% endif %}
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\dashboard.html"

# templates/view_job.html
@"
{% extends 'base.html' %}
{% block content %}
<div class='d-flex justify-content-between align-items-center mb-3'>
  <h1 class='h4'>{{ job.job_number }} — {{ job.title }}</h1>
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
      <div class='card-header'>Photos</div>
      <div class='card-body'>
        {% if photos %}
          <div class='row g-2'>
            {% for p in photos %}
              <div class='col-6 col-md-4'>
                <img src='{{ url_for('static', filename='uploads/' ~ p.filename) }}' class='img-fluid rounded'>
              </div>
            {% endfor %}
          </div>
        {% else %}
          <p class='text-muted'>No photos uploaded.</p>
        {% endif %}
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
              </li>
            {% endfor %}
          </ul>
        {% else %}
          <p class='text-muted'>No packout items.</p>
        {% endif %}
      </div>
    </div>

    <div class='card mb-3'>
      <div class='card-header'>Contracts</div>
      <div class='card-body'>
        {% if contracts %}
          <ul class='list-group mb-3'>
            {% for c in contracts %}
              <li class='list-group-item'>
                Template #{{ c.template_id }} — {% if c.signed %}Signed{% else %}Pending{% endif %}
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

  </div>
</div>
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\view_job.html"

# templates/new_job.html
@"
{% extends 'base.html' %}
{% block content %}
<h1 class='h4 mb-3'>New Job</h1>
<form method='post'>
  <div class='mb-3'><label class='form-label'>Job Number</label><input class='form-control' name='job_number'></div>
  <div class='mb-3'><label class='form-label'>Title</label><input class='form-control' name='title'></div>
  <div class='mb-3'><label class='form-label'>Client Name</label><input class='form-control' name='client_name'></div>
  <div class='mb-3'><label class='form-label'>Address</label><input class='form-control' name='address'></div>
  <div class='mb-3'><label class='form-label'>Service Type</label><input class='form-control' name='service_type'></div>
  <button class='btn btn-primary' type='submit'>Create</button>
</form>
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\new_job.html"

# templates/contracts.html
@"
{% extends 'base.html' %}
{% block content %}
<h1 class='h4 mb-3'>Contract Templates</h1>

<form method='post' enctype='multipart/form-data' class='mb-3'>
  <div class='mb-2'><label class='form-label'>Name</label><input class='form-control' name='name'></div>
  <div class='mb-2'><label class='form-label'>File</label><input type='file' class='form-control' name='contract_file'></div>
  <button class='btn btn-primary' type='submit'>Upload Template</button>
</form>

{% if templates %}
  <ul class='list-group'>
    {% for t in templates %}
      <li class='list-group-item'>{{ t.name }} ({{ t.filename }})</li>
    {% endfor %}
  </ul>
{% else %}
  <p class='text-muted'>No templates yet.</p>
{% endif %}
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\contracts.html"

# static/manifest.json
@"
{
  ""name"": ""PCRRG FieldOps"",
  ""short_name"": ""FieldOps"",
  ""start_url"": ""/"",
  ""display"": ""standalone"",
  ""background_color"": ""#ffffff"",
  ""theme_color"": ""#0d6efd"",
  ""icons"": []
}
"@ | Set-Content -Encoding UTF8 "static\manifest.json"

# static/service-worker.js
@"
self.addEventListener('install', event => {
  console.log('Service worker installed');
});
self.addEventListener('fetch', event => {
  // default network behavior
});
"@ | Set-Content -Encoding UTF8 "static\service-worker.js"

# Initialize git
if (!(Test-Path ".git")) {
    git init
    git add -A
    git commit -m 'Initial scaffold commit'
}

Write-Host "Scaffold complete. Activate venv: .\.venv\Scripts\activate  then run: python app.py"
