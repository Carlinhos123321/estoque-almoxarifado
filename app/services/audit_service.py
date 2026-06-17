from flask import current_app, request

from ..extensions import db
from ..models import ActivityLog


class AuditService:
    """Centralized activity logging."""

    @staticmethod
    def log(action, entity, entity_id, description, company_id, user_id, commit=True):
        """Record an activity log entry.

        Existing callers run this after the business transaction commits, so the
        default is to commit the audit entry independently. If a future caller
        needs the audit row in the same transaction, pass commit=False.
        """
        try:
            ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            log = ActivityLog(
                company_id=company_id,
                user_id=user_id,
                action=action,
                entity=entity,
                entity_id=entity_id,
                description=(description or "")[:400],
                ip=ip,
            )
            db.session.add(log)
            if commit:
                db.session.commit()
            else:
                db.session.flush()
            return log
        except Exception:
            if commit:
                db.session.rollback()
            current_app.logger.exception("Failed to persist audit log for %s:%s", entity, entity_id)
            return None
