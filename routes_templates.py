from flask import Blueprint, render_template
from flask_login import login_required
from app import is_admin
from models_templates import JobTemplate, PackoutProfile, ContractBundle, TaskPreset

templates_bp = Blueprint('templates_bp', __name__, url_prefix='/admin/templates')

@templates_bp.route('/', methods=['GET'])
@login_required
def templates_home():
    if not is_admin():
        return render_template('error.html', message='Admins only.')

    job_templates = JobTemplate.query.all()
    packouts = PackoutProfile.query.all()
    bundles = ContractBundle.query.all()
    presets = TaskPreset.query.all()

    return render_template('admin_templates_center.html',
                           job_templates=job_templates,
                           packouts=packouts,
                           bundles=bundles,
                           presets=presets)
