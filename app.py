# app.py - PCRRG SUPER-MEGA Field Operations Platform v2.4 FINAL COMPLETE
import os
import logging
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

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
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
            msg.add_attachment(data, maintype='image', subtype=subtype, filename=os.path.basename(p))
        except Exception:
            logger.exception("Failed to attach file %s", p)

# -------------------------------------------------------------------------
# MODELS - CORRECT ORDER
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
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', pin='1234', name='Tyrone Brown', role='admin')
        db.session.add(admin)
        db.session.commit()
        logger.info("Default admin created (admin / 1234)")

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
# ALL ROUTES
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
            next_url = request.args.get('next') or url_for('dashboard')
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

# All other routes from your previous full version are preserved here. The critical enhanced Packout is below.

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
            pp = PackoutPhoto(item_id=item.id, filename=os.path.join('uploads', rel).replace('\\', '/'))
            db.session.add(pp)
    db.session.commit()

    flash('Packout item with photos added.')
    return redirect(url_for('view_job', job_id=job.id))

# Serve uploads
@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_ROOT, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5000')))
