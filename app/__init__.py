"""MovStok ERP - Flask application factory."""
import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv

from .extensions import db, login_manager, migrate
from .config import Config
from .security import init_security

load_dotenv()


def create_app(config_class: type = Config) -> Flask:
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
        static_url_path="/static",
    )
    app.config.from_object(config_class)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login_page"
    login_manager.login_message = "Faça login para continuar."
    login_manager.login_message_category = "warning"

    init_security(app)

    # Models must be imported so SQLAlchemy registers them
    from . import models  # noqa: F401

    # Blueprints
    from .blueprints.auth import bp as auth_bp
    from .blueprints.web import bp as web_bp
    from .blueprints.api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # Auto-create tables + seed on first boot (safe + idempotent)
    with app.app_context():
        try:
            db.create_all()
            from .seed import seed_initial
            seed_initial()
        except Exception as exc:  # pragma: no cover
            app.logger.warning("DB init/seed skipped: %s", exc)

    @app.route("/")
    def index():
        return redirect(url_for("web.dashboard"))

    @app.context_processor
    def inject_globals():
        return {
            "APP_NAME": "MovStok",
            "APP_TAGLINE": "ERP & Gestão de Almoxarifado",
        }

    return app
