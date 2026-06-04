"""Security controls for the MovStok Flask app.

Client-side code can always be inspected in a browser. The protections here
therefore focus on the assets that actually matter: sessions, API requests,
browser security headers, brute-force resistance and data exposure boundaries.
"""
from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, jsonify, request, session

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_HEADER = "X-CSRF-Token"
CSRF_SESSION_KEY = "_csrf_token"

_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def get_client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.remote_addr or "unknown"


def get_csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf() -> tuple[bool, str | None]:
    expected = session.get(CSRF_SESSION_KEY)
    provided = request.headers.get(CSRF_HEADER)
    if expected and provided and secrets.compare_digest(expected, provided):
        return True, None
    return False, "Sessão expirada ou requisição inválida. Recarregue a página e tente novamente."


def rate_limit(limit: int, window_seconds: int, key_prefix: str | None = None):
    """Simple per-process rate limit for sensitive endpoints.

    This is intentionally dependency-free. In a multi-worker production deploy,
    replace this with Redis-backed limiting so all workers share the same bucket.
    """
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            now = time.time()
            identity = f"{key_prefix or request.endpoint}:{get_client_ip()}"
            bucket = _rate_buckets[identity]

            while bucket and bucket[0] <= now - window_seconds:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                response = jsonify({
                    "error": "Muitas tentativas. Aguarde um pouco e tente novamente."
                })
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                return response

            bucket.append(now)
            return view(*args, **kwargs)
        return wrapper
    return decorator


def init_security(app):
    @app.before_request
    def enforce_csrf():
        if request.method not in UNSAFE_METHODS:
            return None
        if request.endpoint in {"auth.api_csrf"}:
            return None
        if request.path.startswith("/static/"):
            return None

        valid, message = validate_csrf()
        if not valid:
            return jsonify({"error": message}), 419
        return None

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net blob:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "worker-src 'self' blob:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'",
        )

        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")

        if request.is_secure or current_app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
