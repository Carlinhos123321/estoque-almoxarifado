"""Initial IMA Stock schema baseline.

This migration is intentionally idempotent so an existing Railway database that
was previously created with db.create_all() can be adopted by Alembic safely.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260617_0001"
down_revision = None
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name):
    return _inspector().has_table(table_name)


def _create_index(name, table_name, columns, unique=False):
    if not _has_table(table_name):
        return
    indexes = {idx["name"] for idx in _inspector().get_indexes(table_name)}
    if name not in indexes:
        op.create_index(name, table_name, columns, unique=unique)


def upgrade():
    if not _has_table("companies"):
        op.create_table(
            "companies",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("legal_name", sa.String(length=200), nullable=True),
            sa.Column("cnpj", sa.String(length=20), nullable=True),
            sa.Column("email", sa.String(length=160), nullable=True),
            sa.Column("phone", sa.String(length=40), nullable=True),
            sa.Column("address", sa.String(length=255), nullable=True),
            sa.Column("city", sa.String(length=120), nullable=True),
            sa.Column("state", sa.String(length=40), nullable=True),
            sa.Column("zipcode", sa.String(length=20), nullable=True),
            sa.Column("logo_url", sa.String(length=255), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("cnpj"),
        )

    if not _has_table("permissions"):
        op.create_table(
            "permissions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("label", sa.String(length=120), nullable=False),
            sa.Column("module", sa.String(length=40), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )

    if not _has_table("roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("label", sa.String(length=80), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("is_system", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    if not _has_table("role_permissions"):
        op.create_table(
            "role_permissions",
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.Column("permission_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("role_id", "permission_id"),
        )

    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("role_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("email", sa.String(length=160), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("avatar_url", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=40), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("last_login_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )

    if not _has_table("categories"):
        op.create_table(
            "categories",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("color", sa.String(length=20), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "name", name="uq_category_company_name"),
        )

    if not _has_table("suppliers"):
        op.create_table(
            "suppliers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("cnpj", sa.String(length=20), nullable=True),
            sa.Column("email", sa.String(length=160), nullable=True),
            sa.Column("phone", sa.String(length=40), nullable=True),
            sa.Column("contact_person", sa.String(length=120), nullable=True),
            sa.Column("address", sa.String(length=255), nullable=True),
            sa.Column("city", sa.String(length=120), nullable=True),
            sa.Column("state", sa.String(length=40), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("stock_locations"):
        op.create_table(
            "stock_locations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("code", sa.String(length=40), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "code", name="uq_location_company_code"),
        )

    if not _has_table("employees"):
        op.create_table(
            "employees",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("enrollment", sa.String(length=40), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("cpf", sa.String(length=20), nullable=True),
            sa.Column("email", sa.String(length=160), nullable=True),
            sa.Column("phone", sa.String(length=40), nullable=True),
            sa.Column("department", sa.String(length=120), nullable=True),
            sa.Column("position", sa.String(length=120), nullable=True),
            sa.Column("hire_date", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "enrollment", name="uq_employee_company_enrollment"),
        )

    if not _has_table("products"):
        op.create_table(
            "products",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("category_id", sa.Integer(), nullable=True),
            sa.Column("supplier_id", sa.Integer(), nullable=True),
            sa.Column("location_id", sa.Integer(), nullable=True),
            sa.Column("sku", sa.String(length=40), nullable=False),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("unit", sa.String(length=20), nullable=False),
            sa.Column("barcode", sa.String(length=80), nullable=True),
            sa.Column("cost_price", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("sale_price", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("stock_quantity", sa.Numeric(precision=14, scale=3), nullable=False),
            sa.Column("min_stock", sa.Numeric(precision=14, scale=3), nullable=False),
            sa.Column("max_stock", sa.Numeric(precision=14, scale=3), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("image_url", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["location_id"], ["stock_locations.id"]),
            sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
            sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "sku", name="uq_product_company_sku"),
        )

    if not _has_table("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=255), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("requested_ip", sa.String(length=60), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )

    if not _has_table("activity_logs"):
        op.create_table(
            "activity_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=60), nullable=False),
            sa.Column("entity", sa.String(length=60), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("description", sa.String(length=400), nullable=True),
            sa.Column("ip", sa.String(length=60), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("type", sa.String(length=40), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("message", sa.String(length=500), nullable=True),
            sa.Column("link", sa.String(length=255), nullable=True),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("stock_entries"):
        op.create_table(
            "stock_entries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("supplier_id", sa.Integer(), nullable=True),
            sa.Column("document", sa.String(length=60), nullable=True),
            sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
            sa.Column("unit_cost", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("total_cost", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("entry_date", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
            sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("stock_outputs"):
        op.create_table(
            "stock_outputs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=True),
            sa.Column("document", sa.String(length=60), nullable=True),
            sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
            sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("total_price", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("reason", sa.String(length=60), nullable=True),
            sa.Column("destination", sa.String(length=160), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("output_date", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("stock_movements"):
        op.create_table(
            "stock_movements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("entry_id", sa.Integer(), nullable=True),
            sa.Column("output_id", sa.Integer(), nullable=True),
            sa.Column("movement_type", sa.String(length=20), nullable=False),
            sa.Column("document", sa.String(length=60), nullable=True),
            sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
            sa.Column("unit_value", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("total_value", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("balance_after", sa.Numeric(precision=14, scale=3), nullable=True),
            sa.Column("reason", sa.String(length=120), nullable=True),
            sa.Column("movement_date", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["entry_id"], ["stock_entries.id"]),
            sa.ForeignKeyConstraint(["output_id"], ["stock_outputs.id"]),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index("ix_activity_logs_action", "activity_logs", ["action"])
    _create_index("ix_activity_logs_company_id", "activity_logs", ["company_id"])
    _create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"])
    _create_index("ix_activity_logs_entity", "activity_logs", ["entity"])
    _create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"])
    _create_index("ix_categories_company_id", "categories", ["company_id"])
    _create_index("ix_categories_created_at", "categories", ["created_at"])
    _create_index("ix_companies_cnpj", "companies", ["cnpj"], unique=True)
    _create_index("ix_companies_created_at", "companies", ["created_at"])
    _create_index("ix_employees_company_id", "employees", ["company_id"])
    _create_index("ix_employees_cpf", "employees", ["cpf"])
    _create_index("ix_employees_created_at", "employees", ["created_at"])
    _create_index("ix_employees_enrollment", "employees", ["enrollment"])
    _create_index("ix_employees_name", "employees", ["name"])
    _create_index("ix_employees_status", "employees", ["status"])
    _create_index("ix_notifications_company_id", "notifications", ["company_id"])
    _create_index("ix_notifications_created_at", "notifications", ["created_at"])
    _create_index("ix_notifications_user_id", "notifications", ["user_id"])
    _create_index("ix_password_reset_tokens_created_at", "password_reset_tokens", ["created_at"])
    _create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])
    _create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    _create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    _create_index("ix_permissions_code", "permissions", ["code"], unique=True)
    _create_index("ix_permissions_created_at", "permissions", ["created_at"])
    _create_index("ix_permissions_module", "permissions", ["module"])
    _create_index("ix_product_search", "products", ["name", "sku"])
    _create_index("ix_products_barcode", "products", ["barcode"])
    _create_index("ix_products_category_id", "products", ["category_id"])
    _create_index("ix_products_company_id", "products", ["company_id"])
    _create_index("ix_products_created_at", "products", ["created_at"])
    _create_index("ix_products_location_id", "products", ["location_id"])
    _create_index("ix_products_name", "products", ["name"])
    _create_index("ix_products_sku", "products", ["sku"])
    _create_index("ix_products_status", "products", ["status"])
    _create_index("ix_products_supplier_id", "products", ["supplier_id"])
    _create_index("ix_roles_created_at", "roles", ["created_at"])
    _create_index("ix_roles_name", "roles", ["name"], unique=True)
    _create_index("ix_stock_entries_company_id", "stock_entries", ["company_id"])
    _create_index("ix_stock_entries_created_at", "stock_entries", ["created_at"])
    _create_index("ix_stock_entries_entry_date", "stock_entries", ["entry_date"])
    _create_index("ix_stock_entries_product_id", "stock_entries", ["product_id"])
    _create_index("ix_stock_entries_status", "stock_entries", ["status"])
    _create_index("ix_stock_entries_supplier_id", "stock_entries", ["supplier_id"])
    _create_index("ix_stock_locations_company_id", "stock_locations", ["company_id"])
    _create_index("ix_stock_locations_created_at", "stock_locations", ["created_at"])
    _create_index("ix_stock_movements_company_id", "stock_movements", ["company_id"])
    _create_index("ix_stock_movements_created_at", "stock_movements", ["created_at"])
    _create_index("ix_stock_movements_entry_id", "stock_movements", ["entry_id"])
    _create_index("ix_stock_movements_movement_date", "stock_movements", ["movement_date"])
    _create_index("ix_stock_movements_movement_type", "stock_movements", ["movement_type"])
    _create_index("ix_stock_movements_output_id", "stock_movements", ["output_id"])
    _create_index("ix_stock_movements_product_id", "stock_movements", ["product_id"])
    _create_index("ix_stock_outputs_company_id", "stock_outputs", ["company_id"])
    _create_index("ix_stock_outputs_created_at", "stock_outputs", ["created_at"])
    _create_index("ix_stock_outputs_employee_id", "stock_outputs", ["employee_id"])
    _create_index("ix_stock_outputs_output_date", "stock_outputs", ["output_date"])
    _create_index("ix_stock_outputs_product_id", "stock_outputs", ["product_id"])
    _create_index("ix_stock_outputs_status", "stock_outputs", ["status"])
    _create_index("ix_suppliers_cnpj", "suppliers", ["cnpj"])
    _create_index("ix_suppliers_company_id", "suppliers", ["company_id"])
    _create_index("ix_suppliers_created_at", "suppliers", ["created_at"])
    _create_index("ix_suppliers_name", "suppliers", ["name"])
    _create_index("ix_users_company_id", "users", ["company_id"])
    _create_index("ix_users_created_at", "users", ["created_at"])
    _create_index("ix_users_email", "users", ["email"], unique=True)
    _create_index("ix_users_role_id", "users", ["role_id"])
    _create_index("ix_users_status", "users", ["status"])


def downgrade():
    for table_name in [
        "stock_movements",
        "stock_outputs",
        "stock_entries",
        "notifications",
        "activity_logs",
        "password_reset_tokens",
        "products",
        "employees",
        "stock_locations",
        "suppliers",
        "categories",
        "users",
        "role_permissions",
        "roles",
        "permissions",
        "companies",
    ]:
        if _has_table(table_name):
            op.drop_table(table_name)
