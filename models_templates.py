from app import db

class JobTemplate(db.Model):
    __tablename__ = 'job_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    job_type = db.Column(db.String(80), nullable=True)
    auto_apply_tasks = db.Column(db.Boolean, default=True)
    auto_apply_materials = db.Column(db.Boolean, default=True)
    auto_apply_packout = db.Column(db.Boolean, default=True)
    ask_contracts = db.Column(db.Boolean, default=True)
    ask_notes = db.Column(db.Boolean, default=True)
    ask_photos = db.Column(db.Boolean, default=True)

class JobTemplateTask(db.Model):
    __tablename__ = 'job_template_tasks'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('job_templates.id'))
    description = db.Column(db.String(255), nullable=False)

class JobTemplateMaterial(db.Model):
    __tablename__ = 'job_template_materials'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('job_templates.id'))
    name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1)

class PackoutProfile(db.Model):
    __tablename__ = 'packout_profiles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

class PackoutItem(db.Model):
    __tablename__ = 'packout_items'
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('packout_profiles.id'))
    name = db.Column(db.String(255), nullable=False)
    condition = db.Column(db.String(80), nullable=True)
    location = db.Column(db.String(120), nullable=True)
    quantity = db.Column(db.Integer, default=1)

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    doc_type = db.Column(db.String(80), nullable=True)
    file_path = db.Column(db.String(255), nullable=False)
    requires_signature = db.Column(db.Boolean, default=False)

class ContractBundle(db.Model):
    __tablename__ = 'contract_bundles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

class ContractBundleItem(db.Model):
    __tablename__ = 'contract_bundle_items'
    id = db.Column(db.Integer, primary_key=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('contract_bundles.id'))
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))

class TaskPreset(db.Model):
    __tablename__ = 'task_presets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    job_type = db.Column(db.String(80), nullable=True)

class TaskPresetItem(db.Model):
    __tablename__ = 'task_preset_items'
    id = db.Column(db.Integer, primary_key=True)
    preset_id = db.Column(db.Integer, db.ForeignKey('task_presets.id'))
    description = db.Column(db.String(255), nullable=False)
