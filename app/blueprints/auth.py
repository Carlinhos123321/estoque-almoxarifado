"""Authentication blueprint - login / logout / session APIs."""
from datetime import datetime, timedelta
import secrets

from flask import Blueprint, current_app, jsonify, redirect, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from email_validator import EmailNotValidError, validate_email

from ..extensions import db
from ..helpers import log_activity
from ..models import PasswordResetToken, User
from ..services.email import queue_password_reset_email

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login_page():
    """Serve the SPA login page (handled by static/index.html)."""
    return current_app.send_static_file("index.html")


@bp.post("/api/auth/login")
def api_login():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    remember = bool(data.get("remember", False))

    if not email or not password:
        return jsonify({"error": "Email e senha são obrigatórios."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Credenciais inválidas."}), 401
    if user.status != "active":
        return jsonify({"error": "Usuário inativo. Contate o administrador."}), 403

    login_user(user, remember=remember)
    user.last_login_at = datetime.utcnow()
    db.session.commit()
    log_activity("login", "user", user.id, f"Login de {user.email}")

    return jsonify({"ok": True, "user": user.to_dict()})


@bp.post("/api/auth/logout")
@login_required
def api_logout():
    log_activity("logout", "user", current_user.id, f"Logout de {current_user.email}")
    logout_user()
    return jsonify({"ok": True})


@bp.post("/api/auth/forgot-password")
def api_forgot_password():
    data = request.get_json(silent=True) or {}
    raw_email = (data.get("email") or "").strip().lower()

    try:
        email = validate_email(raw_email, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return jsonify({"error": "Informe um e-mail corporativo válido."}), 400

    response = {
        "ok": True,
        "message": "Se o e-mail estiver cadastrado, enviaremos as instruções de recuperação em instantes.",
    }

    user = User.query.filter_by(email=email).first()
    if not user or user.status != "active":
        current_app.logger.info("Password reset requested for unknown/inactive email: %s", email)
        return jsonify(response)

    token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(
            minutes=current_app.config.get("PASSWORD_RESET_TOKEN_MINUTES", 30)
        ),
        requested_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
    )
    reset.set_token(token)
    db.session.add(reset)
    db.session.commit()

    reset_url = url_for("auth.login_page", _external=True) + f"?reset_token={token}"
    queue_password_reset_email(user, reset_url, reset.expires_at)
    log_activity("password_reset_request", "user", user.id, f"Recuperação de senha solicitada para {user.email}")

    return jsonify(response)


@bp.get("/api/auth/me")
def api_me():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False}), 200
    return jsonify({
        "authenticated": True,
        "user": current_user.to_dict(),
        "permissions": (
            [p.code for p in current_user.role.permissions]
            if current_user.role else []
        ),
    })


@bp.post("/api/auth/change-password")
@login_required
def api_change_password():
    data = request.get_json(silent=True) or {}
    current = data.get("current_password") or ""
    new = data.get("new_password") or ""
    if not current_user.check_password(current):
        return jsonify({"error": "Senha atual incorreta."}), 400
    if len(new) < 6:
        return jsonify({"error": "A nova senha deve ter pelo menos 6 caracteres."}), 400
    current_user.set_password(new)
    db.session.commit()
    log_activity("update", "user", current_user.id, "Alteração de senha")
    return jsonify({"ok": True})
