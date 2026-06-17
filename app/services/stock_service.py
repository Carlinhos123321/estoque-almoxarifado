from datetime import datetime
from decimal import Decimal, InvalidOperation

from ..extensions import db
from ..models import Employee, Notification, Product, StockEntry, StockMovement, StockOutput, Supplier
from .audit_service import AuditService


class StockService:
    """Stock movement engine with tenant validation."""

    def __init__(self, company_id, user_id):
        self.company_id = company_id
        self.user_id = user_id

    def _decimal(self, value, field_label, default="0"):
        try:
            number = Decimal(str(value if value not in (None, "") else default))
        except (InvalidOperation, ValueError):
            raise ValueError(f"{field_label} deve ser um numero valido.")
        return number

    def _tenant_fk(self, model, value, field_label):
        if value in (None, ""):
            return None
        try:
            item_id = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field_label} invalido.")
        if not model.query.filter_by(company_id=self.company_id, id=item_id).first():
            raise ValueError(f"{field_label} nao pertence a esta empresa.")
        return item_id

    def register_entry(self, data):
        """Process an inbound stock movement and update balance."""
        pid = data.get("product_id")
        qty = self._decimal(data.get("quantity"), "Quantidade")
        if qty <= 0:
            raise ValueError("Quantidade deve ser positiva.")

        product = Product.query.filter_by(company_id=self.company_id, id=pid).first_or_404()
        supplier_id = self._tenant_fk(Supplier, data.get("supplier_id"), "Fornecedor") or product.supplier_id
        unit_cost = self._decimal(data.get("unit_cost"), "Custo unitario", product.cost_price or 0)

        entry = StockEntry(
            company_id=self.company_id,
            product_id=product.id,
            supplier_id=supplier_id,
            document=data.get("document"),
            quantity=qty,
            unit_cost=unit_cost,
            total_cost=qty * unit_cost,
            notes=data.get("notes"),
            entry_date=datetime.utcnow(),
            status="confirmed",
            created_by_id=self.user_id,
        )

        product.stock_quantity = (product.stock_quantity or 0) + qty
        db.session.add(entry)
        db.session.flush()

        self._add_movement(product, "entry", qty, entry.unit_cost, entry.document, entry.id, None)
        db.session.commit()

        AuditService.log("entry", "stock_entry", entry.id, f"Entrada: {qty} {product.sku}", self.company_id, self.user_id)
        return entry

    def register_output(self, data):
        """Process an outbound stock movement after checking availability."""
        pid = data.get("product_id")
        qty = self._decimal(data.get("quantity"), "Quantidade")
        if qty <= 0:
            raise ValueError("Quantidade invalida.")

        product = Product.query.filter_by(company_id=self.company_id, id=pid).first_or_404()
        if product.stock_quantity < qty:
            raise ValueError(f"Estoque insuficiente. Disponivel: {product.stock_quantity}")

        employee_id = self._tenant_fk(Employee, data.get("employee_id"), "Funcionario")
        unit_price = self._decimal(data.get("unit_price"), "Preco unitario", product.sale_price or 0)

        output = StockOutput(
            company_id=self.company_id,
            product_id=product.id,
            employee_id=employee_id,
            reason=data.get("reason", "consumption"),
            destination=data.get("destination"),
            document=data.get("document"),
            quantity=qty,
            unit_price=unit_price,
            total_price=qty * unit_price,
            notes=data.get("notes"),
            output_date=datetime.utcnow(),
            status="confirmed",
            created_by_id=self.user_id,
        )

        product.stock_quantity -= qty
        db.session.add(output)
        db.session.flush()

        self._add_movement(product, "output", -qty, output.unit_price, output.document, None, output.id)

        if product.stock_quantity <= product.min_stock:
            self._notify_low_stock(product)

        db.session.commit()
        AuditService.log("output", "stock_output", output.id, f"Saida: {qty} {product.sku}", self.company_id, self.user_id)
        return output

    def _add_movement(self, product, m_type, qty, val, doc, entry_id, output_id):
        mov = StockMovement(
            company_id=self.company_id,
            product_id=product.id,
            movement_type=m_type,
            quantity=qty,
            unit_value=val,
            total_value=abs(qty * val),
            document=doc,
            balance_after=product.stock_quantity,
            entry_id=entry_id,
            output_id=output_id,
            movement_date=datetime.utcnow(),
            created_by_id=self.user_id,
        )
        db.session.add(mov)

    def _notify_low_stock(self, product):
        notif = Notification(
            company_id=self.company_id,
            type="warning",
            title="Alerta de Reposicao",
            message=f"O produto {product.sku} atingiu o nivel minimo ({product.min_stock}).",
            link=f"/app/estoque?search={product.sku}",
        )
        db.session.add(notif)
