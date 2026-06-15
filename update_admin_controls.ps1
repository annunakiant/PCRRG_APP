# update_admin_controls.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = "C:\PCRRG_FieldOps_Fresh"
Set-Location $root

Write-Host "Updating app.py with admin controls and custom tabs/fields..."

@"
import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import smtplib
from email.message import EmailMessage
import json

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'data', 'pcrrg_fieldops.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER_PHOTOS'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER_CONTRACTS'] = os.path.join(BASE_DIR, 'static', 'contracts')
app.config['UPLOAD_FOLDER_PACKOUT'] = os.path.join(BASE_DIR, 'static', 'packouts')
app.config['ARCHIVE_FOLDER'] = os.path.join(BASE_DIR, 'data', 'archive')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# MODELS
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
    status = db.Column(db.String(50), default='open')  # open, closed, archived
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

class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(100))
    barcode = db.Column(db.String(255))
    quantity = db.Column(db.Integer, default=0)
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

# Custom tabs/fields
class CustomTab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    order = db.Column(db.Integer, default=0)

class CustomField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tab_id = db.Column(db.Integer, db.ForeignKey('custom_tab.id'), nullable=False)
    label = db.Column(db.String(255), nullable=False)
    field_type = db.Column(db.String(50), nullable=False)  # text, number, checkbox, dropdown
    required = db.Column(db.Boolean, default=False)
    options = db.Column(db.String(255))  # for dropdown, comma-separated

    tab = db.relationship('CustomTab', backref='fields')

class CustomFieldValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('custom_field.id'), nullable=False)
    value = db.Column(db.String(255))

    field = db.relationship('CustomField')
    job = db.relationship('Job', backref='custom_values')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_admin():
    return current_user.is_authenticated and current_user.is_admin()

@app.context_processor
def inject_globals():
    return {'is_admin': is_admin(), 'current_user': current_user}

# EMAIL HELPER
def send_job_email(job, to_email, subject, body):
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT','587'))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    from_email = os.environ.get('FROM_EMAIL', smtp_user)

    if not (smtp_host and smtp_user and smtp_pass and from_email):
        print('Email not configured; skipping send.')
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

# CORE ROUTES (dashboard, jobs, etc.)
@app.route('/')
@login_required
def dashboard():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    inventory_count = InventoryItem.query.count()
    contracts_pending = JobContract.query.filter_by(signed=False).count()
    return render_template('dashboard.html', jobs=jobs,
                           inventory_count=inventory_count,
                           contracts_pending=contracts_pending)

@app.route('/jobs/<int:job_id>')
@login_required
def view_job(job_id):
    job = Job.query.get_or_404(job_id)
    photos = job.photos.all()
    packout_items = job.packout_items.all()
    contracts = job.contracts.all()
    templates = ContractTemplate.query.all()
    tabs = CustomTab.query.order_by(CustomTab.order).all()
    # build field values map
    values_map = {}
    for v in job.custom_values:
        values_map[v.field_id] = v.value
    return render_template('view_job.html', job=job, photos=photos,
                           packout_items=packout_items, contracts=contracts,
                           templates=templates, tabs=tabs, values_map=values_map)

@app.route('/jobs/new', methods=['GET','POST'])
@login_required
def new_job():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        job = Job(
            job_number=request.form.get('job_number') or 'JOB-0001',
            title=request.form.get('title') or 'Untitled',
            client_name=request.form.get('client_name'),
            address=request.form.get('address'),
            service_type=request.form.get('service_type')
        )
        db.session.add(job)
        db.session.commit()
        flash('Job created.')
        return redirect(url_for('view_job', job_id=job.id))
    return render_template('new_job.html')

@app.route('/jobs/<int:job_id>/edit', methods=['GET','POST'])
@login_required
def edit_job(job_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    job = Job.query.get_or_404(job_id)
    if request.method == 'POST':
        job.job_number = request.form.get('job_number') or job.job_number
        job.title = request.form.get('title') or job.title
        job.client_name = request.form.get('client_name')
        job.address = request.form.get('address')
        job.service_type = request.form.get('service_type')
        job.status = request.form.get('status') or job.status
        if job.status == 'closed' and not job.closed_at:
            job.closed_at = datetime.utcnow()
        db.session.commit()
        flash('Job updated.')
        return redirect(url_for('view_job', job_id=job.id))
    return render_template('edit_job.html', job=job)

@app.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash('Job deleted.')
    return redirect(url_for('dashboard'))

@app.route('/jobs/<int:job_id>/upload_photo', methods=['POST'])
@login_required
def upload_photo(job_id):
    job = Job.query.get_or_404(job_id)
    file = request.files.get('photo')
    if not file or file.filename == '':
        flash('No file selected.')
        return redirect(url_for('view_job', job_id=job.id))
    os.makedirs(app.config['UPLOAD_FOLDER_PHOTOS'], exist_ok=True)
    filename = f"{job.id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
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
    item = PackoutItem(
        job_id=job.id,
        name=request.form.get('name'),
        quantity=int(request.form.get('quantity') or 1),
        location=request.form.get('location'),
        notes=request.form.get('notes')
    )
    db.session.add(item)
    db.session.commit()
    flash('Packout item added.')
    return redirect(url_for('view_job', job_id=job.id))

@app.route('/jobs/<int:job_id>/packout/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_packout_item(job_id, item_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('view_job', job_id=job_id))
    item = PackoutItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Packout item deleted.')
    return redirect(url_for('view_job', job_id=job_id))

@app.route('/inventory')
@login_required
def inventory_list():
    items = InventoryItem.query.order_by(InventoryItem.name).all()
    return render_template('inventory.html', items=items)

@app.route('/inventory/new', methods=['GET','POST'])
@login_required
def inventory_new():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('inventory_list'))
    if request.method == 'POST':
        item = InventoryItem(
            name=request.form.get('name'),
            sku=request.form.get('sku'),
            barcode=request.form.get('barcode'),
            quantity=int(request.form.get('quantity') or 0),
            location=request.form.get('location'),
            notes=request.form.get('notes')
        )
        db.session.add(item)
        db.session.commit()
        flash('Inventory item created.')
        return redirect(url_for('inventory_list'))
    return render_template('inventory_edit.html', item=None)

@app.route('/inventory/<int:item_id>/edit', methods=['GET','POST'])
@login_required
def inventory_edit(item_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('inventory_list'))
    item = InventoryItem.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form.get('name') or item.name
        item.sku = request.form.get('sku')
        item.barcode = request.form.get('barcode')
        item.quantity = int(request.form.get('quantity') or item.quantity)
        item.location = request.form.get('location')
        item.notes = request.form.get('notes')
        db.session.commit()
        flash('Inventory item updated.')
        return redirect(url_for('inventory_list'))
    return render_template('inventory_edit.html', item=item)

@app.route('/inventory/<int:item_id>/delete', methods=['POST'])
@login_required
def inventory_delete(item_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('inventory_list'))
    item = InventoryItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Inventory item deleted.')
    return redirect(url_for('inventory_list'))

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
            filename = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
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

@app.route('/jobs/<int:job_id>/contracts/<int:contract_id>/sign', methods=['GET','POST'])
def sign_contract(job_id, contract_id):
    job = Job.query.get_or_404(job_id)
    jc = JobContract.query.get_or_404(contract_id)
    if request.method == 'POST':
        signer_name = request.form.get('signer_name')
        signer_email = request.form.get('signer_email')
        jc.signed = True
        jc.signed_at = datetime.utcnow()
        jc.signer_name = signer_name
        jc.signer_email = signer_email
        db.session.commit()
        flash('Contract signed.')
        return redirect(url_for('view_job', job_id=job.id))
    return render_template('sign_contract.html', job=job, contract=jc)

@app.route('/jobs/<int:job_id>/share', methods=['POST'])
@login_required
def share_job(job_id):
    job = Job.query.get_or_404(job_id)
    to_email = request.form.get('email')
    if not to_email:
        flash('Email required.')
        return redirect(url_for('view_job', job_id=job.id))

    packout_items = job.packout_items.all()
    contracts = job.contracts.all()

    body_lines = [
        f"Job {job.job_number} - {job.title}",
        f"Client: {job.client_name}",
        f"Address: {job.address}",
        f"Service: {job.service_type}",
        f"Status: {job.status}",
        "",
        "Packout items:"
    ]
    for item in packout_items:
        body_lines.append(f"- {item.name} x{item.quantity} @ {item.location} ({item.notes})")
    body_lines.append("")
    body_lines.append("Contracts:")
    for c in contracts:
        status = "Signed" if c.signed else "Pending"
        body_lines.append(f"- Template #{c.template_id} [{status}]")

    body = "\n".join(body_lines)
    send_job_email(job, to_email, f"Job report: {job.job_number}", body)
    flash('Job report emailed (if email is configured).')
    return redirect(url_for('view_job', job_id=job.id))

@app.route('/jobs/<int:job_id>/archive', methods=['POST'])
@login_required
def archive_job(job_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('view_job', job_id=job_id))
    job = Job.query.get_or_404(job_id)
    os.makedirs(app.config['ARCHIVE_FOLDER'], exist_ok=True)
    archive_path = os.path.join(app.config['ARCHIVE_FOLDER'], f"job_{job.id}.json")

    data = {
        'id': job.id,
        'job_number': job.job_number,
        'title': job.title,
        'client_name': job.client_name,
        'address': job.address,
        'status': job.status,
        'service_type': job.service_type,
        'created_at': job.created_at.isoformat() if job.created_at else None,
        'closed_at': job.closed_at.isoformat() if job.closed_at else None,
        'photos': [
            {'filename': p.filename, 'category': p.category, 'uploaded_at': p.uploaded_at.isoformat() if p.uploaded_at else None}
            for p in job.photos.all()
        ],
        'packout_items': [
            {'name': i.name, 'quantity': i.quantity, 'location': i.location, 'notes': i.notes}
            for i in job.packout_items.all()
        ],
        'contracts': [
            {
                'template_id': c.template_id,
                'signed': c.signed,
                'signed_at': c.signed_at.isoformat() if c.signed_at else None,
                'signer_name': c.signer_name,
                'signer_email': c.signer_email
            }
            for c in job.contracts.all()
        ]
    }

    with open(archive_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    job.status = 'archived'
    job.closed_at = datetime.utcnow()
    db.session.commit()
    flash('Job archived and saved to archive folder.')
    return redirect(url_for('dashboard'))

# ADMIN CONTROL CENTER
@app.route('/admin')
@login_required
def admin_home():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    jobs = Job.query.order_by(Job.created_at.desc()).limit(10).all()
    inventory_items = InventoryItem.query.order_by(InventoryItem.name).limit(10).all()
    tabs = CustomTab.query.order_by(CustomTab.order).all()
    return render_template('admin.html', jobs=jobs, inventory_items=inventory_items, tabs=tabs)

@app.route('/admin/tabs', methods=['GET','POST'])
@login_required
def admin_tabs():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name')
        order = int(request.form.get('order') or 0)
        tab = CustomTab(name=name, order=order)
        db.session.add(tab)
        db.session.commit()
        flash('Tab created.')
        return redirect(url_for('admin_tabs'))
    tabs = CustomTab.query.order_by(CustomTab.order).all()
    return render_template('admin_tabs.html', tabs=tabs)

@app.route('/admin/tabs/<int:tab_id>/delete', methods=['POST'])
@login_required
def admin_tab_delete(tab_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('admin_tabs'))
    tab = CustomTab.query.get_or_404(tab_id)
    # delete fields and values under this tab
    for field in tab.fields:
        CustomFieldValue.query.filter_by(field_id=field.id).delete()
        db.session.delete(field)
    db.session.delete(tab)
    db.session.commit()
    flash('Tab and its fields deleted.')
    return redirect(url_for('admin_tabs'))

@app.route('/admin/fields/<int:tab_id>', methods=['GET','POST'])
@login_required
def admin_fields(tab_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    tab = CustomTab.query.get_or_404(tab_id)
    if request.method == 'POST':
        label = request.form.get('label')
        field_type = request.form.get('field_type')
        required = bool(request.form.get('required'))
        options = request.form.get('options')
        field = CustomField(tab_id=tab.id, label=label, field_type=field_type,
                            required=required, options=options)
        db.session.add(field)
        db.session.commit()
        flash('Field created.')
        return redirect(url_for('admin_fields', tab_id=tab.id))
    return render_template('admin_fields.html', tab=tab)

@app.route('/admin/fields/<int:field_id>/delete', methods=['POST'])
@login_required
def admin_field_delete(field_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('admin_home'))
    field = CustomField.query.get_or_404(field_id)
    CustomFieldValue.query.filter_by(field_id=field.id).delete()
    db.session.delete(field)
    db.session.commit()
    flash('Field deleted.')
    return redirect(url_for('admin_fields', tab_id=field.tab_id))

@app.route('/jobs/<int:job_id>/custom/save', methods=['POST'])
@login_required
def save_custom_fields(job_id):
    job = Job.query.get_or_404(job_id)
    tabs = CustomTab.query.all()
    for tab in tabs:
        for field in tab.fields:
            key = f"field_{field.id}"
            val = request.form.get(key)
            existing = CustomFieldValue.query.filter_by(job_id=job.id, field_id=field.id).first()
            if existing:
                existing.value = val
            else:
                if val:
                    cfv = CustomFieldValue(job_id=job.id, field_id=field.id, value=val)
                    db.session.add(cfv)
    db.session.commit()
    flash('Custom fields saved.')
    return redirect(url_for('view_job', job_id=job.id))

# AUTH
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
        job = Job(job_number='PCRRG-1001', title='Sample Job', client_name='Acme Corp',
                  address='123 Main St', service_type='Water Mitigation')
        db.session.add(job)
        db.session.commit()

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER_PHOTOS'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_CONTRACTS'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_PACKOUT'], exist_ok=True)
    os.makedirs(app.config['ARCHIVE_FOLDER'], exist_ok=True)
    with app.app_context():
        init_db()
    app.run(debug=True)
"@ | Set-Content -Encoding UTF8 "app.py"

Write-Host "Updating templates..."

# base.html
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
            {% if is_admin %}
              <a class='btn btn-outline-dark me-2' href='{{ url_for('admin_home') }}'>Admin</a>
            {% endif %}
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

# dashboard.html
@"
{% extends 'base.html' %}
{% block content %}
<div class='row mb-3'>
  <div class='col-md-8'>
    <h1 class='h4'>Jobs</h1>
  </div>
  <div class='col-md-4 text-end'>
    {% if is_admin %}
      <a href='{{ url_for('new_job') }}' class='btn btn-primary'>New Job</a>
      <a href='{{ url_for('inventory_list') }}' class='btn btn-outline-secondary ms-2'>Inventory</a>
      <a href='{{ url_for('manage_contracts') }}' class='btn btn-outline-secondary ms-2'>Contracts</a>
    {% endif %}
  </div>
</div>

<div class='row'>
  <div class='col-md-8'>
    {% if jobs %}
      <div class='row g-3'>
        {% for job in jobs %}
          <div class='col-md-6'>
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
  </div>
  <div class='col-md-4'>
    <div class='card mb-3'>
      <div class='card-body'>
        <h5 class='card-title'>Summary</h5>
        <p>Inventory items: {{ inventory_count }}</p>
        <p>Contracts pending: {{ contracts_pending }}</p>
      </div>
    </div>
  </div>
</div>
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\dashboard.html"

# admin.html
@"
{% extends 'base.html' %}
{% block content %}
<h1 class='h4 mb-3'>Admin Control Center</h1>

<ul class='nav nav-tabs mb-3'>
  <li class='nav-item'><a class='nav-link active' data-bs-toggle='tab' href='#jobs'>Jobs</a></li>
  <li class='nav-item'><a class='nav-link' data-bs-toggle='tab' href='#inventory'>Inventory</a></li>
  <li class='nav-item'><a class='nav-link' data-bs-toggle='tab' href='#tabs'>Custom Tabs</a></li>
</ul>

<div class='tab-content'>
  <div class='tab-pane fade show active' id='jobs'>
    <h5>Recent Jobs</h5>
    <table class='table table-sm'>
      <thead><tr><th>#</th><th>Title</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>
        {% for job in jobs %}
          <tr>
            <td>{{ job.job_number }}</td>
            <td>{{ job.title }}</td>
            <td>{{ job.status }}</td>
            <td>
              <a href='{{ url_for('edit_job', job_id=job.id) }}' class='btn btn-sm btn-outline-primary'>Edit</a>
              <form method='post' action='{{ url_for('delete_job', job_id=job.id) }}' class='d-inline'>
                <button class='btn btn-sm btn-outline-danger' type='submit'>Delete</button>
              </form>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class='tab-pane fade' id='inventory'>
    <h5>Inventory</h5>
    <a href='{{ url_for('inventory_new') }}' class='btn btn-sm btn-primary mb-2'>New Item</a>
    <table class='table table-sm'>
      <thead><tr><th>Name</th><th>SKU</th><th>Barcode</th><th>Qty</th><th>Location</th><th>Actions</th></tr></thead>
      <tbody>
        {% for item in inventory_items %}
          <tr>
            <td>{{ item.name }}</td>
            <td>{{ item.sku }}</td>
            <td>{{ item.barcode }}</td>
            <td>{{ item.quantity }}</td>
            <td>{{ item.location }}</td>
            <td>
              <a href='{{ url_for('inventory_edit', item_id=item.id) }}' class='btn btn-sm btn-outline-primary'>Edit</a>
              <form method='post' action='{{ url_for('inventory_delete', item_id=item.id) }}' class='d-inline'>
                <button class='btn btn-sm btn-outline-danger' type='submit'>Delete</button>
              </form>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class='tab-pane fade' id='tabs'>
    <h5>Custom Tabs</h5>
    <a href='{{ url_for('admin_tabs') }}' class='btn btn-sm btn-outline-primary mb-2'>Manage Tabs</a>
  </div>
</div>
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\admin.html"

# admin_tabs.html
@"
{% extends 'base.html' %}
{% block content %}
<h1 class='h4 mb-3'>Custom Tabs</h1>

<form method='post' class='mb-3'>
  <div class='row g-2'>
    <div class='col-md-6'>
      <input class='form-control' name='name' placeholder='Tab name'>
    </div>
    <div class='col-md-2'>
      <input class='form-control' name='order' placeholder='Order' value='0'>
    </div>
    <div class='col-md-4'>
      <button class='btn btn-primary w-100' type='submit'>Add Tab</button>
    </div>
  </div>
</form>

{% if tabs %}
  <table class='table table-sm'>
    <thead><tr><th>Name</th><th>Order</th><th>Fields</th><th>Actions</th></tr></thead>
    <tbody>
      {% for tab in tabs %}
        <tr>
          <td>{{ tab.name }}</td>
          <td>{{ tab.order }}</td>
          <td><a href='{{ url_for('admin_fields', tab_id=tab.id) }}' class='btn btn-sm btn-outline-secondary'>Fields</a></td>
          <td>
            <form method='post' action='{{ url_for('admin_tab_delete', tab_id=tab.id) }}'>
              <button class='btn btn-sm btn-outline-danger' type='submit'>Delete</button>
            </form>
          </td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
{% else %}
  <p class='text-muted'>No tabs yet.</p>
{% endif %}
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\admin_tabs.html"

# admin_fields.html
@"
{% extends 'base.html' %}
{% block content %}
<h1 class='h4 mb-3'>Fields for {{ tab.name }}</h1>

<form method='post' class='mb-3'>
  <div class='row g-2'>
    <div class='col-md-4'>
      <input class='form-control' name='label' placeholder='Field label'>
    </div>
    <div class='col-md-3'>
      <select class='form-select' name='field_type'>
        <option value='text'>Text</option>
        <option value='number'>Number</option>
        <option value='checkbox'>Checkbox</option>
        <option value='dropdown'>Dropdown</option>
      </select>
    </div>
    <div class='col-md-2'>
      <div class='form-check mt-2'>
        <input class='form-check-input' type='checkbox' name='required' id='required'>
        <label class='form-check-label' for='required'>Required</label>
      </div>
    </div>
    <div class='col-md-3'>
      <input class='form-control' name='options' placeholder='Options (comma-separated for dropdown)'>
    </div>
  </div>
  <button class='btn btn-primary mt-2' type='submit'>Add Field</button>
</form>

{% if tab.fields %}
  <table class='table table-sm'>
    <thead><tr><th>Label</th><th>Type</th><th>Required</th><th>Options</th><th>Actions</th></tr></thead>
    <tbody>
      {% for field in tab.fields %}
        <tr>
          <td>{{ field.label }}</td>
          <td>{{ field.field_type }}</td>
          <td>{{ 'Yes' if field.required else 'No' }}</td>
          <td>{{ field.options }}</td>
          <td>
            <form method='post' action='{{ url_for('admin_field_delete', field_id=field.id) }}'>
              <button class='btn btn-sm btn-outline-danger' type='submit'>Delete</button>
            </form>
          </td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
{% else %}
  <p class='text-muted'>No fields yet.</p>
{% endif %}
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\admin_fields.html"

# inventory.html
@"
{% extends 'base.html' %}
{% block content %}
<h1 class='h4 mb-3'>Inventory</h1>
{% if is_admin %}
  <a href='{{ url_for('inventory_new') }}' class='btn btn-primary mb-3'>New Item</a>
{% endif %}
<table class='table table-sm'>
  <thead><tr><th>Name</th><th>SKU</th><th>Barcode</th><th>Qty</th><th>Location</th><th>Actions</th></tr></thead>
  <tbody>
    {% for item in items %}
      <tr>
        <td>{{ item.name }}</td>
        <td>{{ item.sku }}</td>
        <td>{{ item.barcode }}</td>
        <td>{{ item.quantity }}</td>
        <td>{{ item.location }}</td>
        <td>
          {% if is_admin %}
            <a href='{{ url_for('inventory_edit', item_id=item.id) }}' class='btn btn-sm btn-outline-primary'>Edit</a>
            <form method='post' action='{{ url_for('inventory_delete', item_id=item.id) }}' class='d-inline'>
              <button class='btn btn-sm btn-outline-danger' type='submit'>Delete</button>
            </form>
          {% endif %}
        </td>
      </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\inventory.html"

# inventory_edit.html
@"
{% extends 'base.html' %}
{% block content %}
<h1 class='h4 mb-3'>{{ 'New' if not item else 'Edit' }} Inventory Item</h1>
<form method='post'>
  <div class='mb-3'><label class='form-label'>Name</label><input class='form-control' name='name' value='{{ item.name if item else "" }}'></div>
  <div class='mb-3'><label class='form-label'>SKU</label><input class='form-control' name='sku' value='{{ item.sku if item else "" }}'></div>
  <div class='mb-3'><label class='form-label'>Barcode</label><input class='form-control' name='barcode' value='{{ item.barcode if item else "" }}'></div>
  <div class='mb-3'><label class='form-label'>Quantity</label><input class='form-control' name='quantity' value='{{ item.quantity if item else 0 }}'></div>
  <div class='mb-3'><label class='form-label'>Location</label><input class='form-control' name='location' value='{{ item.location if item else "" }}'></div>
  <div class='mb-3'><label class='form-label'>Notes</label><input class='form-control' name='notes' value='{{ item.notes if item else "" }}'></div>
  <button class='btn btn-primary' type='submit'>Save</button>
</form>
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\inventory_edit.html"

# edit_job.html
@"
{% extends 'base.html' %}
{% block content %}
<h1 class='h4 mb-3'>Edit Job {{ job.job_number }}</h1>
<form method='post'>
  <div class='mb-3'><label class='form-label'>Job Number</label><input class='form-control' name='job_number' value='{{ job.job_number }}'></div>
  <div class='mb-3'><label class='form-label'>Title</label><input class='form-control' name='title' value='{{ job.title }}'></div>
  <div class='mb-3'><label class='form-label'>Client Name</label><input class='form-control' name='client_name' value='{{ job.client_name }}'></div>
  <div class='mb-3'><label class='form-label'>Address</label><input class='form-control' name='address' value='{{ job.address }}'></div>
  <div class='mb-3'><label class='form-label'>Service Type</label><input class='form-control' name='service_type' value='{{ job.service_type }}'></div>
  <div class='mb-3'>
    <label class='form-label'>Status</label>
    <select class='form-select' name='status'>
      <option value='open' {% if job.status == 'open' %}selected{% endif %}>Open</option>
      <option value='closed' {% if job.status == 'closed' %}selected{% endif %}>Closed</option>
      <option value='archived' {% if job.status == 'archived' %}selected{% endif %}>Archived</option>
    </select>
  </div>
  <button class='btn btn-primary' type='submit'>Save</button>
</form>
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\edit_job.html"

# view_job.html (extended with custom fields)
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
        <form method='post' action='{{ url_for('upload_photo', job_id=job.id) }}' enctype='multipart/form-data' class='mt-3'>
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
      <div class='card-header'>Contracts</div>
      <div class='card-body'>
        {% if contracts %}
          <ul class='list-group mb-3'>
            {% for c in contracts %}
              <li class='list-group-item d-flex justify-content-between align-items-center'>
                <span>Template #{{ c.template_id }} — {% if c.signed %}Signed{% else %}Pending{% endif %}</span>
                {% if not c.signed %}
                  <a href='{{ url_for('sign_contract', job_id=job.id, contract_id=c.id) }}' class='btn btn-sm btn-outline-success'>Sign</a>
                {% endif %}
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
{% endblock %}
"@ | Set-Content -Encoding UTF8 "templates\view_job.html"

Write-Host "Admin control update complete."
