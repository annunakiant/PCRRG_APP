import os, json
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import app, is_admin

THEME_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data')
THEME_FILE = os.path.join(THEME_DIR, 'theme_engine.json')

os.makedirs(THEME_DIR, exist_ok=True)

DEFAULT_THEME = {
    "mode": "dark",
    "primary": "#00A8FF",
    "accent": "#00E0FF",
    "background": "#0D0D0D",
    "card": "rgba(255,255,255,0.05)",
    "card_border": "rgba(255,255,255,0.08)",
    "font_family": "Inter, system-ui",
    "font_size": "15px",
    "blur": True,
    "layout": "wide",
    "tabs": "pill",
    "buttons": "rounded",
    "background_image": ""
}

def load_theme():
    if not os.path.exists(THEME_FILE):
        with open(THEME_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_THEME, f, indent=2)
        return DEFAULT_THEME
    with open(THEME_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_theme(cfg):
    with open(THEME_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)

from theme_engine import theme_bp

@theme_bp.route('/admin/theme-engine', methods=['GET', 'POST'])
@login_required
def theme_admin():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    cfg = load_theme()

    if request.method == 'POST':
        for key in cfg.keys():
            if key in request.form:
                cfg[key] = request.form.get(key)

        # Handle background image upload
        bg_file = request.files.get('background_image_file')
        if bg_file and bg_file.filename:
            upload_dir = os.path.join(app.root_path, 'static', 'theme')
            os.makedirs(upload_dir, exist_ok=True)
            filename = f"bg_{bg_file.filename}"
            path = os.path.join(upload_dir, filename)
            bg_file.save(path)
            cfg["background_image"] = f"/static/theme/{filename}"

        save_theme(cfg)
        flash('Theme updated.')
        return redirect(url_for('theme.theme_admin'))

    return render_template('theme_engine.html', theme=cfg)
