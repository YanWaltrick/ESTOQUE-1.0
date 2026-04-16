from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app import estoque

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    """Página principal do dashboard"""
    return render_template('index.html')

@main_bp.route('/admin')
@login_required
def admin():
    """Página de administração de usuários"""
    if not current_user.is_admin:
        return redirect(url_for('main.index'))
    return render_template('admin.html')