from flask import Flask, g, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY']                  = os.environ.get('SECRET_KEY', 'dev-key-imobifacil-2026')
    app.config['SQLALCHEMY_DATABASE_URI']     = os.environ.get('DATABASE_URL', 'sqlite:///imobifacil.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH']          = 16 * 1024 * 1024   # 16 MB upload máximo

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # ── Registro de Blueprints ─────────────────────────────────────
    from .auth.routes  import auth_bp
    from .admin.routes import admin_bp
    from .site.routes  import site_bp
    from .leads.routes import leads_bp
    from .api.routes   import api_bp

    app.register_blueprint(auth_bp,  url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(leads_bp, url_prefix='/admin/leads')
    app.register_blueprint(api_bp,   url_prefix='/api')
    app.register_blueprint(site_bp)

    # ── Middleware: identifica a imobiliária pelo domínio ──────────
    @app.before_request
    def carregar_imobiliaria():
        # Rotas estáticas não precisam de lookup no banco
        if request.endpoint == 'static':
            return
        from .models import Imobiliaria
        host = request.host.split(':')[0]
        g.imobiliaria = Imobiliaria.query.filter_by(dominio=host).first()

    return app


@login_manager.user_loader
def load_user(user_id):
    from .models import Usuario
    return Usuario.query.get(int(user_id))