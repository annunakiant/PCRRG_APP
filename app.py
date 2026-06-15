import os
import json
from datetime import datetime
from flask import (
    Flask, render_template, redirect, url_for,
    request, flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
import smtplib
from email.message import EmailMessage

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
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
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)


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


# EMAIL
def send_job_email(job, to_email, subject, body):
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
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


# CORE ROUTES
@app.route('/')
@login_required
def dashboard():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    inventory_count = InventoryItem.query.count()
    contracts_pending = JobContract.query.filter_by(signed=False).count()
    return render_template(
        'dashboard.html',
        jobs=jobs,
        inventory_count=inventory_count,
        contracts_pending=contracts_pending
    )


@app.route('/jobs/<int:job_id>')
@login_required
def view_job(job_id):
    job = Job.query.get_or_404(job_id)
    photos = job.photos.all()
    packout_items = job.packout_items.all()
    contracts = job.contracts.all()
    templates = ContractTemplate.query.all()
    tabs = CustomTab.query.order_by(CustomTab.order).all()

    values_map = {}
    for v in job.custom_values:
        values_map[v.field_id] = v.value

    return render_template(
        'view_job.html',
        job=job,
        photos=photos,
        packout_items=packout_items,
        contracts=contracts,
        templates=templates,
        tabs=tabs,
        values_map=values_map
    )


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
        filename=filename,
        category=request.form.get('category'),
        latitude=float(lat) if lat else None,
        longitude=float(lon) if lon else None
    )

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

    return render_template(
        'admin.html',
        jobs=jobs,
        inventory_items=inventory_items,
        tabs=tabs
    )


@app.route('/admin/tabs', methods=['GET', 'POST'])
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

    for field in tab.fields:
        CustomFieldValue.query.filter_by(field_id=field.id).delete()
        db.session.delete(field)

    db.session.delete(tab)
    db.session.commit()
    flash('Tab and its fields deleted.')
    return redirect(url_for('admin_tabs'))


@app.route('/admin/fields/<int:tab_id>', methods=['GET', 'POST'])
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
        field = CustomField(
            tab_id=tab.id,
            label=label,
            field_type=field_type,
            required=required,
            options=options
        )
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
            existing = CustomFieldValue.query.filter_by(
                job_id=job.id,
                field_id=field.id
            ).first()
            if existing:
                existing.value = val
            else:
                if val:
                    cfv = CustomFieldValue(
                        job_id=job.id,
                        field_id=field.id,
                        value=val
                    )
                    db.session.add(cfv)

    db.session.commit()
    flash('Custom fields saved.')
    return redirect(url_for('view_job', job_id=job.id))


# AUTH
@app.route('/login', methods=['GET', 'POST'])
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


@app.route('/register', methods=['GET', 'POST'])
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

        user = User(
            username=username,
            pin=pin,
            name=name,
            phone=phone,
            email=email,
            role='tech'
        )
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
        job = Job(
            job_number='PCRRG-1001',
            title='Sample Job',
            client_name='Acme Corp',
            address='123 Main St',
            service_type='Water Mitigation'
        )
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
