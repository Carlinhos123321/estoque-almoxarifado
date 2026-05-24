"""MovStok ERP - configuration."""
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///movstok.db")

    # Render / Heroku give postgres:// but SQLAlchemy 2.x needs postgresql://
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    JSON_SORT_KEYS = False
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8h

    # Defaults
    DEFAULT_COMPANY_NAME = os.getenv("COMPANY_NAME", "MovStok Logística Ltda")
    DEFAULT_COMPANY_CNPJ = os.getenv("COMPANY_CNPJ", "00.000.000/0001-00")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@movstok.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Administrador")
