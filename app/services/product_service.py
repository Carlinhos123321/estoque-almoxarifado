import re
import unicodedata
from decimal import Decimal, InvalidOperation
from sqlalchemy import or_, desc
from ..extensions import db
from ..models import Category, Product, StockLocation, Supplier
from ..helpers import paginate_query

class ProductService:
    """Encapsula toda a regra de negócio relacionada ao catálogo de produtos."""

    def __init__(self, company_id, user_id):
        self.company_id = company_id
        self.user_id = user_id

    def _decimal(self, value, field_label):
        try:
            number = Decimal(str(value if value not in (None, "") else 0))
        except (InvalidOperation, ValueError):
            raise ValueError(f"{field_label} deve ser um número válido.")
        if number < 0:
            raise ValueError(f"{field_label} não pode ser negativo.")
        return number

    def _tenant_fk(self, model, value, field_label):
        if value in (None, ""):
            return None
        try:
            item_id = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field_label} inválido.")
        if not model.query.filter_by(company_id=self.company_id, id=item_id).first():
            raise ValueError(f"{field_label} não encontrado para esta empresa.")
        return item_id

    def _location_from_name(self, value):
        name = (value or "").strip()
        if not name:
            return None

        location = StockLocation.query.filter(
            StockLocation.company_id == self.company_id,
            or_(StockLocation.name.ilike(name), StockLocation.code.ilike(name)),
        ).first()
        if location:
            return location.id

        normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
        base_code = re.sub(r"[^A-Za-z0-9]+", "-", normalized.upper()).strip("-") or "LOCAL"
        code = base_code[:40]
        suffix = 2
        while StockLocation.query.filter_by(company_id=self.company_id, code=code).first():
            suffix_text = f"-{suffix}"
            code = f"{base_code[:40 - len(suffix_text)]}{suffix_text}"
            suffix += 1

        location = StockLocation(company_id=self.company_id, code=code, name=name)
        db.session.add(location)
        db.session.flush()
        return location.id

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

        return paginate_query(query, default_per_page=per_page)

    def create(self, data: dict):
        sku = (data.get("sku") or "").strip()
        name = (data.get("name") or "").strip()
        if not sku:
            raise ValueError("SKU é obrigatório.")
        if not name:
            raise ValueError("Nome do produto é obrigatório.")
        if Product.query.filter_by(company_id=self.company_id, sku=sku).first():
            raise ValueError("SKU duplicado para esta empresa.")

        product = Product(
            company_id=self.company_id,
            created_by_id=self.user_id,
            sku=sku,
            name=name,
            description=data.get("description"),
            unit=(data.get("unit") or "UN").strip().upper(),
            cost_price=self._decimal(data.get("cost_price"), "Custo"),
            sale_price=self._decimal(data.get("sale_price"), "Preço de venda"),
            stock_quantity=self._decimal(data.get("stock_quantity"), "Estoque inicial"),
            min_stock=self._decimal(data.get("min_stock"), "Estoque mínimo"),
            max_stock=self._decimal(data.get("max_stock"), "Estoque máximo"),
            category_id=self._tenant_fk(Category, data.get("category_id"), "Categoria"),
            supplier_id=self._tenant_fk(Supplier, data.get("supplier_id"), "Fornecedor"),
            location_id=self._location_from_name(data.get("location_name"))
                if "location_name" in data
                else self._tenant_fk(StockLocation, data.get("location_id"), "Local de estoque"),
            status="active"
        )
        db.session.add(product)
        db.session.commit()
        return product

    def update(self, product_id, data: dict):
        product = Product.query.filter_by(company_id=self.company_id, id=product_id).first_or_404()
        
        editable_fields = ["sku", "name", "description", "unit", "cost_price", "sale_price", "min_stock", "max_stock", "category_id", "supplier_id", "location_id", "status"]
        for field in editable_fields:
            if field in data:
                val = data[field]
                if "price" in field or "stock" in field:
                    labels = {
                        "cost_price": "Custo",
                        "sale_price": "Preço de venda",
                        "min_stock": "Estoque mínimo",
                        "max_stock": "Estoque máximo",
                    }
                    val = self._decimal(val, labels.get(field, field))
                elif field == "sku":
                    val = (val or "").strip()
                    if not val:
                        raise ValueError("SKU é obrigatório.")
                    duplicate = Product.query.filter(
                        Product.company_id == self.company_id,
                        Product.sku == val,
                        Product.id != product_id,
                    ).first()
                    if duplicate:
                        raise ValueError("SKU duplicado para esta empresa.")
                elif field == "name":
                    val = (val or "").strip()
                    if not val:
                        raise ValueError("Nome do produto é obrigatório.")
                elif field == "unit":
                    val = (val or "UN").strip().upper()
                elif field == "category_id":
                    val = self._tenant_fk(Category, val, "Categoria")
                elif field == "supplier_id":
                    val = self._tenant_fk(Supplier, val, "Fornecedor")
                elif field == "location_id":
                    val = self._tenant_fk(StockLocation, val, "Local de estoque")
                setattr(product, field, val)

        if "location_name" in data:
            product.location_id = self._location_from_name(data.get("location_name"))

        product.updated_by_id = self.user_id
        db.session.commit()
        return product
