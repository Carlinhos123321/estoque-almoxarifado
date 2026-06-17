"""IMA Stock ERP - Database models (SQLAlchemy).

All entities required by the ERP:
- Company, User, Role, Permission, RolePermission, UserRole
- Category, Supplier, Product, StockLocation
- StockEntry (entrada), StockOutput (saida), StockMovement (unified ledger)
- Employee, Enrollment (matrícula)
- ActivityLog, Notification

Designed with: relationships, indexes, timestamps, status fields, audit fields,
soft-delete-friendly (active flags), and ready for PostgreSQL.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric,
    String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------
class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class AuditMixin:
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)


# ---------------------------------------------------------------------------
# Company (multi-tenant friendly; single tenant by default)
# ---------------------------------------------------------------------------
class Company(db.Model, TimestampMixin):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)
    legal_name = Column(String(200))
    cnpj = Column(String(20), unique=True, index=True)
    email = Column(String(160))
    phone = Column(String(40))
    address = Column(String(255))
    city = Column(String(120))
    state = Column(String(40))
    zipcode = Column(String(20))
    logo_url = Column(String(255))
    active = Column(Boolean, default=True, nullable=False)

    users = relationship("User", back_populates="company")
    products = relationship("Product", back_populates="company")
    suppliers = relationship("Supplier", back_populates="company")
    employees = relationship("Employee", back_populates="company")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "legal_name": self.legal_name,
            "cnpj": self.cnpj, "email": self.email, "phone": self.phone,
            "address": self.address, "city": self.city, "state": self.state,
            "zipcode": self.zipcode, "logo_url": self.logo_url, "active": self.active,
        }


# ---------------------------------------------------------------------------
# RBAC: Role / Permission
# ---------------------------------------------------------------------------
role_permissions = db.Table(
    "role_permissions",
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(db.Model, TimestampMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    label = Column(String(80), nullable=False)
    description = Column(String(255))
    is_system = Column(Boolean, default=False, nullable=False)

    permissions = relationship("Permission", secondary=role_permissions, backref="roles")
    users = relationship("User", back_populates="role")

    def has_permission(self, code: str) -> bool:
        return any(p.code == code for p in self.permissions)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "label": self.label,
            "description": self.description, "is_system": self.is_system,
            "permissions": [p.code for p in self.permissions],
        }


class Permission(db.Model, TimestampMixin):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True, nullable=False, index=True)
    label = Column(String(120), nullable=False)
    module = Column(String(40), nullable=False, index=True)

    def to_dict(self):
        return {"id": self.id, "code": self.code, "label": self.label, "module": self.module}


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(db.Model, UserMixin, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True, index=True)

    name = Column(String(120), nullable=False)
    email = Column(String(160), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(String(255))
    phone = Column(String(40))
    status = Column(String(20), default="active", nullable=False, index=True)  # active|inactive|blocked
    last_login_at = Column(DateTime)

    company = relationship("Company", back_populates="users")
    role = relationship("Role", back_populates="users")

    # password helpers
    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    # auth helpers
    @property
    def is_admin(self) -> bool:
        return bool(self.role and self.role.name in {"admin", "super_admin"})

    @property
    def is_super_admin(self) -> bool:
        return bool(self.role and self.role.name == "super_admin")

    def can(self, permission_code: str) -> bool:
        if self.is_admin:
            return True
        return bool(self.role and self.role.has_permission(permission_code))

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "email": self.email,
            "phone": self.phone, "avatar_url": self.avatar_url, "status": self.status,
            "role": self.role.to_dict() if self.role else None,
            "company_id": self.company_id,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PasswordResetToken(db.Model, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime)
    requested_ip = Column(String(60))

    user = relationship("User")

    def set_token(self, raw: str) -> None:
        self.token_hash = generate_password_hash(raw)

    def check_token(self, raw: str) -> bool:
        return check_password_hash(self.token_hash, raw)

    @property
    def is_active(self) -> bool:
        return not self.used_at and self.expires_at > datetime.utcnow()


@login_manager.user_loader
def _load_user(user_id: str):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Catalog: Category / Supplier / Product / StockLocation
# ---------------------------------------------------------------------------
class Category(db.Model, TimestampMixin, AuditMixin):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    name = Column(String(120), nullable=False)
    description = Column(String(255))
    color = Column(String(20), default="#1d4ed8")
    active = Column(Boolean, default=True, nullable=False)

    products = relationship("Product", back_populates="category")

    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_category_company_name"),)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "color": self.color, "active": self.active,
            "products_count": len(self.products),
        }


class Supplier(db.Model, TimestampMixin, AuditMixin):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    name = Column(String(160), nullable=False, index=True)
    cnpj = Column(String(20), index=True)
    email = Column(String(160))
    phone = Column(String(40))
    contact_person = Column(String(120))
    address = Column(String(255))
    city = Column(String(120))
    state = Column(String(40))
    notes = Column(Text)
    active = Column(Boolean, default=True, nullable=False)

    company = relationship("Company", back_populates="suppliers")
    products = relationship("Product", back_populates="supplier")
    entries = relationship("StockEntry", back_populates="supplier")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "cnpj": self.cnpj,
            "email": self.email, "phone": self.phone,
            "contact_person": self.contact_person, "address": self.address,
            "city": self.city, "state": self.state, "notes": self.notes,
            "active": self.active,
        }


class StockLocation(db.Model, TimestampMixin):
    __tablename__ = "stock_locations"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    code = Column(String(40), nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(String(255))
    active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_location_company_code"),)

    def to_dict(self):
        return {"id": self.id, "code": self.code, "name": self.name,
                "description": self.description, "active": self.active}


class Product(db.Model, TimestampMixin, AuditMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), index=True)
    location_id = Column(Integer, ForeignKey("stock_locations.id"), index=True)

    sku = Column(String(40), nullable=False, index=True)
    name = Column(String(180), nullable=False, index=True)
    description = Column(Text)
    unit = Column(String(20), default="UN", nullable=False)  # UN, KG, L, CX...
    barcode = Column(String(80), index=True)

    cost_price = Column(Numeric(14, 2), default=0)
    sale_price = Column(Numeric(14, 2), default=0)

    stock_quantity = Column(Numeric(14, 3), default=0, nullable=False)
    min_stock = Column(Numeric(14, 3), default=0, nullable=False)
    max_stock = Column(Numeric(14, 3), default=0, nullable=False)

    status = Column(String(20), default="active", nullable=False, index=True)  # active|inactive|discontinued
    image_url = Column(String(255))

    company = relationship("Company", back_populates="products")
    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    location = relationship("StockLocation")
    entries = relationship("StockEntry", back_populates="product")
    outputs = relationship("StockOutput", back_populates="product")

    __table_args__ = (
        UniqueConstraint("company_id", "sku", name="uq_product_company_sku"),
        Index("ix_product_search", "name", "sku"),
    )

    @property
    def stock_status(self) -> str:
        q = float(self.stock_quantity or 0)
        mn = float(self.min_stock or 0)
        if q <= 0:
            return "out"
        if q <= mn:
            return "low"
        return "ok"

    def to_dict(self):
        return {
            "id": self.id, "sku": self.sku, "name": self.name,
            "description": self.description, "unit": self.unit, "barcode": self.barcode,
            "cost_price": float(self.cost_price or 0),
            "sale_price": float(self.sale_price or 0),
            "stock_quantity": float(self.stock_quantity or 0),
            "min_stock": float(self.min_stock or 0),
            "max_stock": float(self.max_stock or 0),
            "status": self.status,
            "stock_status": self.stock_status,
            "image_url": self.image_url,
            "category": self.category.to_dict() if self.category else None,
            "supplier": {"id": self.supplier.id, "name": self.supplier.name} if self.supplier else None,
            "location": self.location.to_dict() if self.location else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# Stock movements
# ---------------------------------------------------------------------------
class StockEntry(db.Model, TimestampMixin, AuditMixin):
    """Entrada de estoque (compra / devolução / ajuste positivo)."""
    __tablename__ = "stock_entries"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), index=True)

    document = Column(String(60))  # NF, OC, etc.
    quantity = Column(Numeric(14, 3), nullable=False)
    unit_cost = Column(Numeric(14, 2), default=0)
    total_cost = Column(Numeric(14, 2), default=0)
    notes = Column(Text)
    entry_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    status = Column(String(20), default="confirmed", nullable=False, index=True)

    product = relationship("Product", back_populates="entries")
    supplier = relationship("Supplier", back_populates="entries")

    def to_dict(self):
        return {
            "id": self.id, "document": self.document,
            "quantity": float(self.quantity or 0),
            "unit_cost": float(self.unit_cost or 0),
            "total_cost": float(self.total_cost or 0),
            "notes": self.notes,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "status": self.status,
            "product": {"id": self.product.id, "sku": self.product.sku, "name": self.product.name} if self.product else None,
            "supplier": {"id": self.supplier.id, "name": self.supplier.name} if self.supplier else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StockOutput(db.Model, TimestampMixin, AuditMixin):
    """Saída de estoque (venda / consumo / requisição interna)."""
    __tablename__ = "stock_outputs"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), index=True)

    document = Column(String(60))
    quantity = Column(Numeric(14, 3), nullable=False)
    unit_price = Column(Numeric(14, 2), default=0)
    total_price = Column(Numeric(14, 2), default=0)
    reason = Column(String(60), default="consumption")  # sale|consumption|loss|transfer
    destination = Column(String(160))
    notes = Column(Text)
    output_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    status = Column(String(20), default="confirmed", nullable=False, index=True)

    product = relationship("Product", back_populates="outputs")
    employee = relationship("Employee", back_populates="outputs")

    def to_dict(self):
        return {
            "id": self.id, "document": self.document,
            "quantity": float(self.quantity or 0),
            "unit_price": float(self.unit_price or 0),
            "total_price": float(self.total_price or 0),
            "reason": self.reason, "destination": self.destination, "notes": self.notes,
            "output_date": self.output_date.isoformat() if self.output_date else None,
            "status": self.status,
            "product": {"id": self.product.id, "sku": self.product.sku, "name": self.product.name} if self.product else None,
            "employee": {"id": self.employee.id, "name": self.employee.name, "enrollment": self.employee.enrollment} if self.employee else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Unified stock ledger
# ---------------------------------------------------------------------------
class StockMovement(db.Model, TimestampMixin, AuditMixin):
    """Unified stock ledger for reports, audits and future SaaS analytics."""
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    entry_id = Column(Integer, ForeignKey("stock_entries.id"), index=True)
    output_id = Column(Integer, ForeignKey("stock_outputs.id"), index=True)

    movement_type = Column(String(20), nullable=False, index=True)
    document = Column(String(60))
    quantity = Column(Numeric(14, 3), nullable=False)
    unit_value = Column(Numeric(14, 2), default=0)
    total_value = Column(Numeric(14, 2), default=0)
    balance_after = Column(Numeric(14, 3), default=0)
    reason = Column(String(120))
    movement_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    product = relationship("Product")
    entry = relationship("StockEntry")
    output = relationship("StockOutput")

    def to_dict(self):
        return {
            "id": self.id,
            "movement_type": self.movement_type,
            "document": self.document,
            "quantity": float(self.quantity or 0),
            "unit_value": float(self.unit_value or 0),
            "total_value": float(self.total_value or 0),
            "balance_after": float(self.balance_after or 0),
            "reason": self.reason,
            "movement_date": self.movement_date.isoformat() if self.movement_date else None,
            "product": {"id": self.product.id, "sku": self.product.sku, "name": self.product.name} if self.product else None,
        }


# ---------------------------------------------------------------------------
# Employee + Enrollment
# ---------------------------------------------------------------------------
class Employee(db.Model, TimestampMixin, AuditMixin):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    enrollment = Column(String(40), nullable=False, index=True)  # matrícula
    name = Column(String(160), nullable=False, index=True)
    cpf = Column(String(20), index=True)
    email = Column(String(160))
    phone = Column(String(40))
    department = Column(String(120))
    position = Column(String(120))
    hire_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="active", nullable=False, index=True)  # active|leave|terminated
    notes = Column(Text)

    company = relationship("Company", back_populates="employees")
    outputs = relationship("StockOutput", back_populates="employee")

    __table_args__ = (
        UniqueConstraint("company_id", "enrollment", name="uq_employee_company_enrollment"),
    )

    def to_dict(self):
        return {
            "id": self.id, "enrollment": self.enrollment, "name": self.name,
            "cpf": self.cpf, "email": self.email, "phone": self.phone,
            "department": self.department, "position": self.position,
            "hire_date": self.hire_date.isoformat() if self.hire_date else None,
            "status": self.status, "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# ActivityLog (audit trail) + Notification
# ---------------------------------------------------------------------------
class ActivityLog(db.Model, TimestampMixin):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    action = Column(String(60), nullable=False, index=True)  # create|update|delete|login|logout|entry|output
    entity = Column(String(60), nullable=False, index=True)
    entity_id = Column(Integer)
    description = Column(String(400))
    ip = Column(String(60))

    user = relationship("User")

    def to_dict(self):
        return {
            "id": self.id, "action": self.action, "entity": self.entity,
            "entity_id": self.entity_id, "description": self.description,
            "ip": self.ip,
            "user": {"id": self.user.id, "name": self.user.name} if self.user else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Notification(db.Model, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)  # null = broadcast
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    type = Column(String(40), default="info", nullable=False)  # info|warning|success|danger
    title = Column(String(160), nullable=False)
    message = Column(String(500))
    link = Column(String(255))
    read_at = Column(DateTime)

    def to_dict(self):
        return {
            "id": self.id, "type": self.type, "title": self.title,
            "message": self.message, "link": self.link,
            "read": self.read_at is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

