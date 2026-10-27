"""Small domain model demonstrating classes, inheritance and polymorphism."""
from __future__ import annotations
from datetime import date, datetime


class Product:
    """Common product model used by inventory pages."""
    def __init__(self, row: dict):
        self.product_id = row.get("product_id")
        self.sku = row.get("sku", "")
        self.name = row.get("name", "")
        self.category_name = row.get("category_name", "Uncategorised")
        self.supplier_name = row.get("supplier_name") or "-"
        self.unit_price = float(row.get("unit_price") or 0)
        self.product_type = row.get("product_type", "STANDARD")
        self.expiry_date = row.get("expiry_date")
        self.reorder_level = int(row.get("reorder_level") or 0)
        self.is_active = row.get("is_active", "Y")

    @property
    def display_type(self) -> str:
        return "Standard"

    @property
    def expiry_warning(self) -> str:
        return "Not applicable"


class PerishableProduct(Product):
    """Specialized product with an expiry-date status."""
    @property
    def display_type(self) -> str:
        return "Perishable"

    @property
    def expiry_warning(self) -> str:
        if not self.expiry_date:
            return "Expiry date missing"
        value = self.expiry_date
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, str):
            try:
                value = date.fromisoformat(value[:10])
            except ValueError:
                return str(value)
        days = (value - date.today()).days
        if days < 0:
            return f"Expired {abs(days)} day(s) ago"
        if days <= 7:
            return f"Expires in {days} day(s)"
        return f"Expires {value.isoformat()}"


def product_from_row(row: dict) -> Product:
    """Factory demonstrates polymorphism: returns a suitable product subtype."""
    if str(row.get("product_type", "STANDARD")).upper() == "PERISHABLE":
        return PerishableProduct(row)
    return Product(row)
