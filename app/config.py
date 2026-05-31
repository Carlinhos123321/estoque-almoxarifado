"""MovStok ERP - configuration."""
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/movstok",
    )

    # Railway/Render/Heroku may expose postgres://; SQLAlchemy 2.x expects postgresql://.
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    JSON_SORT_KEYS = False
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8h
    PASSWORD_RESET_TOKEN_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_MINUTES", "30"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(8 * 1024 * 1024)))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    # Defaults
    DEFAULT_COMPANY_NAME = os.getenv("COMPANY_NAME", "MovStok Logística Ltda")
    DEFAULT_COMPANY_CNPJ = os.getenv("COMPANY_CNPJ", "00.000.000/0001-00")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@movstok.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this-before-deploy")
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Administrador")
