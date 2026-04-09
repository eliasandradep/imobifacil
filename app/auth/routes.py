from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user
from ..models import Usuario, Imobiliaria

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Superadmin autenticado não deve usar este login
    if current_user.is_authenticated:
        if getattr(current_user, 'is_superadmin', False):
            return redirect(url_for('superadmin.dashboard'))
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        user  = Usuario.query.filter_by(email=email).first()

        if user and user.check_senha(senha):
            # Verifica se a imobiliária está ativa
            imob = Imobiliaria.query.get(user.imobiliaria_id)
            if not imob or not imob.ativo:
                flash('Esta conta está suspensa. Entre em contato com o suporte.', 'danger')
                return render_template('auth/login.html')
            login_user(user)
            return redirect(url_for('admin.dashboard'))

        flash('E-mail ou senha incorretos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
