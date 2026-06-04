"""Seed initial data: company, permissions, roles, admin user, demo catalog."""
from datetime import datetime, timedelta
import random
import sqlalchemy as sa
from flask import current_app

from .extensions import db
from .models import (
    Category, Company, Employee, Permission, Product, Role,
    StockEntry, StockLocation, StockOutput, Supplier, User,
    PasswordResetToken, ActivityLog
)

PERMISSIONS = [
    # module, code, label
    ("dashboard", "dashboard.view", "Visualizar dashboard"),
    ("products", "products.view", "Visualizar produtos"),
    ("products", "products.create", "Criar produtos"),
    ("products", "products.edit", "Editar produtos"),
    ("products", "products.delete", "Excluir produtos"),
    ("finance", "finance.view", "Visualizar financeiro"),
    ("finance", "finance.manage", "Gerenciar financeiro"),
    ("admin", "admin.system", "Administrar sistema"),
    ("users", "users.view", "Visualizar usuarios"),
    ("stock", "stock.view", "Visualizar estoque"),
    ("stock", "stock.entry", "Registrar entradas"),
    ("stock", "stock.output", "Registrar saídas"),
    ("suppliers", "suppliers.view", "Visualizar fornecedores"),
    ("suppliers", "suppliers.manage", "Gerenciar fornecedores"),
    ("categories", "categories.view", "Visualizar categorias"),
    ("categories", "categories.manage", "Gerenciar categorias"),
    ("employees", "employees.view", "Visualizar funcionários"),
    ("employees", "employees.manage", "Gerenciar funcionários"),
    ("reports", "reports.view", "Visualizar relatórios"),
    ("reports", "reports.export", "Exportar relatórios"),
    ("settings", "settings.view", "Visualizar configurações"),
    ("settings", "settings.manage", "Gerenciar configurações"),
    ("users", "users.manage", "Gerenciar usuários e permissões"),
]

ROLES = {
    "super_admin": {
        "label": "Super Admin",
        "description": "Acesso irrestrito a todos os modulos, telas e configuracoes",
        "permissions": "*",
    },
    "admin": {
        "label": "Administrador",
        "description": "Acesso total ao sistema",
        "permissions": "*",
    },
    "manager": {
        "label": "Gerente",
        "description": "Operações + relatórios, sem gestão de usuários",
        "permissions": [
            "dashboard.view", "products.view", "products.create", "products.edit",
            "stock.view", "stock.entry", "stock.output",
            "suppliers.view", "suppliers.manage",
            "categories.view", "categories.manage",
            "employees.view", "employees.manage",
            "reports.view", "reports.export",
            "settings.view", "users.view",
        ],
    },
    "operator": {
        "label": "Operador",
        "description": "Operações diárias de almoxarifado",
        "permissions": [
            "dashboard.view", "products.view",
            "stock.view", "stock.entry", "stock.output",
            "suppliers.view", "categories.view", "employees.view",
            "reports.view",
        ],
    },
    "viewer": {
        "label": "Consulta",
        "description": "Somente leitura",
        "permissions": [
            "dashboard.view", "products.view", "stock.view",
            "suppliers.view", "categories.view", "employees.view", "reports.view",
        ],
    },
}


def _ensure_permissions():
    existing = {p.code for p in Permission.query.all()}
    for module, code, label in PERMISSIONS:
        if code not in existing:
            db.session.add(Permission(module=module, code=code, label=label))
    db.session.commit()


def _ensure_roles():
    all_perms = {p.code: p for p in Permission.query.all()}
    for name, cfg in ROLES.items():
        role = Role.query.filter_by(name=name).first()
        if not role:
            role = Role(name=name, label=cfg["label"], description=cfg["description"], is_system=True)
            db.session.add(role)
            db.session.flush()
        if cfg["permissions"] == "*":
            role.permissions = list(all_perms.values())
        else:
            role.permissions = [all_perms[c] for c in cfg["permissions"] if c in all_perms]
    db.session.commit()


def factory_reset():
    """Limpeza completa para distribuição (Factory Reset).
    Remove dados operacionais, preservando apenas RBAC.
    """
    # Ordem de exclusão respeitando FKs
    tables_to_clear = [
        StockEntry, StockOutput, ActivityLog, PasswordResetToken,
        Product, Category, Supplier, Employee, StockLocation,
        User, Company
    ]
    
    for model in tables_to_clear:
        db.session.query(model).delete()
    
    db.session.commit()
    print("Factory Reset concluído: Sistema limpo para distribuição.")

def seed_initial():
    """Idempotent seed for first boot."""
    _ensure_permissions()
    _ensure_roles()
    # Nota: Empresa e Admin não são mais criados automaticamente no seed.
    # O sistema agora aguarda o primeiro registro via UI (Opção A).
