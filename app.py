# app.py
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

# -------------------------
# Basic config + logging
# -------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(DATA_DIR, "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Upload folders
app.config["UPLOAD_FOLDER_PHOTOS"] = os.path.join(STATIC_DIR, "uploads", "photos")
app.config["UPLOAD_FOLDER_PACKOUT"] = os.path.join(STATIC_DIR, "uploads", "packouts")
app.config["UPLOAD_FOLDER_CONTRACTS"] = os.path.join(STATIC_DIR, "uploads", "contracts")
for p in (app.config["UPLOAD_FOLDER_PHOTOS"], app.config["UPLOAD_FOLDER_PACKOUT"], app.config["UPLOAD_FOLDER_CONTRACTS"]):
    os.makedirs(p, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.info("Starting app.py")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif"}


# -------------------------
# Models
# -------------------------
class ThemeSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    primary_color = db.Column(db.String(20), default="#1E88E5")
    secondary_color = db.Column(db.String(20), default="#FFC107")
    logo_url = db.Column(db.String(255), default="/static/logo.png")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    pin = db.Column(db.String(16), nullable=False)
    name = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255))
    role = db.Column(db.String(50), default="tech")  # 'tech', 'admin'

    def is_admin(self):
        return self.role == "admin"


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    client_name = db.Column(db.String(255))
    address = db.Column(db.String(255))
    status = db.Column(db.String(50), default="open")  # open, closed, archived
    service_type = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)

    photos = db.relationship("JobPhoto", backref="job", lazy="dynamic", cascade="all,delete-orphan")
    packout_items = db.relationship("PackoutItem", backref="job", lazy="dynamic", cascade="all,delete-orphan")
    contracts = db.relationship("JobContract", backref="job", lazy="dynamic", cascade="all,delete-orphan")
    tasks = db.relationship("JobTask", backref="job", lazy="dynamic", cascade="all,delete-orphan")
    custom_values = db.relationship("JobCustomValue", backref="job", lazy="dynamic", cascade="all,delete-orphan")


class JobPhoto(db.Model):
    """
    Room-level photos (before/after). Each photo belongs to a job and has a location label.
    """
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    filename = db.Column(db.String(255), nullable=False)
    location_label = db.Column(db.String(255))  # e.g., Kitchen, Bedroom
    before_after = db.Column(db.String(16))  # 'before' or 'after' or None
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)


class PackoutItem(db.Model):
    """
    Packout items attached to a job. Each item can have multiple photos (packout photos).
    """
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    location = db.Column(db.String(255))
    notes = db.Column(db.String(255))
    condition = db.Column(db.String(50))
    photos = db.relationship("PackoutPhoto", backref="item", lazy="dynamic", cascade="all,delete-orphan")


class PackoutPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("packout_item.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContractTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)


class JobContract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("contract_template.id"))
    signed = db.Column(db.Boolean, default=False)
    signed_at = db.Column(db.DateTime)
    signer_name = db.Column(db.String(255))
    signer_email = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    template = db.relationship("ContractTemplate")


class JobTaskTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    service_type = db.Column(db.String(100))


class JobTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("job_task_template.id"))
    label = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    completed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    template = db.relationship("JobTaskTemplate")
    completed_by = db.relationship("User")


class CustomField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tab_id = db.Column(db.Integer, db.ForeignKey("custom_tab.id"), nullable=True)
    label = db.Column(db.String(255), nullable=False)
    field_type = db.Column(db.String(50), nullable=False)  # text, number, select, checkbox
    required = db.Column(db.Boolean, default=False)
    options = db.Column(db.String(255))  # comma-separated for select


class JobCustomValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey("custom_field.id"), nullable=False)
    value = db.Column(db.String(255))
    field = db.relationship("CustomField")


# -------------------------
# Helpers
# -------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXT


def save_upload(fileobj, folder):
    filename = secure_filename(fileobj.filename)
    timestamp = int(datetime.utcnow().timestamp())
    filename = f"{timestamp}_{filename}"
    path = os.path.join(folder, filename)
    fileobj.save(path)
    # return relative path from static for templates
    rel = os.path.relpath(path, STATIC_DIR)
    return rel, path


def attach_files_to_email(msg: EmailMessage, file_paths):
    for p in file_paths:
        try:
            with open(p, "rb") as f:
                data = f.read()
            maintype = "image"
            subtype = p.rsplit(".", 1)[1].lower() if "." in p else "octet-stream"
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(p))
        except Exception:
            logger.exception("Failed to attach file %s", p)


# -------------------------
# Bootstrap (create DB + default admin)
# -------------------------
with app.app_context():
    db.create_all()
    if not ThemeSettings.query.first():
        db.session.add(ThemeSettings())
        db.session.commit()
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", pin="1234", name="Default Admin", role="admin")
        db.session.add(admin)
        db.session.commit()
        logger.info("Created default admin (admin / 1234)")


# -------------------------
# Login + globals
# -------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_globals():
    theme = ThemeSettings.query.first()
    return {"is_admin": current_user.is_authenticated and getattr(current_user, "role", "") == "admin",
            "current_user": current_user, "theme": theme}


# -------------------------
# Routes (Auth, Dashboard, Jobs, Packout, Photos)
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        pin = request.form.get("pin")
        user = User.query.filter_by(username=username, pin=pin).first()
        if user:
            login_user(user)
            flash("Logged in.")
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid credentials.")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    jobs_open = Job.query.filter_by(status="open").count()
    jobs_closed = Job.query.filter_by(status="closed").count()
    jobs_archived = Job.query.filter_by(status="archived").count()
    inventory_count = 0 if not db.engine else db.session.query(db.func.count()).select_from(PackoutItem).scalar() or 0
    contracts_pending = JobContract.query.filter_by(signed=False).count()
    recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(10).all()
    active_sessions = []  # keep simple
    return render_template("dashboard.html", jobs_open=jobs_open, jobs_closed=jobs_closed,
                           jobs_archived=jobs_archived, inventory_count=inventory_count,
                           contracts_pending=contracts_pending, recent_jobs=recent_jobs,
                           active_sessions=active_sessions)


# Job CRUD
@app.route("/jobs/new", methods=["GET", "POST"])
@login_required
def new_job():
    if not current_user.is_authenticated or not current_user.is_admin():
        flash("Admins only.")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        job = Job(job_number=request.form.get("job_number") or f"JOB-{int(datetime.utcnow().timestamp())}",
                  title=request.form.get("title") or "Untitled",
                  client_name=request.form.get("client_name"),
                  address=request.form.get("address"),
                  service_type=request.form.get("service_type"))
        db.session.add(job)
        db.session.commit()
        flash("Job created.")
        return redirect(url_for("view_job", job_id=job.id))
    return render_template("new_job.html")


@app.route("/jobs/<int:job_id>")
@login_required
def view_job(job_id):
    job = Job.query.get_or_404(job_id)
    photos = job.photos.order_by(JobPhoto.uploaded_at.desc()).all()
    packout_items = job.packout_items.order_by(PackoutItem.id.desc()).all()
    return render_template("view_job.html", job=job, photos=photos, packout_items=packout_items)


# Upload room-level photo (before/after)
@app.route("/jobs/<int:job_id>/upload_room_photo", methods=["POST"])
@login_required
def upload_room_photo(job_id):
    job = Job.query.get_or_404(job_id)
    file = request.files.get("photo")
    if not file or file.filename == "" or not allowed_file(file.filename):
        flash("No valid image selected.")
        return redirect(url_for("view_job", job_id=job.id))

    rel, fullpath = save_upload(file, app.config["UPLOAD_FOLDER_PHOTOS"])
    location_label = request.form.get("location_label")
    before_after = request.form.get("before_after")  # 'before' or 'after'
    lat = request.form.get("lat")
    lon = request.form.get("lon")

    jp = JobPhoto(job_id=job.id, user_id=current_user.id, filename=rel,
                  location_label=location_label, before_after=before_after,
                  latitude=float(lat) if lat else None, longitude=float(lon) if lon else None)
    db.session.add(jp)
    db.session.commit()
    flash("Photo uploaded.")
    return redirect(url_for("view_job", job_id=job.id))


# Add packout item (optionally with a packout photo)
@app.route("/jobs/<int:job_id>/packout/add", methods=["POST"])
@login_required
def add_packout_item(job_id):
    job = Job.query.get_or_404(job_id)
    name = request.form.get("name")
    if not name:
        flash("Item name required.")
        return redirect(url_for("view_job", job_id=job.id))
    item = PackoutItem(job_id=job.id,
                       name=name,
                       quantity=int(request.form.get("quantity") or 1),
                       location=request.form.get("location"),
                       notes=request.form.get("notes"),
                       condition=request.form.get("condition"))
    db.session.add(item)
    db.session.commit()

    # optional packout photo
    file = request.files.get("packout_photo")
    if file and file.filename and allowed_file(file.filename):
        rel, fullpath = save_upload(file, app.config["UPLOAD_FOLDER_PACKOUT"])
        pp = PackoutPhoto(item_id=item.id, filename=rel)
        db.session.add(pp)
        db.session.commit()

    flash("Packout item added.")
    return redirect(url_for("view_job", job_id=job.id))


# Delete packout item
@app.route("/jobs/<int:job_id>/packout/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_packout_item(job_id, item_id):
    if not current_user.is_authenticated or not current_user.is_admin():
        flash("Admins only.")
        return redirect(url_for("view_job", job_id=job_id))
    item = PackoutItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Packout item deleted.")
    return redirect(url_for("view_job", job_id=job_id))


# Serve static uploaded files (safe)
@app.route("/static/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(os.path.join(STATIC_DIR, "uploads"), filename)


# Share job report via email with attachments (packout photos + before/after)
@app.route("/jobs/<int:job_id>/share", methods=["POST"])
@login_required
def share_job(job_id):
    job = Job.query.get_or_404(job_id)
    to_email = request.form.get("email")
    if not to_email:
        flash("Email required.")
        return redirect(url_for("view_job", job_id=job.id))

    # Build body
    lines = [
        f"Job {job.job_number} - {job.title}",
        f"Client: {job.client_name}",
        f"Address: {job.address}",
        f"Service: {job.service_type}",
        f"Status: {job.status}",
        "",
        "Packout items:"
    ]
    attachments = []
    for item in job.packout_items:
        lines.append(f"- {item.name} x{item.quantity} @ {item.location} ({item.notes or ''})")
        for p in item.photos:
            full = os.path.join(STATIC_DIR, p.filename)
            if os.path.exists(full):
                attachments.append(full)

    lines.append("")
    lines.append("Room photos (before/after):")
    for ph in job.photos:
        lines.append(f"- {ph.location_label or 'Unknown'} [{ph.before_after or 'n/a'}] {ph.filename}")
        full = os.path.join(STATIC_DIR, ph.filename)
        if os.path.exists(full):
            attachments.append(full)

    body = "\n".join(lines)

    # Send email (attach images)
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    from_email = os.environ.get("FROM_EMAIL", smtp_user)

    if not (smtp_host and smtp_user and smtp_pass and from_email):
        flash("Email not configured on server; report not sent but prepared.")
        return redirect(url_for("view_job", job_id=job.id))

    msg = EmailMessage()
    msg["Subject"] = f"Job report: {job.job_number}"
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(body)
    attach_files_to_email(msg, attachments)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        flash("Report emailed.")
    except Exception:
        logger.exception("Failed to send email")
        flash("Failed to send email (check server logs).")

    return redirect(url_for("view_job", job_id=job.id))


# Admin theme update
@app.route("/admin/theme", methods=["POST"])
@login_required
def admin_theme_update():
    if not current_user.is_authenticated or not current_user.is_admin():
        flash("Admins only.")
        return redirect(url_for("dashboard"))
    primary = request.form.get("primary_color")
    secondary = request.form.get("secondary_color")
    logo = request.form.get("logo_url")
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
    flash("Theme updated.")
    return redirect(url_for("admin_home"))


@app.route("/admin")
@login_required
def admin_home():
    if not current_user.is_authenticated or not current_user.is_admin():
        flash("Admins only.")
        return redirect(url_for("dashboard"))
    jobs = Job.query.order_by(Job.created_at.desc()).limit(10).all()
    tabs = CustomTab.query.order_by(CustomTab.order).all() if "CustomTab" in globals() else []
    theme = ThemeSettings.query.first()
    return render_template("admin.html", jobs=jobs, tabs=tabs, theme=theme)


# Minimal safe endpoints for other features (placeholders)
@app.route("/inventory")
@login_required
def inventory_list():
    items = []  # keep simple; extend as needed
    return render_template("inventory.html", items=items)


# -------------------------
# Run (local dev)
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
 
