"""Authentication blueprint - login / logout / session APIs."""
from datetime import datetime, timedelta
import secrets

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, jsonify, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensions import db
from ..helpers import log_activity
from ..models import ActivityLog, Company, PasswordResetToken, Permission, Role, User
from ..security import get_client_ip, get_csrf_token, rate_limit
from ..services.email import queue_password_reset_email

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login_page():
    """Serve the SPA login page (handled by static/index.html)."""
    return current_app.send_static_file("index.html")


@bp.get("/api/auth/csrf")
def api_csrf():
    return jsonify({"csrf_token": get_csrf_token()})


@bp.post("/api/auth/login")
@rate_limit(limit=8, window_seconds=15 * 60, key_prefix="login")
def api_login():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    remember = bool(data.get("remember", False))

    if not email or not password:
        return jsonify({"error": "Email e senha sao obrigatorios."}), 400

    try:
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "Credenciais invalidas."}), 401
        if user.status != "active":
            return jsonify({"error": "Usuario inativo. Contate o administrador."}), 403

        login_user(user, remember=remember)
        user.last_login_at = datetime.utcnow()
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Login failed because of a database error.")
        return jsonify({"error": "Nao foi possivel autenticar agora."}), 503

    log_activity("login", "user", user.id, f"Login de {user.email}")
    return jsonify({"ok": True, "user": user.to_dict()})


@bp.post("/api/auth/logout")
@login_required
def api_logout():
    log_activity("logout", "user", current_user.id, f"Logout de {current_user.email}")
    logout_user()
    return jsonify({"ok": True})


@bp.post("/api/auth/register")
@rate_limit(limit=3, window_seconds=10 * 60, key_prefix="register")
def api_register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()[:100]
    company_name = (data.get("company_name") or "").strip()[:100]
    email = (data.get("email") or "").strip().lower()[:120]
    phone = (data.get("phone") or "").strip()[:20]
    password = data.get("password") or ""

    if not name or not company_name or not email or not password:
        return jsonify({"error": "Todos os campos sao obrigatorios."}), 400

    if len(password) < 6:
        return jsonify({"error": "A senha deve ter pelo menos 6 caracteres."}), 400

    try:
        email = validate_email(email, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return jsonify({"error": "Informe um e-mail valido."}), 400

    try:
        ten_min_ago = datetime.utcnow() - timedelta(minutes=10)
        recent_attempts = ActivityLog.query.filter(
            ActivityLog.ip == get_client_ip(),
            ActivityLog.action == "create",
            ActivityLog.entity == "user",
            ActivityLog.created_at >= ten_min_ago,
        ).count()

        if recent_attempts >= 3:
            return jsonify({"error": "Muitas tentativas de cadastro. Tente novamente em instantes."}), 429

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Este e-mail ja esta cadastrado."}), 400

        admin_role = Role.query.filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                label="Administrador",
                description="Acesso total ao sistema",
                is_system=True,
            )
            admin_role.permissions = Permission.query.all()
            db.session.add(admin_role)
            db.session.flush()

        company = Company(name=company_name, legal_name=company_name)
        db.session.add(company)
        db.session.flush()

        user = User(
            name=name,
            email=email,
            company_id=company.id,
            role_id=admin_role.id,
            phone=phone,
            status="active",
        )
        user.set_password(password)
        user.last_login_at = datetime.utcnow()
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Este e-mail ja esta cadastrado."}), 400
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Registration failed because of a database error.")
        return jsonify({"error": "Nao foi possivel criar a conta agora."}), 503

    login_user(user, remember=True)
    log_activity("create", "user", user.id, f"Novo registro: {user.email}")

    return jsonify({"ok": True, "message": "Conta criada!", "user": user.to_dict()})


@bp.post("/api/auth/forgot-password")
@rate_limit(limit=5, window_seconds=15 * 60, key_prefix="forgot-password")
def api_forgot_password():
    data = request.get_json(silent=True) or {}
    raw_email = (data.get("email") or "").strip().lower()

    try:
        email = validate_email(raw_email, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return jsonify({"error": "Informe um e-mail corporativo valido."}), 400

    response = {
        "ok": True,
        "message": "Se o e-mail estiver cadastrado, enviaremos as instrucoes de recuperacao em instantes.",
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
    log_activity("password_reset_request", "user", user.id, f"Recuperacao de senha solicitada para {user.email}")

    return jsonify(response)


@bp.post("/api/auth/reset-password")
@rate_limit(limit=3, window_seconds=15 * 60, key_prefix="reset-password")
def api_reset_password_token():
    """Validate the reset token and set a new password."""
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    new_password = data.get("password")

    if not token or not new_password or len(new_password) < 6:
        return jsonify({"error": "Dados invalidos ou senha muito curta (min. 6 caracteres)."}), 400

    reset_records = PasswordResetToken.query.filter(
        PasswordResetToken.expires_at > datetime.utcnow(),
        PasswordResetToken.used_at.is_(None),
    ).all()
    target_reset = next((r for r in reset_records if r.check_token(token)), None)

    if not target_reset:
        return jsonify({"error": "Token de recuperacao invalido ou expirado."}), 400

    user = db.session.get(User, target_reset.user_id)
    if not user:
        return jsonify({"error": "Usuario nao encontrado."}), 404

    user.set_password(new_password)
    target_reset.used_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "message": "Senha alterada com sucesso!"})


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
    log_activity("update", "user", current_user.id, "Alteracao de senha")
    return jsonify({"ok": True})
