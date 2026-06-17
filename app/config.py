"""IMA Stock - configuration."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _database_url() -> str:
    uri = os.getenv("DATABASE_URL")
    if not uri:
        raise RuntimeError("DATABASE_URL is required. Configure it in .env or the hosting environment.")
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    return uri


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("SQLALCHEMY_POOL_RECYCLE", "280")),
    }

    JSON_SORT_KEYS = False
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8h
    PASSWORD_RESET_TOKEN_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_MINUTES", "30"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(8 * 1024 * 1024)))
    LOG_DATABASE_URI = os.getenv("LOG_DATABASE_URI", "0") == "1"
    AUTO_CREATE_SCHEMA = os.getenv("AUTO_CREATE_SCHEMA", "0") == "1"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv(
        "SESSION_COOKIE_SECURE",
        "1" if os.getenv("FLASK_ENV") == "production" else "0",
    ) == "1"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    # Defaults
    DEFAULT_COMPANY_NAME = os.getenv("COMPANY_NAME", "IMA Stock")
    DEFAULT_COMPANY_CNPJ = os.getenv("COMPANY_CNPJ", "00.000.000/0001-00")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@imastock.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this-before-deploy")
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Administrador")
