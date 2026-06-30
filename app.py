# app.py - PCRRG SUPER-MEGA Field Operations Platform v2.5 FINAL COMPLETE

import os
import logging
import json
from datetime import datetime
from flask import (
    Flask, render_template, redirect, url_for,
    request, flash, jsonify, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
import smtplib
from email.message import EmailMessage
from werkzeug.utils import secure_filename

# -------------------------------------------------------------------------
# BASE CONFIG + LOGGING
# -------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')

data_dir = os.path.join(BASE_DIR, 'data')
os.makedirs(data_dir, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(data_dir, 'pcrrg_fieldops_v2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

STATIC_DIR = os.path.join(BASE_DIR, 'static')
UPLOAD_ROOT = os.path.join(STATIC_DIR, 'uploads')
PHOTOS_FOLDER = os.path.join(UPLOAD_ROOT, 'photos')
PACKOUT_FOLDER = os.path.join(UPLOAD_ROOT, 'packouts')
CONTRACTS_FOLDER = os.path.join(UPLOAD_ROOT, 'contracts')
ARCHIVE_FOLDER = os.path.join(data_dir, 'archive')

for p in (UPLOAD_ROOT, PHOTOS_FOLDER, PACKOUT_FOLDER, CONTRACTS_FOLDER, ARCHIVE_FOLDER):
    os.makedirs(p, exist_ok=True)

app.config['UPLOAD_FOLDER_PHOTOS'] = PHOTOS_FOLDER
app.config['UPLOAD_FOLDER_PACKOUT'] = PACKOUT_FOLDER
app.config['UPLOAD_FOLDER_CONTRACTS'] = CONTRACTS_FOLDER
app.config['ARCHIVE_FOLDER'] = ARCHIVE_FOLDER

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("Starting PCRRG SUPER-MEGA app.py")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# -------------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT


def save_upload(fileobj, folder):
    filename = secure_filename(fileobj.filename)
    timestamp = int(datetime.utcnow().timestamp())
    filename = f"{timestamp}_{filename}"
    abs_path = os.path.join(folder, filename)
    fileobj.save(abs_path)
    rel_path = os.path.relpath(abs_path, STATIC_DIR)
    return rel_path.replace('\\', '/'), abs_path


def attach_files_to_email(msg: EmailMessage, file_paths):
    for p in file_paths:
        try:
            with open(p, 'rb') as f:
                data = f.read()
            subtype = p.rsplit('.', 1)[1].lower() if '.' in p else 'octet-stream'
            msg.add_attachment(
                data,
                maintype='image',
                subtype=subtype,
                filename=os.path.basename(p)
            )
        except Exception:
            logger.exception("Failed to attach file %s", p)


def send_job_email(job, to_email, subject, body):
    # Simple SMTP stub – assumes environment variables for SMTP
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')

    if not smtp_host or not smtp_user or not smtp_pass:
        logger.warning("SMTP not configured; skipping email send.")
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info("Job email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send job email to %s", to_email)

# -------------------------------------------------------------------------
# MODELS
# -------------------------------------------------------------------------
class ThemeSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    primary_color = db.Column(db.String(32), default="#1E88E5")
    secondary_color = db.Column(db.String(32), default="#FFC107")
    logo_url = db.Column(db.String(255), default="/static/logo.png")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    pin = db.Column(db.String(16), nullable=False)
    name = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255))
    role = db.Column(db.String(50), default='tech')

    def is_admin(self):
        return self.role == 'admin'


class CustomTab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    order = db.Column(db.Integer, default=0)


class CustomField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tab_id = db.Column(db.Integer, db.ForeignKey('custom_tab.id'), nullable=True)
    label = db.Column(db.String(255), nullable=False)
    field_type = db.Column(db.String(50), nullable=False)
    required = db.Column(db.Boolean, default=False)
    options = db.Column(db.String(255))
    tab = db.relationship('CustomTab', backref=db.backref('fields', lazy='dynamic'))


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    client_name = db.Column(db.String(255))
    address = db.Column(db.String(255))
    status = db.Column(db.String(50), default='open')
    service_type = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    photos = db.relationship('JobPhoto', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    packout_items = db.relationship('PackoutItem', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    contracts = db.relationship('JobContract', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('JobTask', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    custom_values = db.relationship('JobCustomValue', backref='job', lazy='dynamic', cascade='all, delete-orphan')


class JobPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    filename = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(255))
    location_label = db.Column(db.String(255))
    before_after = db.Column(db.String(16))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)


class PackoutItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    location = db.Column(db.String(255))
    notes = db.Column(db.Text)
    condition = db.Column(db.String(50))
    photos = db.relationship('PackoutPhoto', backref='item', lazy='dynamic', cascade='all, delete-orphan')


class PackoutPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('packout_item.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


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
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    template = db.relationship('ContractTemplate', backref=db.backref('contracts', lazy='dynamic'))


class JobTaskTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    service_type = db.Column(db.String(128))


class JobTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('job_task_template.id'))
    label = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    template = db.relationship('JobTaskTemplate', backref=db.backref('tasks', lazy='dynamic'))
    completed_by = db.relationship('User')


class JobCustomValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('custom_field.id'), nullable=False)
    value = db.Column(db.String(255))
    field = db.relationship('CustomField', backref=db.backref('values', lazy='dynamic'))


class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(128))
    barcode = db.Column(db.String(128))
    quantity = db.Column(db.Integer, default=0)
    location = db.Column(db.String(255))
    notes = db.Column(db.Text)


class EmployeeSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    clock_in_at = db.Column(db.DateTime, default=datetime.utcnow)
    clock_out_at = db.Column(db.DateTime)
    clock_in_lat = db.Column(db.Float)
    clock_in_lon = db.Column(db.Float)
    clock_out_lat = db.Column(db.Float)
    clock_out_lon = db.Column(db.Float)
    notes = db.Column(db.Text)

# -------------------------------------------------------------------------
# BOOTSTRAP
# -------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def is_admin():
    return current_user.is_authenticated and getattr(current_user, 'role', '') == 'admin'


@app.context_processor
def inject_globals():
    theme = ThemeSettings.query.first()
    return {'is_admin': is_admin(), 'current_user': current_user, 'theme': theme}

# -------------------------------------------------------------------------

from urllib.parse import urlparse, urljoin

def safe_redirect_target(target):
    """Prevents Android/PWA redirect loops by validating next= URLs."""
    if not target:
        return None
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    if redirect_url.scheme in ("http", "https") and host_url.netloc == redirect_url.netloc:
        return redirect_url.path
    return None

# AUTH + DASHBOARD
# -------------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        pin = request.form.get('pin')
        user = User.query.filter_by(username=username, pin=pin).first()
        if user:
            login_user(user)
            flash('Logged in.')
            next_url = request.args.get('next')
            next_url = safe_redirect_target(next_url)
            protected = ('/jobs', '/admin', '/packout', '/contracts')
            if not next_url or next_url.startswith(protected):
                next_url = url_for('dashboard')
            return redirect(next_url)
        else:
            flash('Invalid credentials.')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    jobs_open = Job.query.filter_by(status='open').count()
    jobs_closed = Job.query.filter_by(status='closed').count()
    jobs_archived = Job.query.filter_by(status='archived').count()
    inventory_count = InventoryItem.query.count()
    contracts_pending = JobContract.query.filter_by(signed=False).count()
    recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(10).all()
    active_sessions = EmployeeSession.query.filter(EmployeeSession.clock_out_at.is_(None)).all()
    return render_template(
        'dashboard.html',
        jobs_open=jobs_open,
        jobs_closed=jobs_closed,
        jobs_archived=jobs_archived,
        inventory_count=inventory_count,
        contracts_pending=contracts_pending,
        recent_jobs=recent_jobs,
        active_sessions=active_sessions
    )

# -------------------------------------------------------------------------
# EMPLOYEE CLOCK
# -------------------------------------------------------------------------
@app.route('/employee/clock-in', methods=['POST'])
@login_required
def employee_clock_in():
    session = EmployeeSession(user_id=current_user.id, job_id=None, clock_in_at=datetime.utcnow())
    db.session.add(session)
    db.session.commit()
    flash('Clocked in.')
    return redirect(url_for('dashboard'))


@app.route('/employee/clock-out', methods=['POST'])
@login_required
def employee_clock_out():
    session = EmployeeSession.query.filter_by(user_id=current_user.id, clock_out_at=None).first()
    if session:
        session.clock_out_at = datetime.utcnow()
        db.session.commit()
        flash('Clocked out.')
    else:
        flash('No active session.')
    return redirect(url_for('dashboard'))

# -------------------------------------------------------------------------
# ADMIN HOME + THEME + USERS + TABS
# -------------------------------------------------------------------------


@app.route('/admin')
@login_required
def admin_home():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    jobs = Job.query.order_by(Job.created_at.desc()).limit(10).all()
    inventory_items = InventoryItem.query.order_by(InventoryItem.name).limit(10).all()
    tabs = CustomTab.query.order_by(CustomTab.order).all()
    theme = ThemeSettings.query.first()
    task_templates = JobTaskTemplate.query.order_by(JobTaskTemplate.name).all()
    active_sessions = EmployeeSession.query.filter(EmployeeSession.clock_out_at.is_(None)).all()

    return render_template(
        'admin.html',
        jobs=jobs,
        inventory_items=inventory_items,
        tabs=tabs,
        theme=theme,
        task_templates=task_templates,
        active_sessions=active_sessions
    )




@app.route('/admin/theme', methods=['POST'])
@login_required
def admin_theme_update():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    primary = request.form.get('primary_color')
    secondary = request.form.get('secondary_color')
    logo = request.form.get('logo_url')

    theme = ThemeSettings.query.first()
    if not theme:
        theme = ThemeSettings()
        db.session.add(theme)

    if primary:
        theme.primary_color = primary
    if secondary:
        theme.secondary_color = secondary
    if logo:
        theme.logo_url = logo

    db.session.commit()
    flash('Theme updated.')
    return redirect(url_for('admin_home'))


@app.route('/admin/users')
@login_required
def admin_users():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    users = User.query.order_by(User.username).all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/new', methods=['GET', 'POST'])
@login_required
def admin_users_new():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        pin = request.form.get('pin')
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        role = request.form.get('role') or 'tech'

        if not username or not pin:
            flash('Username and PIN are required.')
            return redirect(url_for('admin_users_new'))

        existing = User.query.filter_by(username=username).first()
        if existing:
            flash('Username already exists.')
            return redirect(url_for('admin_users_new'))

        user = User(
            username=username,
            pin=pin,
            name=name,
            phone=phone,
            email=email,
            role=role
        )
        db.session.add(user)
        db.session.commit()
        flash('User created.')
        return redirect(url_for('admin_users'))

    return render_template('admin_users_edit.html', user=None)


@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_users_edit(user_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.username = request.form.get('username') or user.username
        user.pin = request.form.get('pin') or user.pin
        user.name = request.form.get('name')
        user.phone = request.form.get('phone')
        user.email = request.form.get('email')
        user.role = request.form.get('role') or user.role

        db.session.commit()
        flash('User updated.')
        return redirect(url_for('admin_users'))

    return render_template('admin_users_edit.html', user=user)


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_users_delete(user_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    if user.username == 'admin':
        flash('Cannot delete default admin.')
        return redirect(url_for('admin_users'))

    db.session.delete(user)
    db.session.commit()
    flash('User deleted.')
    return redirect(url_for('admin_users'))


@app.route('/admin/tabs', methods=['GET', 'POST'])
@login_required
def admin_tabs():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        order = request.form.get('order') or 0

        if not name:
            flash('Tab name is required.')
            return redirect(url_for('admin_tabs'))

        tab = CustomTab(name=name, order=int(order))
        db.session.add(tab)
        db.session.commit()
        flash('Tab created.')
        return redirect(url_for('admin_tabs'))

    tabs = CustomTab.query.order_by(CustomTab.order).all()
    return render_template('admin_tabs.html', tabs=tabs)


@app.route('/admin/tabs/<int:tab_id>/delete', methods=['POST'])
@login_required
def admin_tabs_delete(tab_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    tab = CustomTab.query.get_or_404(tab_id)
    db.session.delete(tab)
    db.session.commit()
    flash('Tab deleted.')
    return redirect(url_for('admin_tabs'))

# -------------------------------------------------------------------------
# TIMELINE
# -------------------------------------------------------------------------
@app.route('/jobs/<int:job_id>/timeline')
@login_required
def job_timeline(job_id):
    job = Job.query.get_or_404(job_id)
    events = []

    for p in job.photos.order_by(JobPhoto.uploaded_at.desc()).all():
        events.append({
            'type': 'photo',
            'timestamp': p.uploaded_at,
            'label': f'Photo: {p.category or "Uncategorized"}',
            'meta': {
                'filename': p.filename,
                'lat': p.latitude,
                'lon': p.longitude,
                'user': p.user_id
            }
        })

    for i in job.packout_items.order_by(PackoutItem.id.desc()).all():
        events.append({
            'type': 'packout',
            'timestamp': job.created_at,
            'label': f'Packout: {i.name} x{i.quantity}',
            'meta': {
                'location': i.location,
                'notes': i.notes
            }
        })

    for c in job.contracts.order_by(JobContract.signed_at.desc()).all():
        events.append({
            'type': 'contract',
            'timestamp': c.signed_at or job.created_at,
            'label': f'Contract: {"Signed" if c.signed else "Pending"}',
            'meta': {
                'signer': c.signer_name,
                'email': c.signer_email,
                'lat': c.latitude,
                'lon': c.longitude
            }
        })

    for t in job.tasks.order_by(JobTask.id.desc()).all():
        events.append({
            'type': 'task',
            'timestamp': t.completed_at or job.created_at,
            'label': f'Task: {t.label} {"(Done)" if t.completed else "(Pending)"}',
            'meta': {
                'completed_by': t.completed_by_id
            }
        })

    events.sort(key=lambda e: e['timestamp'] or job.created_at, reverse=True)
    return render_template('timeline.html', job=job, events=events)

# -------------------------------------------------------------------------
# JOB VIEW + MAP DATA
# -------------------------------------------------------------------------
@app.route('/jobs/<int:job_id>')
@login_required
def view_job(job_id):
    job = Job.query.get_or_404(job_id)
    photos = job.photos.all()
    packout_items = job.packout_items.all()
    contracts = job.contracts.all()
    templates = ContractTemplate.query.all()
    tabs = CustomTab.query.order_by(CustomTab.order).all()
    tasks = job.tasks.order_by(JobTask.id).all()

    # FIX: load checklist templates
    task_templates = JobTaskTemplate.query.order_by(JobTaskTemplate.name.asc()).all()

    values_map = {v.field_id: v.value for v in job.custom_values}

    return render_template(

        'view_job.html',
        job=job,
        photos=photos,
        packout_items=packout_items,
        contracts=contracts,
        templates=templates,
        tabs=tabs,
        values_map=values_map,
        tasks=tasks,
        task_templates=task_templates
    )


@app.route('/jobs/<int:job_id>/report-builder')
@login_required
def report_builder(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template(
        'report_builder.html',
        job=job,
        JobPhoto=JobPhoto
    )


@app.route('/jobs/<int:job_id>/export/companycam', methods=['POST'])
@login_required
def export_job_companycam(job_id):
    import io, os, csv, zipfile
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import landscape, letter

    job = Job.query.get_or_404(job_id)
    data = request.get_json() or {}
    selected_ids = data.get("photos") or []
    layout = int(data.get("layout") or 4)
    metadata = data.get("metadata") or []

    # Resolve photos
    if selected_ids:
        photos = JobPhoto.query.filter(JobPhoto.id.in_(selected_ids)).order_by(JobPhoto.uploaded_at.asc()).all()
    else:
        photos = job.photos.order_by(JobPhoto.uploaded_at.asc()).all()

    packout_items = job.packout_items.order_by(PackoutItem.id.asc()).all()
    contracts = job.contracts.order_by(JobContract.id.asc()).all()
    tasks = job.tasks.order_by(JobTask.id.asc()).all()

    # Prepare export directory
    export_root = os.path.join(app.config['ARCHIVE_FOLDER'], 'companycam')
    os.makedirs(export_root, exist_ok=True)
    pdf_filename = f"job_{job.id}_companycam_report.pdf"
    pdf_path = os.path.join(export_root, pdf_filename)

    # Build PDF (landscape, Encircle-style summaries + CompanyCam-style grids)
    pdf = canvas.Canvas(pdf_path, pagesize=landscape(letter))

    # Page 1 — Job Summary
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(50, 550, f"Job Report — {job.job_number}")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 520, f"Title: {job.title}")
    pdf.drawString(50, 500, f"Client: {job.client_name or ''}")
    pdf.drawString(50, 480, f"Address: {job.address or ''}")
    pdf.drawString(50, 460, f"Service: {job.service_type or ''}")
    pdf.drawString(50, 440, f"Status: {job.status}")
    pdf.showPage()

    # Page 2 — Task Summary
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 550, "Task Summary")
    pdf.setFont("Helvetica", 11)
    y = 520
    for t in tasks:
        status = "Done" if t.completed else "Pending"
        pdf.drawString(50, y, f"{t.label} — {status}")
        y -= 18
        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica-Bold", 18)
            pdf.drawString(50, 550, "Task Summary (cont.)")
            pdf.setFont("Helvetica", 11)
            y = 520
    pdf.showPage()

    # Page 3 — Packout Summary
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 550, "Packout Summary")
    pdf.setFont("Helvetica", 11)
    y = 520
    for item in packout_items:
        pdf.drawString(50, y, f"{item.name} x{item.quantity} @ {item.location or ''} ({item.condition or ''})")
        y -= 18
        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica-Bold", 18)
            pdf.drawString(50, 550, "Packout Summary (cont.)")
            pdf.setFont("Helvetica", 11)
            y = 520
    pdf.showPage()

    # Page 4 — Contracts Summary
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 550, "Contracts Summary")
    pdf.setFont("Helvetica", 11)
    y = 520
    for c in contracts:
        status = "Signed" if c.signed else "Pending"
        pdf.drawString(50, y, f"Template #{c.template_id} — {status} — {c.signer_name or ''}")
        y -= 18
        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica-Bold", 18)
            pdf.drawString(50, 550, "Contracts Summary (cont.)")
            pdf.setFont("Helvetica", 11)
            y = 520
    pdf.showPage()

    # Photo pages — CompanyCam-style grid (thumbnails)
    per_row = max(2, min(layout, 4))
    per_page = per_row * 2
    index = 0
    thumb_size = 150

    while index < len(photos):
        chunk = photos[index:index+per_page]
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, 550, "Photo Evidence")
        x_start = 50
        y_start = 500

        for i, p in enumerate(chunk):
            row = i // per_row
            col = i % per_row
            x = x_start + col * (thumb_size + 20)
            y = y_start - row * (thumb_size + 60)

            # Resolve absolute path from STATIC_DIR + relative filename
            rel = p.filename.replace("\\", "/").replace("\\", "/")
            abs_path = os.path.join(STATIC_DIR, rel)
            try:
                pdf.drawImage(abs_path, x, y, width=thumb_size, height=thumb_size, preserveAspectRatio=True, anchor='c')
            except Exception:
                pdf.setFont("Helvetica", 8)
                pdf.drawString(x, y + thumb_size/2, "[Image missing]")

            meta_y = y - 12
            pdf.setFont("Helvetica", 8)
            line = []
            if "numbers" in metadata:
                line.append(f"#{p.id}")
            if "captured_by" in metadata and p.user_id:
                line.append(f"User {p.user_id}")
            if "location" in metadata and p.location_label:
                line.append(p.location_label)
            if "date" in metadata and p.uploaded_at:
                line.append(p.uploaded_at.strftime("%Y-%m-%d %H:%M"))
            if "tags" in metadata and p.category:
                line.append(p.category)
            if line:
                pdf.drawString(x, meta_y, " | ".join(line))

        pdf.showPage()
        index += per_page

    pdf.save()

    # Build ZIP package: PDF + full-res photos + packout CSV + contracts metadata
    zip_buffer = io.BytesIO()
    z = zipfile.ZipFile(zip_buffer, "w")

    # Add PDF
    with open(pdf_path, "rb") as fpdf:
        z.writestr(pdf_filename, fpdf.read())

    # Add photos (full resolution)
    for p in photos:
        rel = p.filename.replace("\\", "/").replace("\\", "/")
        abs_path = os.path.join(STATIC_DIR, rel)
        if os.path.exists(abs_path):
            with open(abs_path, "rb") as fimg:
                z.writestr(f"photos/{os.path.basename(rel)}", fimg.read())

    # Add packout CSV
    csv_io = io.StringIO()
    writer = csv.writer(csv_io)
    writer.writerow(["Name","Quantity","Location","Condition","Notes"])
    for item in packout_items:
        writer.writerow([
            item.name,
            item.quantity,
            item.location or "",
            item.condition or "",
            item.notes or "",
        ])
    z.writestr("packout.csv", csv_io.getvalue())

    # Add contracts metadata JSON
    import json as _json
    contracts_data = []
    for c in contracts:
        contracts_data.append({
            "template_id": c.template_id,
            "signed": bool(c.signed),
            "signed_at": c.signed_at.isoformat() if c.signed_at else None,
            "signer_name": c.signer_name,
            "signer_email": c.signer_email,
            "latitude": c.latitude,
            "longitude": c.longitude,
        })
    z.writestr("contracts.json", _json.dumps(contracts_data, indent=2))

    z.close()
    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"job_{job.id}_companycam_report.zip"
    )
@app.route('/jobs/<int:job_id>/map-data')
@login_required
def job_map_data(job_id):
    job = Job.query.get_or_404(job_id)

    photo_points = []
    for p in job.photos.all():
        if p.latitude is not None and p.longitude is not None:
            photo_points.append({
                'lat': p.latitude,
                'lon': p.longitude,
                'label': f'Photo: {p.category or "Uncategorized"}',
                'filename': p.filename
            })

    contract_points = []
    for c in job.contracts.all():
        if c.latitude is not None and c.longitude is not None:
            contract_points.append({
                'lat': c.latitude,
                'lon': c.longitude,
                'label': f'Contract: {"Signed" if c.signed else "Pending"}',
                'signer': c.signer_name
            })

    return jsonify({
        'job': {
            'id': job.id,
            'title': job.title,
            'address': job.address
        },
        'photos': photo_points,
        'contracts': contract_points
    })

# -------------------------------------------------------------------------
# JOB CRUD
# -------------------------------------------------------------------------
@app.route('/jobs/new', methods=['GET', 'POST'])
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

        # AUTO‑ATTACH TASKS BASED ON JOB TYPE
        templates = JobTaskTemplate.query.filter_by(service_type=job.service_type).all()
        for tmpl in templates:
            task = JobTask(
                job_id=job.id,
                template_id=tmpl.id,
                label=tmpl.name
            )
            db.session.add(task)
        db.session.commit()

        # AUTO‑ATTACH TASKS BASED ON JOB TYPE
        templates = JobTaskTemplate.query.filter_by(service_type=job.service_type).all()
        for tmpl in templates:
            task = JobTask(
                job_id=job.id,
                template_id=tmpl.id,
                label=tmpl.name
            )
            db.session.add(task)
        db.session.commit()

        flash('Job created.')
        return redirect(url_for('view_job', job_id=job.id))

    return render_template('new_job.html')


@app.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
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

# -------------------------------------------------------------------------
# JOB TASK TEMPLATES + TASKS
# -------------------------------------------------------------------------


@app.route('/admin/checklists/import', methods=['GET', 'POST'])
@login_required
def import_checklist():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        file = request.files.get('file')
        name = request.form.get('name') or 'Imported Checklist'
        service_type = request.form.get('service_type')

        if not file or file.filename == '':
            flash('No file selected.')
            return redirect(url_for('import_checklist'))

        # Save uploaded file
        import_dir = os.path.join(app.config['ARCHIVE_FOLDER'], 'imported_docs')
        os.makedirs(import_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        abs_path = os.path.join(import_dir, filename)
        file.save(abs_path)

        # Extract steps
        steps = []
        ext = filename.lower().split('.')[-1]

        if ext == 'txt':
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as ftxt:
                steps = [line.strip() for line in ftxt if line.strip()]

        elif ext == 'docx':
            try:
                from docx import Document
                doc = Document(abs_path)
                for p in doc.paragraphs:
                    if p.text.strip():
                        steps.append(p.text.strip())
            except:
                steps = []

        elif ext == 'pdf':
            try:
                import PyPDF2
                with open(abs_path, 'rb') as fpdf:
                    reader = PyPDF2.PdfReader(fpdf)
                    for page in reader.pages:
                        text = page.extract_text() or ""
                        for line in text.splitlines():
                            if line.strip():
                                steps.append(line.strip())
            except:
                steps = []

        # Create template
        tmpl = JobTaskTemplate(
            name=name,
            description=json.dumps(steps),
            service_type=service_type
        )
        db.session.add(tmpl)
        db.session.commit()

        flash('Checklist imported successfully.')
        return redirect(url_for('admin_checklists'))

    return render_template('admin_checklist_import.html')


@app.route('/admin/checklists', methods=['GET', 'POST'])
@login_required
def admin_checklists():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        steps_raw = request.form.get('steps') or ""
        steps = [s.strip() for s in steps_raw.splitlines() if s.strip()]

        tmpl = JobTaskTemplate(
            name=name,
            description=json.dumps(steps),
            service_type=request.form.get('service_type')
        )
        db.session.add(tmpl)
        db.session.commit()
        flash('Checklist created.')
        return redirect(url_for('admin_checklists'))

    templates = JobTaskTemplate.query.order_by(JobTaskTemplate.name).all()
    return render_template('admin_checklists.html', templates=templates)


@app.route('/admin/task-templates', methods=['GET', 'POST'])
@login_required
def admin_task_templates():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        service_type = request.form.get('service_type')
        tmpl = JobTaskTemplate(
            name=name,
            description=description,
            service_type=service_type
        )
        db.session.add(tmpl)
        db.session.commit()
        flash('Task template created.')
        return redirect(url_for('admin_task_templates'))

    templates = JobTaskTemplate.query.order_by(JobTaskTemplate.name).all()
    return render_template('admin_task_templates.html', templates=templates)



@app.route('/jobs/<int:job_id>/attach_checklist', methods=['POST'])
@login_required
def attach_checklist(job_id):
    job = Job.query.get_or_404(job_id)
    tmpl_id = int(request.form.get('template_id'))
    tmpl = JobTaskTemplate.query.get_or_404(tmpl_id)

    try:
        steps = json.loads(tmpl.description or "[]")
    except:
        steps = []

    for step in steps:
        task = JobTask(
            job_id=job.id,
            template_id=tmpl.id,
            label=step
        )
        db.session.add(task)

    db.session.commit()
    flash('Checklist attached.')
    return redirect(url_for('view_job', job_id=job.id))


@app.route('/jobs/<int:job_id>/tasks/add', methods=['POST'])
@login_required
def add_job_task(job_id):
    job = Job.query.get_or_404(job_id)
    template_id = request.form.get('template_id')
    label = request.form.get('label')

    if template_id:
        tmpl = JobTaskTemplate.query.get(int(template_id))
        label = label or (tmpl.name if tmpl else label)

    task = JobTask(
        job_id=job.id,
        template_id=int(template_id) if template_id else None,
        label=label or 'Task'
    )
    db.session.add(task)
    db.session.commit()
    flash('Task added to job.')
    return redirect(url_for('view_job', job_id=job.id))



@app.route('/jobs/<int:job_id>/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_job_task(job_id, task_id):
    job = Job.query.get_or_404(job_id)
    task = JobTask.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.')
    return redirect(url_for('view_job', job_id=job.id))


@app.route('/jobs/<int:job_id>/tasks/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_job_task(job_id, task_id):
    job = Job.query.get_or_404(job_id)
    task = JobTask.query.get_or_404(task_id)

    if task.completed:
        task.completed = False
        task.completed_at = None
        task.completed_by_id = None
    else:
        task.completed = True
        task.completed_at = datetime.utcnow()
        task.completed_by_id = current_user.id

    db.session.commit()
    flash('Task status updated.')
    return redirect(url_for('view_job', job_id=job.id))

# -------------------------------------------------------------------------
# PHOTO UPLOAD
# -------------------------------------------------------------------------
@app.route('/jobs/<int:job_id>/upload_photo', methods=['POST'])
@login_required
def upload_photo(job_id):
    job = Job.query.get_or_404(job_id)
    file = request.files.get('photo')

    if not file or file.filename == '':
        flash('No file selected.')
        return redirect(url_for('view_job', job_id=job.id))

    os.makedirs(app.config['UPLOAD_FOLDER_PHOTOS'], exist_ok=True)

    filename = f"{job.id}_{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
    path = os.path.join(app.config['UPLOAD_FOLDER_PHOTOS'], filename)
    file.save(path)

    lat = request.form.get('lat')
    lon = request.form.get('lon')

    photo = JobPhoto(
        job_id=job.id,
        user_id=current_user.id,
        filename=os.path.join('uploads', 'photos', filename).replace('\\', '/'),
        category=request.form.get('category'),
        latitude=float(lat) if lat else None,
        longitude=float(lon) if lon else None
    )

    db.session.add(photo)
    db.session.commit()

    flash('Photo uploaded.')
    return redirect(url_for('view_job', job_id=job.id))

# -------------------------------------------------------------------------
# PACKOUT
# -------------------------------------------------------------------------
@app.route('/jobs/<int:job_id>/packout/add', methods=['POST'])
@login_required
def add_packout_item(job_id):
    job = Job.query.get_or_404(job_id)

    name = request.form.get('name')
    if not name:
        flash('Item name required.')
        return redirect(url_for('view_job', job_id=job.id))

    item = PackoutItem(
        job_id=job.id,
        name=name,
        quantity=int(request.form.get('quantity') or 1),
        location=request.form.get('location'),
        notes=request.form.get('notes'),
        condition=request.form.get('condition')
    )
    db.session.add(item)
    db.session.commit()

    files = request.files.getlist('packout_photo')
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            rel, _ = save_upload(file, app.config['UPLOAD_FOLDER_PACKOUT'])
            pp = PackoutPhoto(
                item_id=item.id,
                filename=os.path.join('uploads', rel).replace('\\', '/')
            )
            db.session.add(pp)
    db.session.commit()

    flash('Packout item with photos added.')
    return redirect(url_for('view_job', job_id=job.id))


@app.route('/jobs/<int:job_id>/packout')
@login_required
def packout(job_id):
    job = Job.query.get_or_404(job_id)
    items = job.packout_items.all()
    return render_template('packout_items.html', job=job, items=items)


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

# -------------------------------------------------------------------------
# INVENTORY
# -------------------------------------------------------------------------
@app.route('/inventory')
@login_required
def inventory_list():
    items = InventoryItem.query.order_by(InventoryItem.name).all()
    return render_template('inventory.html', items=items)


@app.route('/inventory/new', methods=['GET', 'POST'])
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


@app.route('/inventory/<int:item_id>/edit', methods=['GET', 'POST'])
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

# -------------------------------------------------------------------------
# CONTRACTS + E-SIGN
# -------------------------------------------------------------------------

@app.route('/contracts/<int:contract_id>/view')
@login_required
def view_contract_doc(contract_id):
    contract = JobContract.query.get_or_404(contract_id)
    tmpl = contract.template
    if not tmpl or not tmpl.filename:
        flash('No contract file available.')
        return redirect(url_for('view_job', job_id=contract.job_id))
    return send_from_directory(CONTRACTS_FOLDER, tmpl.filename, as_attachment=False)


@app.route('/contracts/templates', methods=['GET', 'POST'])
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
            filename = f"{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
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


@app.route('/jobs/<int:job_id>/contracts/<int:contract_id>/sign', methods=['GET', 'POST'])

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

        signer_lat = request.form.get('lat')
        signer_lon = request.form.get('lon')
        jc.latitude = float(signer_lat) if signer_lat else None
        jc.longitude = float(signer_lon) if signer_lon else None

        sig_data = request.form.get('signature_data')
        try:
            if sig_data and ',' in sig_data:
                import base64
                sig_bytes = base64.b64decode(sig_data.split(',')[1])
                # Ensure folder exists; if config missing, fall back to /static/contracts
                upload_root = getattr(app.config, 'UPLOAD_FOLDER_CONTRACTS', os.path.join(STATIC_DIR, 'uploads', 'contracts'))
                os.makedirs(upload_root, exist_ok=True)
                sig_filename = f"signature_{job.id}_{contract_id}_{int(datetime.utcnow().timestamp())}.png"
                sig_path = os.path.join(upload_root, sig_filename)
                with open(sig_path, 'wb') as sig_file:
                    sig_file.write(sig_bytes)
                # Only assign if model has this attribute
                if hasattr(jc, 'signature_file'):
                    jc.signature_file = sig_filename
        except Exception as e:
            # Do not crash the app; just log and continue
            app.logger.error(f"Signature save failed: {e}")

        db.session.commit()
        flash('Contract signed.')
        return redirect(url_for('view_job', job_id=job.id))

    return render_template('sign_contract.html', job=job, contract=jc)



# -------------------------------------------------------------------------
# SHARE + ARCHIVE
# -------------------------------------------------------------------------
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
        body_lines.append(
            f"- {item.name} x{item.quantity} @ {item.location} ({item.notes})"
        )

    body_lines.append("")
    body_lines.append("Contracts:")

    for c in contracts:
        status = "Signed" if c.signed else "Pending"
        body_lines.append(f"- Template #{c.template_id} [{status}]")

    body = "\\n".join(body_lines)
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
            {
                'filename': p.filename,
                'category': p.category,
                'uploaded_at': p.uploaded_at.isoformat() if p.uploaded_at else None,
                'latitude': p.latitude,
                'longitude': p.longitude
            }
            for p in job.photos.all()
        ],
        'packout_items': [
            {
                'name': i.name,
                'quantity': i.quantity,
                'location': i.location,
                'notes': i.notes
            }
            for i in job.packout_items.all()
        ],
        'contracts': [
            {
                'template_id': c.template_id,
                'signed': c.signed,
                'signed_at': c.signed_at.isoformat() if c.signed_at else None,
                'signer_name': c.signer_name,
                'signer_email': c.signer_email,
                'latitude': c.latitude,
                'longitude': c.longitude
            }
            for c in job.contracts.all()
        ],
        'tasks': [
            {
                'label': t.label,
                'completed': t.completed,
                'completed_at': t.completed_at.isoformat() if t.completed_at else None,
                'completed_by_id': t.completed_by_id
            }
            for t in job.tasks.all()
        ]
    }

    with open(archive_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    job.status = 'archived'
    db.session.commit()
    flash('Job archived and exported.')
    return redirect(url_for('view_job', job_id=job.id))

# -------------------------------------------------------------------------
# STATIC UPLOADS
# -------------------------------------------------------------------------
@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_ROOT, filename)

# -------------------------------------------------------------------------
# SUPER-MEGA BOOTSTRAP
# -------------------------------------------------------------------------
def supermega_bootstrap():
    logger.info("Running SUPER-MEGA DB bootstrap...")
    os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_PHOTOS'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_CONTRACTS'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_PACKOUT'], exist_ok=True)
    os.makedirs(app.config['ARCHIVE_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()
        logger.info("DB tables created/verified.")

        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                pin='1234',
                name='Admin',
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            logger.info("Default admin user created (admin / 1234).")
        else:
            logger.info("Admin user already exists.")


supermega_bootstrap()
logger.info("SUPER-MEGA app bootstrap complete.")

# -------------------------------------------------------------------------
# BLUEPRINTS
# -------------------------------------------------------------------------
from extensions.advanced_admin import advanced_admin_bp
app.register_blueprint(advanced_admin_bp)

from plus import plus_bp
app.register_blueprint(plus_bp, url_prefix='/plus')

from theme_engine import theme_bp
app.register_blueprint(theme_bp, url_prefix='/theme')

from theme_engine.routes import load_theme


@app.context_processor
def inject_theme():
    try:
        return {"t": load_theme()}
    except Exception:
        return {"t": {}}

from routes_templates import templates_bp
app.register_blueprint(templates_bp)

# -------------------------------------------------------------------------
# WSGI ENTRYPOINT
# -------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5000')))

# -------------------------------------------------------------------------
# JOB REPORT PDF
# -------------------------------------------------------------------------

@app.route('/jobs/<int:job_id>/export/zip')
@login_required
def export_job_zip(job_id):
    job = Job.query.get_or_404(job_id)
    from export_zip import build_zip_package

    export_dir = os.path.join(app.config['ARCHIVE_FOLDER'], 'exports')
    os.makedirs(export_dir, exist_ok=True)

    filename = f"job_{job.id}_package.zip"
    path = os.path.join(export_dir, filename)

    build_zip_package(job, path)

    return send_from_directory(export_dir, filename, as_attachment=True)

@app.route('/jobs/<int:job_id>/export/pdf')
@login_required
def export_job_pdf(job_id):
    job = Job.query.get_or_404(job_id)
    from export_pdf import build_full_pdf

    export_dir = os.path.join(app.config['ARCHIVE_FOLDER'], 'exports')
    os.makedirs(export_dir, exist_ok=True)

    filename = f"job_{job.id}_full_report.pdf"
    path = os.path.join(export_dir, filename)

    build_full_pdf(job, path)

    return send_from_directory(export_dir, filename, as_attachment=True)


@app.route('/jobs/<int:job_id>/report.pdf')
@login_required
def job_report_pdf(job_id):
    job = Job.query.get_or_404(job_id)
    from job_report import generate_job_pdf
    reports_dir = os.path.join(app.config['ARCHIVE_FOLDER'], 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    filename = f"job_{job.id}_report.pdf"
    path = os.path.join(reports_dir, filename)
    generate_job_pdf(job, path)
    return send_from_directory(reports_dir, filename, as_attachment=True)


@app.route('/jobs/<int:job_id>/attach-checklist', methods=['POST'])
@login_required
def attach_checklist_to_job(job_id):
    job = Job.query.get_or_404(job_id)
    checklist_id = request.form.get('checklist_id')
    tmpl = JobTaskTemplate.query.get_or_404(checklist_id)

    import json
    steps = []
    try:
        steps = json.loads(tmpl.description or "[]")
    except:
        steps = []

    for s in steps:
        if not s.strip():
            continue
        task = JobTask(
            job_id=job.id,
            description=s.strip(),
            completed=False
        )
        db.session.add(task)

    db.session.commit()
    flash('Checklist attached to job.')
    return redirect(url_for('view_job', job_id=job.id))


# ------------------------------------------------------------
# ADMIN: CREATE NEW CHECKLIST TEMPLATE
# ------------------------------------------------------------
@app.route('/admin/checklists/new', methods=['GET', 'POST'])
@login_required
def admin_checklist_new():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    # Create empty template object for the form
    tmpl = JobTaskTemplate(name='', service_type='', description='[]')

    if request.method == 'POST':
        name = request.form.get('name')
        service_type = request.form.get('service_type')
        steps = request.form.getlist('steps[]')

        tmpl = JobTaskTemplate(
            name=name,
            service_type=service_type,
            description=json.dumps([s.strip() for s in steps if s.strip()])
        )
        db.session.add(tmpl)
        db.session.commit()
        flash('Checklist template created.')
        return redirect(url_for('admin_checklists'))

    return render_template('admin_checklist_edit.html', tmpl=tmpl, steps=[])


# ------------------------------------------------------------
# ADMIN: EDIT CHECKLIST TEMPLATE
# ------------------------------------------------------------
@app.route('/admin/checklists/<int:checklist_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_checklist_edit(checklist_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    tmpl = JobTaskTemplate.query.get_or_404(checklist_id)

    import json
    try:
        steps = json.loads(tmpl.description or "[]")
    except:
        steps = []

    if request.method == 'POST':
        tmpl.name = request.form.get('name')
        tmpl.service_type = request.form.get('service_type')
        new_steps = request.form.getlist('steps[]')
        tmpl.description = json.dumps([s.strip() for s in new_steps if s.strip()])
        db.session.commit()
        flash('Checklist updated.')
        return redirect(url_for('admin_checklists'))

    return render_template('admin_checklist_edit.html', tmpl=tmpl, steps=steps)


# ---------------------------------------------------------
# FIX: Missing delete_photo route (causing BuildError)
# ---------------------------------------------------------
@app.route('/jobs/<int:job_id>/photo/<int:photo_id>/delete', methods=['POST'])
@login_required
def delete_photo(job_id, photo_id):
    photo = JobPhoto.query.get_or_404(photo_id)
    db.session.delete(photo)
    db.session.commit()
    flash('Photo deleted.')
    return redirect(url_for('view_job', job_id=job_id))

# =========================
# RBAC + PWA BLOCK 1
# =========================
from functools import wraps

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

class RolePermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey("permission.id"), nullable=False)
    role = db.relationship("Role", backref=db.backref("role_permissions", lazy="dynamic", cascade="all, delete-orphan"))
    permission = db.relationship("Permission", backref=db.backref("permission_roles", lazy="dynamic", cascade="all, delete-orphan"))

class UserRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
    user = db.relationship("User", backref=db.backref("user_roles", lazy="dynamic", cascade="all, delete-orphan"))
    role = db.relationship("Role", backref=db.backref("users", lazy="dynamic", cascade="all, delete-orphan"))

BASE_PERMISSIONS = [
    "view_jobs", "edit_jobs", "delete_jobs", "upload_photos", "delete_photos",
    "manage_inventory", "manage_users", "manage_roles", "approve_contracts",
    "edit_contracts", "edit_tasks", "clock_in_out_edit"
]

def bootstrap_permissions():
    for name in BASE_PERMISSIONS:
        if not Permission.query.filter_by(name=name).first():
            db.session.add(Permission(name=name))
    db.session.commit()

def user_has_permission(perm_name):
    if not current_user.is_authenticated:
        return False
    if getattr(current_user, "role", "") == "admin":
        return True
    perm = Permission.query.filter_by(name=perm_name).first()
    if not perm:
        return False
    for ur in current_user.user_roles:
        for rp in ur.role.role_permissions:
            if rp.permission_id == perm.id:
                return True
    return False

def permission_required(perm_name):
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapped(*args, **kwargs):
            if not user_has_permission(perm_name):
                flash("Permission denied.")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapped
    return decorator

@app.context_processor
def inject_globals():
    theme = ThemeSettings.query.first()
    return {
        "is_admin": is_admin(),
        "current_user": current_user,
        "theme": theme,
        "user_has_permission": user_has_permission,
    }

@app.route("/admin/rbac/bootstrap", methods=["POST"])
@login_required
def admin_rbac_bootstrap():
    if not is_admin():
        flash("Admins only.")
        return redirect(url_for("dashboard"))
    bootstrap_permissions()
    flash("RBAC base permissions initialized.")
    return redirect(url_for("admin_home"))

@app.route("/admin/roles", methods=["GET", "POST"])
@login_required
def admin_roles():
    if not is_admin():
        flash("Admins only.")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        if not name:
            flash("Role name is required.")
            return redirect(url_for("admin_roles"))
        if Role.query.count() >= 3:
            flash("Maximum of 3 roles reached.")
            return redirect(url_for("admin_roles"))
        if Role.query.filter_by(name=name).first():
            flash("Role name already exists.")
            return redirect(url_for("admin_roles"))
        db.session.add(Role(name=name, description=description))
        db.session.commit()
        flash("Role created.")
        return redirect(url_for("admin_roles"))
    roles = Role.query.order_by(Role.name).all()
    permissions = Permission.query.order_by(Permission.name).all()
    return render_template("admin_roles.html", roles=roles, permissions=permissions)

@app.route("/admin/roles/<int:role_id>/permissions", methods=["POST"])
@login_required
def admin_roles_permissions(role_id):
    if not is_admin():
        flash("Admins only.")
        return redirect(url_for("dashboard"))
    role = Role.query.get_or_404(role_id)
    RolePermission.query.filter_by(role_id=role.id).delete()
    selected = request.form.getlist("permissions")
    for pname in selected:
        perm = Permission.query.filter_by(name=pname).first()
        if perm:
            db.session.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.session.commit()
    flash("Role permissions updated.")
    return redirect(url_for("admin_roles"))

@app.route("/admin/users/<int:user_id>/roles", methods=["POST"])
@login_required
def admin_users_assign_roles(user_id):
    if not is_admin():
        flash("Admins only.")
        return redirect(url_for("dashboard"))
    user = User.query.get_or_404(user_id)
    UserRole.query.filter_by(user_id=user.id).delete()
    selected_role_ids = request.form.getlist("roles")
    for rid in selected_role_ids:
        role = Role.query.get(int(rid))
        if role:
            db.session.add(UserRole(user_id=user.id, role_id=role.id))
    db.session.commit()
    flash("User roles updated.")
    return redirect(url_for("admin_users"))




@app.route('/jobs/<int:job_id>/export/companycam_v2', methods=['POST'])
@login_required
def export_job_companycam_v2(job_id):
    import io, os, csv, zipfile
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import landscape, letter

    job = Job.query.get_or_404(job_id)
    data = request.get_json() or {}
    selected_ids = data.get("photos") or []
    layout = int(data.get("layout") or 4)
    metadata = data.get("metadata") or []

    if selected_ids:
        photos = JobPhoto.query.filter(JobPhoto.id.in_(selected_ids)).order_by(JobPhoto.uploaded_at.asc()).all()
    else:
        photos = job.photos.order_by(JobPhoto.uploaded_at.asc()).all()

    packout_items = job.packout_items.order_by(PackoutItem.id.asc()).all()
    contracts = job.contracts.order_by(JobContract.id.asc()).all()
    tasks = job.tasks.order_by(JobTask.id.asc()).all()

    export_root = os.path.join(app.config['ARCHIVE_FOLDER'], 'companycam_v2')
    os.makedirs(export_root, exist_ok=True)
    pdf_filename = f"job_{job.id}_companycam_v2.pdf"
    pdf_path = os.path.join(export_root, pdf_filename)

    pdf = canvas.Canvas(pdf_path, pagesize=landscape(letter))

    try:
        logo_path = os.path.join(STATIC_DIR, "logo.png")
        pdf.drawImage(logo_path, 40, 450, width=120, height=120, preserveAspectRatio=True)
    except:
        pass

    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(180, 520, "Professional Cleaning Restoration & Rehab Services Group")

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(180, 495, f"Job Report — {job.job_number}")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 450, f"Title: {job.title}")
    pdf.drawString(50, 430, f"Client: {job.client_name or ''}")
    pdf.drawString(50, 410, f"Address: {job.address or ''}")
    pdf.drawString(50, 390, f"Service: {job.service_type or ''}")
    pdf.drawString(50, 370, f"Status: {job.status}")
    pdf.drawString(50, 350, f"Created: {job.created_at.strftime('%Y-%m-%d %H:%M')}")
    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 550, "Task Summary")
    pdf.setFont("Helvetica", 11)
    y = 520
    for t in tasks:
        status = "Done" if t.completed else "Pending"
        pdf.drawString(50, y, f"{t.label} — {status}")
        y -= 18
        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica-Bold", 18)
            pdf.drawString(50, 550, "Task Summary (cont.)")
            pdf.setFont("Helvetica", 11)
            y = 520
    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 550, "Packout Summary")
    pdf.setFont("Helvetica", 11)
    y = 520
    for item in packout_items:
        pdf.drawString(50, y, f"{item.name} x{item.quantity} @ {item.location or ''} ({item.condition or ''})")
        y -= 18
        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica-Bold", 18)
            pdf.drawString(50, 550, "Packout Summary (cont.)")
            pdf.setFont("Helvetica", 11)
            y = 520
    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 550, "Contracts Summary")
    pdf.setFont("Helvetica", 11)
    y = 520
    for c in contracts:
        status = "Signed" if c.signed else "Pending"
        pdf.drawString(50, y, f"Template #{c.template_id} — {status} — {c.signer_name or ''}")
        y -= 18
        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica-Bold", 18)
            pdf.drawString(50, 550, "Contracts Summary (cont.)")
            pdf.setFont("Helvetica", 11)
            y = 520
    pdf.showPage()

    per_row = max(2, min(layout, 4))
    per_page = per_row * 2
    thumb_w = 260
    thumb_h = 180
    padding_x = 40
    padding_y = 40

    index = 0
    while index < len(photos):
        chunk = photos[index:index + per_page]
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(50, 550, "Photo Evidence")

        for i, p in enumerate(chunk):
            row = i // per_row
            col = i % per_row
            x = 50 + col * (thumb_w + padding_x)
            y = 500 - row * (thumb_h + padding_y)

            rel = p.filename.replace("\", "/")
            abs_path = os.path.join(STATIC_DIR, rel)
            try:
                pdf.drawImage(abs_path, x, y, width=thumb_w, height=thumb_h, preserveAspectRatio=True)
            except:
                pdf.setFont("Helvetica", 10)
                pdf.drawString(x, y + thumb_h / 2, "[Image missing]")

            meta_y = y - 14
            pdf.setFont("Helvetica", 10)
            meta = []
            if "numbers" in metadata:
                meta.append(f"#{p.id}")
            if "captured_by" in metadata and p.user_id:
                meta.append(f"Tech {p.user_id}")
            if "location" in metadata and p.location_label:
                meta.append(p.location_label)
            if "date" in metadata and p.uploaded_at:
                meta.append(p.uploaded_at.strftime("%Y-%m-%d %H:%M"))
            if "tags" in metadata and p.category:
                meta.append(p.category)
            if meta:
                pdf.drawString(x, meta_y, " | ".join(meta))

        pdf.showPage()
        index += per_page

    pdf.save()

    zip_buffer = io.BytesIO()
    z = zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED)

    with open(pdf_path, "rb") as fpdf:
        z.writestr(pdf_filename, fpdf.read())

    for p in photos:
        rel = p.filename.replace("\", "/")
        abs_path = os.path.join(STATIC_DIR, rel)
        if os.path.exists(abs_path):
            z.write(abs_path, arcname=os.path.join("photos", os.path.basename(abs_path)))

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["Name", "Quantity", "Location", "Condition", "Notes"])
    for item in packout_items:
        writer.writerow([item.name, item.quantity, item.location or "", item.condition or "", item.notes or ""])
    z.writestr(f"job_{job.id}_packout.csv", csv_buffer.getvalue())

    contracts_payload = []
    for c in contracts:
        contracts_payload.append({
            "template_id": c.template_id,
            "signed": bool(c.signed),
            "signed_at": c.signed_at.isoformat() if c.signed_at else None,
            "signer_name": c.signer_name,
            "signer_email": c.signer_email,
        })
    z.writestr(f"job_{job.id}_contracts.json", json.dumps(contracts_payload, indent=2))

    z.close()
    zip_buffer.seek(0)

    zip_name = f"job_{job.id}_companycam_v2.zip"
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=zip_name
    )
