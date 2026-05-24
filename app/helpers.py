"""Common helpers: permission decorators, activity log, pagination."""
from functools import wraps
from typing import Callable

from flask import abort, jsonify, request
from flask_login import current_user

from .extensions import db
from .models import ActivityLog


def login_required_api(view: Callable):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "unauthorized"}), 401
        return view(*args, **kwargs)
    return wrapper


def require_permission(code: str, api: bool = False):
    def decorator(view: Callable):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                if api:
                    return jsonify({"error": "unauthorized"}), 401
                return abort(401)
            if not current_user.can(code):
                if api:
                    return jsonify({"error": "forbidden", "missing_permission": code}), 403
                return abort(403)
            return view(*args, **kwargs)
        return wrapper
    return decorator


def log_activity(action: str, entity: str, entity_id: int | None = None,
                 description: str = "") -> None:
    try:
        log = ActivityLog(
            company_id=getattr(current_user, "company_id", None) if current_user.is_authenticated else None,
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            description=description[:400],
            ip=request.remote_addr if request else None,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


def paginate_query(query, default_per_page: int = 20, max_per_page: int = 200):
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    try:
        per_page = min(max_per_page, max(1, int(request.args.get("per_page", default_per_page))))
    except ValueError:
        per_page = default_per_page

    total = query.count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    pages = (total + per_page - 1) // per_page if per_page else 1
    return {
        "items": items,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
            "has_prev": page > 1,
            "has_next": page < pages,
        },
    }
