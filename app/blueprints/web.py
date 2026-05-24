"""Web blueprint - serves the single-page ERP shell.

All routes return the same static index.html (SPA-like). The frontend
uses History API / hash routing to switch between modules. This keeps
the existing single-file frontend architecture but routes are server-known
so deep links work.
"""
from flask import Blueprint, current_app

bp = Blueprint("web", __name__)

# Pages handled by the SPA shell
PAGES = [
    "dashboard", "produtos", "categorias", "fornecedores",
    "entradas", "saidas", "estoque",
    "funcionarios", "matriculas", "relatorios",
    "configuracoes", "usuarios", "atividades",
]


def _shell():
    return current_app.send_static_file("index.html")


@bp.get("/app")
def dashboard():
    return _shell()


for _p in PAGES:
    bp.add_url_rule(f"/app/{_p}", endpoint=f"page_{_p}", view_func=_shell)
