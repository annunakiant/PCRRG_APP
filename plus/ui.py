import os, json
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import app, db, ThemeSettings, is_admin

PLUS_DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data')
PLUS_CONFIG_PATH = os.path.join(PLUS_DATA_DIR, 'plus_ui.json')
PLUS_UPLOADS = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'static', 'plus_uploads')

os.makedirs(PLUS_DATA_DIR, exist_ok=True)
os.makedirs(PLUS_UPLOADS, exist_ok=True)

def load_plus_config():
    if not os.path.exists(PLUS_CONFIG_PATH):
        cfg = {
            "background_image_url": "",
            "font_family": "system-ui",
            "font_size": "15px",
            "layout_style": "default",
            "home_tabs_style": "standard"
        }
        with open(PLUS_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
        return cfg
    with open(PLUS_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_plus_config(cfg):
    with open(PLUS_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)

@app.context_processor
def inject_plus():
    return { "plus_ui": load_plus_config() }

from plus import plus_bp

@plus_bp.route('/admin/look', methods=['GET', 'POST'])
@login_required
def plus_look():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    cfg = load_plus_config()
    theme = ThemeSettings.query.first()

    if request.method == 'POST':
        # ThemeSettings (DB)
        primary = request.form.get('primary_color')
        secondary = request.form.get('secondary_color')

        if not theme:
            theme = ThemeSettings()
            db.session.add(theme)

        if primary: theme.primary_color = primary
        if secondary: theme.secondary_color = secondary

        # Logo upload
        logo_file = request.files.get('logo_file')
        if logo_file and logo_file.filename:
            filename = f"logo_{current_user.id}_{logo_file.filename}"
            path = os.path.join(PLUS_UPLOADS, filename)
            logo_file.save(path)
            theme.logo_url = f"/static/plus_uploads/{filename}"

        # PLUS config (JSON)
        cfg["background_image_url"] = request.form.get('background_image_url') or cfg["background_image_url"]
        cfg["font_family"] = request.form.get('font_family') or cfg["font_family"]
        cfg["font_size"] = request.form.get('font_size') or cfg["font_size"]
        cfg["layout_style"] = request.form.get('layout_style') or cfg["layout_style"]
        cfg["home_tabs_style"] = request.form.get('home_tabs_style') or cfg["home_tabs_style"]

        save_plus_config(cfg)
        db.session.commit()
        flash('Look & Feel updated.')
        return redirect(url_for('plus.plus_look'))

    return render_template('plus_look.html', theme=theme, plus_ui=cfg)

@plus_bp.route('/admin/presets')
@login_required
def plus_presets():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))
    return render_template('plus_presets.html')
