"""Seed initial data: company, permissions, roles, admin user, demo catalog."""
from datetime import datetime, timedelta
import random

from flask import current_app

from .extensions import db
from .models import (
    Category, Company, Employee, Permission, Product, Role,
    StockEntry, StockLocation, StockOutput, Supplier, User,
)

PERMISSIONS = [
    # module, code, label
    ("dashboard", "dashboard.view", "Visualizar dashboard"),
    ("products", "products.view", "Visualizar produtos"),
    ("products", "products.create", "Criar produtos"),
    ("products", "products.edit", "Editar produtos"),
    ("products", "products.delete", "Excluir produtos"),
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
            "settings.view",
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


def _ensure_company():
    company = Company.query.first()
    if not company:
        company = Company(
            name=current_app.config["DEFAULT_COMPANY_NAME"],
            legal_name=current_app.config["DEFAULT_COMPANY_NAME"],
            cnpj=current_app.config["DEFAULT_COMPANY_CNPJ"],
            email="contato@movstok.com",
            phone="(11) 4000-0000",
            city="São Paulo", state="SP",
        )
        db.session.add(company)
        db.session.commit()
    return company


def _ensure_admin(company):
    email = current_app.config["ADMIN_EMAIL"]
    if User.query.filter_by(email=email).first():
        return
    admin_role = Role.query.filter_by(name="admin").first()
    user = User(
        name=current_app.config["ADMIN_NAME"],
        email=email,
        company_id=company.id,
        role_id=admin_role.id if admin_role else None,
        status="active",
    )
    user.set_password(current_app.config["ADMIN_PASSWORD"])
    db.session.add(user)
    db.session.commit()


def _ensure_demo_catalog(company):
    """Add demo data only the first time (when there are no products)."""
    if Product.query.count() > 0:
        return

    # Stock location
    loc = StockLocation(company_id=company.id, code="A-01", name="Almoxarifado Central",
                        description="Galpão principal")
    db.session.add(loc)

    # Categories
    cats = {
        "EPI": Category(company_id=company.id, name="EPI", description="Equipamentos de Proteção Individual", color="#dc2626"),
        "Ferramentas": Category(company_id=company.id, name="Ferramentas", color="#1d4ed8"),
        "Limpeza": Category(company_id=company.id, name="Limpeza", color="#15803d"),
        "Escritório": Category(company_id=company.id, name="Escritório", color="#d97706"),
        "Elétrica": Category(company_id=company.id, name="Elétrica", color="#7c3aed"),
    }
    for c in cats.values():
        db.session.add(c)

    # Suppliers
    suppliers = [
        Supplier(company_id=company.id, name="Distribuidora Nacional Ltda",
                 cnpj="12.345.678/0001-90", email="vendas@distnac.com.br",
                 phone="(11) 3344-5566", city="São Paulo", state="SP", contact_person="Ricardo Alves"),
        Supplier(company_id=company.id, name="EPI Brasil S/A",
                 cnpj="98.765.432/0001-10", email="comercial@epibrasil.com.br",
                 phone="(11) 2233-4455", city="Guarulhos", state="SP", contact_person="Mariana Souza"),
        Supplier(company_id=company.id, name="FerragensExpress",
                 cnpj="55.444.333/0001-22", email="contato@ferragensex.com.br",
                 phone="(11) 4455-6677", city="Osasco", state="SP", contact_person="Paulo Mendes"),
    ]
    for s in suppliers:
        db.session.add(s)
    db.session.flush()

    # Products
    products_seed = [
        ("EPI-001", "Capacete de Segurança Classe B", "EPI", suppliers[1], "UN", 28.90, 45.00, 80, 20, 200),
        ("EPI-002", "Luva Nitrílica Cano Longo", "EPI", suppliers[1], "PAR", 6.50, 12.00, 320, 100, 800),
        ("EPI-003", "Óculos de Proteção Ampla Visão", "EPI", suppliers[1], "UN", 9.20, 18.00, 145, 50, 400),
        ("EPI-004", "Protetor Auricular Plug", "EPI", suppliers[1], "PAR", 1.80, 4.50, 12, 50, 1000),
        ("FER-001", "Furadeira Industrial 850W", "Ferramentas", suppliers[2], "UN", 320.00, 480.00, 8, 5, 30),
        ("FER-002", "Chave de Fenda Phillips 6\"", "Ferramentas", suppliers[2], "UN", 12.40, 22.00, 64, 20, 150),
        ("FER-003", "Trena 5m Profissional", "Ferramentas", suppliers[2], "UN", 18.90, 32.00, 22, 10, 80),
        ("LMP-001", "Desinfetante Concentrado 5L", "Limpeza", suppliers[0], "L", 24.00, 38.00, 56, 20, 200),
        ("LMP-002", "Papel Toalha Bobina 200m", "Limpeza", suppliers[0], "CX", 42.50, 68.00, 18, 10, 60),
        ("LMP-003", "Saco de Lixo 100L (pacote 100un)", "Limpeza", suppliers[0], "CX", 28.00, 42.00, 4, 10, 60),
        ("ESC-001", "Papel A4 75g (resma 500fls)", "Escritório", suppliers[0], "RM", 22.90, 35.00, 92, 30, 250),
        ("ESC-002", "Caneta Esferográfica Azul", "Escritório", suppliers[0], "UN", 1.20, 2.80, 480, 200, 2000),
        ("ELE-001", "Cabo Flex 2,5mm 100m", "Elétrica", suppliers[2], "RL", 188.00, 260.00, 6, 4, 25),
        ("ELE-002", "Lâmpada LED 12W Bivolt", "Elétrica", suppliers[2], "UN", 8.40, 16.00, 210, 80, 500),
        ("ELE-003", "Disjuntor Bipolar 25A", "Elétrica", suppliers[2], "UN", 24.50, 42.00, 32, 15, 120),
    ]
    products = []
    for sku, name, cat, sup, unit, cost, sale, qty, mn, mx in products_seed:
        p = Product(
            company_id=company.id,
            category_id=cats[cat].id,
            supplier_id=sup.id,
            location_id=loc.id,
            sku=sku, name=name, unit=unit,
            cost_price=cost, sale_price=sale,
            stock_quantity=qty, min_stock=mn, max_stock=mx,
            barcode=f"789{random.randint(1000000000, 9999999999)}",
            status="active",
        )
        db.session.add(p)
        products.append(p)
    db.session.flush()

    # Employees
    employees_seed = [
        ("0001", "João Pereira da Silva", "Logística", "Auxiliar de Almoxarifado"),
        ("0002", "Maria Aparecida Costa", "Logística", "Conferente"),
        ("0003", "Carlos Henrique Rocha", "Manutenção", "Técnico de Manutenção"),
        ("0004", "Fernanda Lima Souza", "Compras", "Analista de Compras"),
        ("0005", "Roberto Almeida", "Logística", "Encarregado"),
        ("0006", "Patrícia Nogueira", "Administrativo", "Assistente Administrativo"),
    ]
    emps = []
    for enrl, name, dept, pos in employees_seed:
        e = Employee(company_id=company.id, enrollment=enrl, name=name,
                     department=dept, position=pos, status="active",
                     hire_date=datetime.utcnow() - timedelta(days=random.randint(120, 1800)))
        db.session.add(e)
        emps.append(e)
    db.session.flush()

    # Movements (some entries and outputs over the last 30 days)
    for _ in range(40):
        p = random.choice(products)
        days_ago = random.randint(0, 30)
        when = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))
        if random.random() < 0.55:
            qty = random.randint(5, 50)
            db.session.add(StockEntry(
                company_id=company.id, product_id=p.id, supplier_id=p.supplier_id,
                document=f"NF-{random.randint(10000, 99999)}",
                quantity=qty, unit_cost=p.cost_price,
                total_cost=float(p.cost_price or 0) * qty,
                entry_date=when, status="confirmed",
            ))
        else:
            qty = random.randint(1, 8)
            emp = random.choice(emps)
            db.session.add(StockOutput(
                company_id=company.id, product_id=p.id, employee_id=emp.id,
                document=f"REQ-{random.randint(1000, 9999)}",
                quantity=qty, unit_price=p.sale_price,
                total_price=float(p.sale_price or 0) * qty,
                reason="consumption", destination=emp.department,
                output_date=when, status="confirmed",
            ))

    db.session.commit()


def seed_initial():
    """Idempotent seed for first boot."""
    _ensure_permissions()
    _ensure_roles()
    company = _ensure_company()
    _ensure_admin(company)
    _ensure_demo_catalog(company)
