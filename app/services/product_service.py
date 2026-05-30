from decimal import Decimal
from sqlalchemy import or_, desc
from ..extensions import db
from ..models import Product
from ..helpers import paginate_query

class ProductService:
    """Encapsula toda a regra de negócio relacionada ao catálogo de produtos."""

    def __init__(self, company_id, user_id):
        self.company_id = company_id
        self.user_id = user_id

    def list_products(self, filters: dict, page=1, per_page=25):
        query = Product.query.filter_by(company_id=self.company_id)

        if search := filters.get("search"):
            like = f"%{search}%"
            query = query.filter(or_(
                Product.name.ilike(like), 
                Product.sku.ilike(like),
                Product.barcode.ilike(like)
            ))

        if cat_id := filters.get("category_id"):
            query = query.filter(Product.category_id == cat_id)
        
        if sup_id := filters.get("supplier_id"):
            query = query.filter(Product.supplier_id == sup_id)

        if stock_status := filters.get("stock_status"):
            if stock_status == "out":
                query = query.filter(Product.stock_quantity <= 0)
            elif stock_status == "low":
                query = query.filter(Product.stock_quantity <= Product.min_stock, Product.stock_quantity > 0)

        sort_col = getattr(Product, filters.get("sort", "name"), Product.name)
        direction = desc if filters.get("dir") == "desc" else lambda x: x
        query = query.order_by(direction(sort_col))

        return paginate_query(query, page=page, per_page=per_page)

    def create(self, data: dict):
        sku = data.get("sku", "").strip()
        if Product.query.filter_by(company_id=self.company_id, sku=sku).first():
            raise ValueError("SKU duplicado para esta empresa.")

        product = Product(
            company_id=self.company_id,
            created_by_id=self.user_id,
            sku=sku,
            name=data.get("name", "").strip(),
            description=data.get("description"),
            unit=data.get("unit", "UN").upper(),
            cost_price=Decimal(str(data.get("cost_price", 0))),
            sale_price=Decimal(str(data.get("sale_price", 0))),
            stock_quantity=Decimal(str(data.get("stock_quantity", 0))),
            min_stock=Decimal(str(data.get("min_stock", 0))),
            category_id=data.get("category_id"),
            supplier_id=data.get("supplier_id"),
            status="active"
        )
        db.session.add(product)
        db.session.commit()
        return product

    def update(self, product_id, data: dict):
        product = Product.query.filter_by(company_id=self.company_id, id=product_id).first_or_404()
        
        editable_fields = ["name", "description", "unit", "cost_price", "sale_price", "min_stock", "category_id", "supplier_id", "status"]
        for field in editable_fields:
            if field in data:
                val = data[field]
                if "price" in field or "stock" in field:
                    val = Decimal(str(val or 0))
                setattr(product, field, val)

        product.updated_by_id = self.user_id
        db.session.commit()
        return product