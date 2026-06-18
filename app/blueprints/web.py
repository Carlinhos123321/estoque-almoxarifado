"""Web blueprint - serves the single-page ERP shell.

All routes return the same static index.html (SPA-like). The frontend
uses History API / hash routing to switch between modules. This keeps
the existing single-file frontend architecture but routes are server-known
so deep links work.
"""
from flask import Blueprint, current_app
from flask_login import login_required

from ..helpers import require_permission

bp = Blueprint("web", __name__)

# Pages handled by the SPA shell
PAGES = [
    "dashboard", "produtos", "categorias", "fornecedores",
    "entradas", "saidas", "estoque",
    "funcionarios", "matriculas", "relatorios",
    "alertas", "financeiro", "configuracoes", "usuarios", "atividades",
    "administracao",
]

PAGE_PERMISSIONS = {
    "dashboard": "dashboard.view",
    "produtos": "products.view",
    "categorias": "categories.view",
    "fornecedores": "suppliers.view",
    "entradas": "stock.entry",
    "saidas": "stock.output",
    "estoque": "stock.view",
    "funcionarios": "employees.view",
    "matriculas": "employees.view",
    "relatorios": "reports.view",
    "alertas": "dashboard.view",
    "financeiro": "finance.view",
    "configuracoes": "settings.view",
    "usuarios": "users.manage",
    "atividades": "admin.system",
    "administracao": "admin.system",
}


def _shell():
    return current_app.send_static_file("index.html")


@bp.get("/app")
@login_required
@require_permission("dashboard.view")
def dashboard():
    return _shell()


for _p in PAGES:
    view = require_permission(PAGE_PERMISSIONS[_p])(_shell)
    bp.add_url_rule(f"/app/{_p}", endpoint=f"page_{_p}", view_func=view)
