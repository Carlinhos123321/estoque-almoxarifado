from datetime import datetime, timedelta
from sqlalchemy import func, desc
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

        # Atividade de hoje
        today = datetime.utcnow().date()
        start_today = datetime.combine(today, datetime.min.time())
        
        entries_today = StockEntry.query.filter(
            StockEntry.company_id == cid, 
            StockEntry.entry_date >= start_today
        ).count()
        
        outputs_today = StockOutput.query.filter(
            StockOutput.company_id == cid, 
            StockOutput.output_date >= start_today
        ).count()

        # Dados para Gráfico (14 dias)
        chart_movements = self._get_movement_history(days=14)
        
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
            },
            "chart_movements": chart_movements,
            "top_products": top_products,
            "recent_activity": [a.to_dict() for a in ActivityLog.query.filter_by(company_id=cid)
                               .order_by(ActivityLog.created_at.desc()).limit(8).all()],
            "banners": self._get_active_banners()
        }

    def _get_movement_history(self, days=14):
        cid = self.company_id
        start = datetime.utcnow() - timedelta(days=days-1)
        history = []
        for i in range(days):
            day = (start + timedelta(days=i)).date()
            d_start = datetime.combine(day, datetime.min.time())
            d_end = d_start + timedelta(days=1)
            
            ent = db.session.query(func.coalesce(func.sum(StockEntry.quantity), 0))\
                .filter(StockEntry.company_id == cid, StockEntry.entry_date >= d_start, StockEntry.entry_date < d_end).scalar()
            
            out = db.session.query(func.coalesce(func.sum(StockOutput.quantity), 0))\
                .filter(StockOutput.company_id == cid, StockOutput.output_date >= d_start, StockOutput.output_date < d_end).scalar()
            
            history.append({"date": day.isoformat(), "entries": float(ent), "outputs": float(out)})
        return history

    def _get_active_banners(self):
        # Lógica de marketing/ERP SaaS
        return [
            {"id": 1, "image": "img/banners/banner1.jpg", "title": "Gestão de Estoque", "desc": "Controle total de entradas e saídas."},
            {"id": 2, "image": "img/banners/banner2.jpg", "title": "Relatórios em Tempo Real", "desc": "Analise seu inventário com um clique."},
        ]

    def _get_top_moved_products(self, limit=6):
        since = datetime.utcnow() - timedelta(days=30)
        res = (db.session.query(Product, func.sum(StockOutput.quantity).label("qty"))
               .join(StockOutput, StockOutput.product_id == Product.id)
               .filter(Product.company_id == self.company_id, StockOutput.output_date >= since)
               .group_by(Product.id).order_by(desc("qty")).limit(limit).all())
        return [{"id": p.id, "sku": p.sku, "name": p.name, "quantity": float(q or 0), "stock": float(p.stock_quantity or 0)} for p, q in res]