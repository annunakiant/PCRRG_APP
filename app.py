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
