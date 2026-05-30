from datetime import datetime
from decimal import Decimal
from ..extensions import db
from ..models import Product, StockEntry, StockOutput, StockMovement, Notification
from .audit_service import AuditService

class StockService:
    """Engine de movimentação de estoque com validação e integridade SaaS."""

    def __init__(self, company_id, user_id):
        self.company_id = company_id
        self.user_id = user_id

    def register_entry(self, data):
        """Processa entrada de mercadoria e atualiza saldo."""
        pid = data.get("product_id")
        qty = Decimal(str(data.get("quantity") or 0))

        if qty <= 0: raise ValueError("Quantidade deve ser positiva.")
        
        # Isolamento de Tenant na busca
        product = Product.query.filter_by(company_id=self.company_id, id=pid).first_or_404()
        
        entry = StockEntry(
            company_id=self.company_id,
            product_id=product.id,
            supplier_id=data.get("supplier_id") or product.supplier_id,
            document=data.get("document"),
            quantity=qty,
            unit_cost=Decimal(str(data.get("unit_cost") or product.cost_price)),
            total_cost=qty * Decimal(str(data.get("unit_cost") or product.cost_price)),
            entry_date=datetime.utcnow(),
            status="confirmed",
            created_by_id=self.user_id
        )

        product.stock_quantity += qty
        db.session.add(entry)
        db.session.flush()

        self._add_movement(product, "entry", qty, entry.unit_cost, entry.document, entry.id, None)
        db.session.commit()
        
        AuditService.log("entry", "stock_entry", entry.id, f"Entrada: {qty} {product.sku}", self.company_id, self.user_id)
        return entry

    def register_output(self, data):
        """Processa saída de mercadoria com checagem de disponibilidade."""
        pid = data.get("product_id")
        qty = Decimal(str(data.get("quantity") or 0))

        if qty <= 0: raise ValueError("Quantidade inválida.")
        
        product = Product.query.filter_by(company_id=self.company_id, id=pid).first_or_404()

        if product.stock_quantity < qty:
            raise ValueError(f"Estoque insuficiente. Disponível: {product.stock_quantity}")

        output = StockOutput(
            company_id=self.company_id,
            product_id=product.id,
            employee_id=data.get("employee_id"),
            reason=data.get("reason", "consumption"),
            document=data.get("document"),
            quantity=qty,
            unit_price=Decimal(str(data.get("unit_price") or product.sale_price)),
            total_price=qty * Decimal(str(data.get("unit_price") or product.sale_price)),
            output_date=datetime.utcnow(),
            status="confirmed",
            created_by_id=self.user_id
        )

        product.stock_quantity -= qty
        db.session.add(output)
        db.session.flush()

        self._add_movement(product, "output", -qty, output.unit_price, output.document, None, output.id)
        
        # Checagem automática de estoque crítico
        if product.stock_quantity <= product.min_stock:
            self._notify_low_stock(product)
            
        db.session.commit()
        AuditService.log("output", "stock_output", output.id, f"Saída: {qty} {product.sku}", self.company_id, self.user_id)
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
            created_by_id=self.user_id
        )
        db.session.add(mov)

    def _notify_low_stock(self, product):
        notif = Notification(
            company_id=self.company_id,
            type="warning",
            title="Alerta de Reposição",
            message=f"O produto {product.sku} atingiu o nível mínimo ({product.min_stock}).",
            link=f"/app/estoque?search={product.sku}"
        )
        db.session.add(notif)