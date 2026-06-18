from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db, User, ThemeSettings, CustomTab

advanced_admin_bp = Blueprint('advanced_admin', __name__, url_prefix='/xadmin')

def is_admin():
    return current_user.is_authenticated and getattr(current_user, 'role', '') == 'admin'

@advanced_admin_bp.route('/')
@login_required
def home():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('dashboard'))

    users = User.query.order_by(User.username).all()
    tabs = CustomTab.query.order_by(CustomTab.order).all()
    theme = ThemeSettings.query.first()
    return render_template('xadmin_home.html', users=users, tabs=tabs, theme=theme)

@advanced_admin_bp.route('/theme', methods=['POST'])
@login_required
def theme_update():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('advanced_admin.home'))

    primary = request.form.get('primary_color')
    secondary = request.form.get('secondary_color')
    logo = request.files.get('logo_file')

    theme = ThemeSettings.query.first()
    if not theme:
        theme = ThemeSettings()
        db.session.add(theme)

    if primary:
        theme.primary_color = primary
    if secondary:
        theme.secondary_color = secondary

    # For now, just accept a URL string; file upload wiring can be added later
    logo_url = request.form.get('logo_url')
    if logo_url:
        theme.logo_url = logo_url

    db.session.commit()
    flash('Advanced theme updated.')
    return redirect(url_for('advanced_admin.home'))

@advanced_admin_bp.route('/tabs', methods=['GET', 'POST'])
@login_required
def tabs():
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('advanced_admin.home'))

    if request.method == 'POST':
        name = request.form.get('name')
        order = int(request.form.get('order') or 0)
        if not name:
            flash('Tab name required.')
            return redirect(url_for('advanced_admin.tabs'))
        tab = CustomTab(name=name, order=order)
        db.session.add(tab)
        db.session.commit()
        flash('Tab created.')
        return redirect(url_for('advanced_admin.tabs'))

    tabs = CustomTab.query.order_by(CustomTab.order).all()
    return render_template('xadmin_tabs.html', tabs=tabs)

@advanced_admin_bp.route('/tabs/<int:tab_id>/delete', methods=['POST'])
@login_required
def tabs_delete(tab_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('advanced_admin.tabs'))

    tab = CustomTab.query.get_or_404(tab_id)
    db.session.delete(tab)
    db.session.commit()
    flash('Tab deleted.')
    return redirect(url_for('advanced_admin.tabs'))

@advanced_admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
def user_role(user_id):
    if not is_admin():
        flash('Admins only.')
        return redirect(url_for('advanced_admin.home'))

    user = User.query.get_or_404(user_id)
    role = request.form.get('role') or user.role
    user.role = role
    db.session.commit()
    flash('User role updated.')
    return redirect(url_for('advanced_admin.home'))
