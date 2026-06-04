from datetime import datetime, timedelta, timezone
from sqlalchemy import func, desc, or_
from ..extensions import db
from ..models import (
    Product, StockEntry, StockOutput, Supplier, Employee, 
    ActivityLog, Category
)

class DashboardService:
    """Serviço especializado em processar métricas e KPIs do ERP."""
    
    def __init__(self, company_id):
        self.company_id = company_id

    def get_summary_metrics(self):
        """Retorna o consolidado de indicadores para o painel principal."""
        cid = self.company_id
        
        # Consultas baseadas em tenant
        total_products = Product.query.filter_by(company_id=cid).count()
        
        # Cálculo de volume e valor contábil
        inventory_stats = db.session.query(
            func.coalesce(func.sum(Product.stock_quantity), 0),
            func.coalesce(func.sum(Product.stock_quantity * Product.cost_price), 0)
        ).filter(Product.company_id == cid).first()

        # Alertas de estoque
        low_stock = Product.query.filter(
            Product.company_id == cid,
            Product.stock_quantity <= Product.min_stock,
            Product.stock_quantity > 0
        ).count()
        
        out_stock = Product.query.filter(
            Product.company_id == cid,
            Product.stock_quantity <= 0
        ).count()

        # Produtos em estoque crítico: zerados ou abaixo do mínimo
        critical_products = Product.query.filter(
            Product.company_id == cid,
            Product.status == "active",
            or_(
                Product.stock_quantity <= Product.min_stock,
                Product.stock_quantity <= 0
            )
        ).order_by(
            Product.stock_quantity.asc()
        ).limit(10).all()

        # Atividade de hoje
        now = datetime.now(timezone.utc)
        today = now.date()
        start_today = datetime.combine(today, datetime.min.time())
        entries_today = StockEntry.query.filter(
            StockEntry.company_id == cid, 
            StockEntry.entry_date >= start_today
        ).count()
        
        outputs_today = StockOutput.query.filter(
            StockOutput.company_id == cid, 
            StockOutput.output_date >= start_today
        ).count()

        # Resumo Mensal (Mês Atual)
        start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        entries_month = db.session.query(func.coalesce(func.sum(StockEntry.quantity), 0)).filter(
            StockEntry.company_id == cid, StockEntry.entry_date >= start_month
        ).scalar()
        
        outputs_month = db.session.query(func.coalesce(func.sum(StockOutput.quantity), 0)).filter(
            StockOutput.company_id == cid, StockOutput.output_date >= start_month
        ).scalar()

        categories_count = Category.query.filter_by(company_id=cid).count()

        # Dados para Gráfico (14 dias)
        chart_movements = self._get_movement_history(days=14)
        
        # Distribuição por Categoria (Real)
        cat_data = db.session.query(
            Category.name, func.count(Product.id)
        ).join(Product, Product.category_id == Category.id)\
         .filter(Category.company_id == cid)\
         .group_by(Category.id).all()

        # Top Produtos (Ranking)
        top_products = self._get_top_moved_products(limit=6)

        return {
            "kpi": {
                "total_products": total_products,
                "total_units": float(inventory_stats[0]),
                "inventory_value": round(float(inventory_stats[1]), 2),
                "low_stock": low_stock,
                "out_stock": out_stock,
                "suppliers": Supplier.query.filter_by(company_id=cid, active=True).count(),
                "employees": Employee.query.filter_by(company_id=cid, status="active").count(),
                "entries_today": entries_today,
                "outputs_today": outputs_today,
                "entries_month": float(entries_month),
                "outputs_month": float(outputs_month),
                "categories_count": categories_count
            },
            "chart_movements": chart_movements,
            "categories_chart": [{"name": name, "count": count} for name, count in cat_data],
            "critical_stock": [
                {"sku": p.sku, "name": p.name, "stock": float(p.stock_quantity), "min": float(p.min_stock)} 
                for p in critical_products
            ]
        }

    def _get_movement_history(self, days=14):
        cid = self.company_id
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days-1)).date()
        history = []
        for i in range(days):
            day = start + timedelta(days=i)
            d_start = datetime.combine(day, datetime.min.time())
            d_end = d_start + timedelta(days=1)
            
            ent = db.session.query(func.coalesce(func.sum(StockEntry.quantity), 0))\
                .filter(StockEntry.company_id == cid, StockEntry.entry_date >= d_start, StockEntry.entry_date < d_end).scalar()
            
            out = db.session.query(func.coalesce(func.sum(StockOutput.quantity), 0))\
                .filter(StockOutput.company_id == cid, StockOutput.output_date >= d_start, StockOutput.output_date < d_end).scalar()
            
            history.append({"date": day.isoformat(), "entries": float(ent), "outputs": float(out)})
        return history

    def _get_top_moved_products(self, limit=6):
        since = datetime.now(timezone.utc) - timedelta(days=30)
        res = (db.session.query(Product, func.sum(StockOutput.quantity).label("qty"))
               .join(StockOutput, StockOutput.product_id == Product.id)
               .filter(Product.company_id == self.company_id, StockOutput.output_date >= since)
               .group_by(Product.id).order_by(desc("qty")).limit(limit).all())
        return [{"id": p.id, "sku": p.sku, "name": p.name, "quantity": float(q or 0), "stock": float(p.stock_quantity or 0)} for p, q in res]
