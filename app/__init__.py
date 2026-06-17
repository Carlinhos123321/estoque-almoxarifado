"""IMA Stock - Flask application factory."""
import os
import re

from flask import Flask, jsonify, redirect, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .extensions import db, login_manager, migrate
from .security import init_security


def _mask_database_uri(uri: str) -> str:
    return re.sub(r"//([^:/@]+):([^@]+)@", r"//\1:***@", uri)


def create_app(config_class: type = Config) -> Flask:
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
        static_url_path="/static",
    )
    app.config.from_object(config_class)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    if app.config.get("LOG_DATABASE_URI"):
        app.logger.info(
            "SQLAlchemy database URI: %s",
            _mask_database_uri(app.config["SQLALCHEMY_DATABASE_URI"]),
        )

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login_page"
    login_manager.login_message = "Faca login para continuar."
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

    if app.config.get("AUTO_CREATE_SCHEMA"):
        with app.app_context():
            try:
                db.create_all()
                from .seed import seed_initial

                seed_initial()
            except Exception as exc:  # pragma: no cover
                app.logger.exception("Automatic DB init/seed failed: %s", exc)

    @app.route("/")
    def index():
        return redirect(url_for("web.dashboard"))

    @app.context_processor
    def inject_globals():
        return {
            "APP_NAME": "IMA Stock",
            "APP_TAGLINE": "ERP & Gestao de Almoxarifado",
        }

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.exception("Unhandled application error: %s", error)
        if request.path.startswith("/api/") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "Erro interno no servidor. Tente novamente em instantes."}), 500
        return app.send_static_file("index.html"), 500

    return app
