"""Email integration points.

The current deployment records reset tokens in the database and logs the reset
URL. A production SMTP/provider integration can replace this service without
changing auth routes or frontend flows.
"""
from flask import current_app


def queue_password_reset_email(user, reset_url: str, expires_at) -> None:
    current_app.logger.info(
        "Password reset queued for %s; expires_at=%s; reset_url=%s",
        user.email,
        expires_at.isoformat() if expires_at else None,
        reset_url,
    )
