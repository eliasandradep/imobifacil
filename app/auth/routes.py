from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user
from ..models import Usuario

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(email=request.form.get('email')).first()
        if user and user.check_senha(request.form.get('senha')):
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        flash('E-mail ou senha incorretos.', 'danger')
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))