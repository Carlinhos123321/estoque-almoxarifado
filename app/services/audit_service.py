from flask import request
from ..extensions import db
from ..models import ActivityLog

class AuditService:
    """Serviço centralizado para auditoria e rastreabilidade (SaaS Professional)."""

    @staticmethod
    def log(action, entity, entity_id, description, company_id, user_id):
        """Registra uma ação no log de atividades com metadados de rede."""
        try:
            ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            log = ActivityLog(
                company_id=company_id,
                user_id=user_id,
                action=action,
                entity=entity,
                entity_id=entity_id,
                description=description,
                ip=ip
            )
            db.session.add(log)
        except Exception:
            pass # Auditoria não deve travar a transação principal