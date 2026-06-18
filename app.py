import os
import json
import logging
from datetime import datetime
from flask import (
    Flask, render_template, redirect, url_for,
    request, flash, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
import smtplib
from email.message import EmailMessage

# -------------------------------------------------------------------------
# BASE CONFIG + LOGGING
# -------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(
    BASE_DIR, 'data', 'pcrrg_fieldops_v2.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER_PHOTOS'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER_CONTRACTS'] = os.path.join(BASE_DIR, 'static', 'contracts')
app.config['UPLOAD_FOLDER_PACKOUT'] = os.path.join(BASE_DIR, 'static', 'packouts')
app.config['ARCHIVE_FOLDER'] = os.path.join(BASE_DIR, 'data', 'archive')

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("Starting PCRRG SUPER-MEGA app.py")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# -------------------------------------------------------------------------
# MODELS
# -------------------------------------------------------------------------
class ThemeSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    primary_color = db.Column(db.String(20), default="#1E88E5")
    secondary_color = db.Column(db.String(20), default="#FFC107")
    logo_url = db.Column(db.String(255), default="/static/logo.png")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    pin = db.Column(db.String(4), nullable=False)
    name = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255))
    role = db.Column(db.String(50), default='tech')  # 'tech', 'admin'

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
    custom_values = db.relationship('CustomFieldValue', backref='job', lazy='dynamic')
    tasks = db.relationship('JobTask', backref='job', lazy='dynamic')
    sessions = db.relationship('EmployeeSession', backref='job', lazy='dynamic')


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    filename = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    user = db.relationship('User')


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
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    template = db.relationship('ContractTemplate')


class CustomTab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    order = db.Column(db.Integer, default=0)


class CustomField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tab_id = db.Column(db.Integer, db.ForeignKey('custom_tab.id'), nullable=False)
    label = db.Column(db.String(255), nullable=False)
    field_type = db.Column(db.String(50), nullable=False)  # text, number, select, checkbox
    required = db.Column(db.Boolean, default=False)
    options = db.Column(db.String(255))  # comma-separated for select

    tab = db.relationship('CustomTab', backref='fields')


class CustomFieldValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('custom_field.id'), nullable=False)
    value = db.Column(db.String(255))

    field = db.relationship('CustomField')


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
    notes = db.Column(db.String(255))

    user = db.relationship('User')


class JobTaskTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    service_type = db.Column(db.String(100))


class JobTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('job_task_template.id'))
    label = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    template = db.relationship('JobTaskTemplate')
    completed_by = db.relationship('User')

# -------------------------------------------------------------------------
# LOGIN + GLOBALS
# -------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def is_admin():
    return current_user.is_authenticated and current_user.is_admin()


@app.context_processor
def inject_globals():
    theme = ThemeSettings.query.first()
    if not theme:
        theme = ThemeSettings(
            primary_color="#1E88E5",
            secondary_color="#FFC107",
            logo_url="/static/logo.png"
        )
        db.session.add(theme)
        db.session.commit()

    return {
        'is_admin': is_admin(),
        'current_user': current_user,
        'theme': theme
    }

# -------------------------------------------------------------------------
# EMAIL
# -------------------------------------------------------------------------
def send_job_email(job, to_email, subject, body):
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    from_email = os.environ.get('FROM_EMAIL', smtp_user)

    if not (smtp_host and smtp_user and smtp_pass and from_email):
        logger.warning('Email not configured; skipping send.')
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info(f"Email sent to {to_email} for job {job.job_number}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")

# -------------------------------------------------------------------------
# AUTH
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

# -------------------------------------------------------------------------
# DASHBOARD
# -------------------------------------------------------------------------
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

@app.route('/employee/clock-in', methods=['POST'])
@login_required
def employee_clock_in():
    session = EmployeeSession(
        user_id=current_user.id,
        job_id=None,
        clock_in_at=datetime.utcnow(),
        clock_in_lat=None,
        clock_in_lon=None
    )
    db.session.add(session)
    db.session.commit()
    flash('Clocked in.')
    return redirect(url_for('dashboard'))


@app.route('/employee/clock-out', methods=['POST'])
@login_required
def employee_clock_out():
    session = EmployeeSession.query.filter_by(
        user_id=current_user.id,
        clock_out_at=None
    ).first()

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

    for p in job.photos.order_by(Photo.uploaded_at.desc()).all():
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
        tasks=tasks
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

    filename = f"{job.id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
    path = os.path.join(app.config['UPLOAD_FOLDER_PHOTOS'], filename)
    file.save(path)

    lat = request.form.get('lat')
    lon = request.form.get('lon')

    photo = Photo(
        job_id=job.id,
        user_id=current_user.id,
        filename=filename,
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
# WSGI ENTRYPOINT
# -------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)

# -------------------------------------------------------------------------
# BLUEPRINT REGISTRATION (ADVANCED ADMIN)
# -------------------------------------------------------------------------
from extensions.advanced_admin import advanced_admin_bp
app.register_blueprint(advanced_admin_bp)
# -------------------------------------------------------------------------
# PLUS PACK BLUEPRINT
# -------------------------------------------------------------------------
from plus import plus_bp
app.register_blueprint(plus_bp, url_prefix='/plus')

# -------------------------------------------------------------------------
# THEME ENGINE 2.0 BLUEPRINT
# -------------------------------------------------------------------------
from theme_engine import theme_bp
app.register_blueprint(theme_bp, url_prefix='/theme')
# Inject Theme Engine config into all templates
from theme_engine.routes import load_theme

@app.context_processor
def inject_theme():
    return {"t": load_theme()}
# -------------------------------------------------------------------------
# THEME ENGINE GLOBAL INJECTOR (FINAL FIX)
# -------------------------------------------------------------------------
from theme_engine.routes import load_theme

@app.context_processor
def inject_theme():
    try:
        return {"t": load_theme()}
    except:
        return {"t": {}}
from routes_templates import templates_bp
app.register_blueprint(templates_bp)
