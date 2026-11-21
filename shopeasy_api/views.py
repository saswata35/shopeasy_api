from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List


def format_money(val: Any) -> str:
    if val is None:
        return "0.00"
    dval = val if isinstance(val, Decimal) else Decimal(str(val))
    return f"{dval:.2f}"


def format_date(val: Any) -> str:
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()
    return str(val)


def product_view(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "price": format_money(row["price"]),
        "stock": int(row["stock"]),
    }


def product_list_view(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [product_view(r) for r in rows]


def customer_view(row: Dict[str, Any]) -> Dict[str, Any]:
    created_at_val = row.get("created_at")
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "city": row.get("city"),
        "created_at": format_date(created_at_val) if created_at_val else None,
    }


def customer_list_view(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [customer_view(r) for r in rows]


def order_list_view(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": r["id"],
            "order_date": format_date(r["order_date"]),
            "status": r["status"],
            "customer_id": r["customer_id"],
            "customer_name": r["customer_name"],
            "total": format_money(r.get("total", Decimal("0.00"))),
        }
        for r in rows
    ]


def order_item_view(row: Dict[str, Any]) -> Dict[str, Any]:
    price = Decimal(str(row["price"]))
    qty = int(row["quantity"])
    line_total = price * qty
    return {
        "id": row["id"],
        "product_id": row["product_id"],
        "product_name": row.get("product_name", row.get("name")),
        "price": format_money(price),
        "quantity": qty,
        "line_total": format_money(line_total),
    }


def order_detail_view(order_row: Dict[str, Any], item_rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    items = [order_item_view(item) for item in item_rows]
    total_dec = sum((Decimal(item["line_total"]) for item in items), Decimal("0.00"))
    customer_info = order_row.get("customer") or {
        "id": order_row["customer_id"],
        "name": order_row.get("customer_name", order_row.get("name")),
        "email": order_row.get("customer_email", order_row.get("email")),
    }
    return {
        "id": order_row["id"],
        "order_date": format_date(order_row["order_date"]),
        "status": order_row["status"],
        "customer": customer_info,
        "items": items,
        "total": format_money(total_dec),
    }


def sales_by_product_view(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "product_id": r.get("product_id", r.get("id")),
            "product_name": r.get("product_name", r.get("name")),
            "units_sold": int(r.get("units_sold", 0)),
            "revenue": format_money(r.get("revenue", Decimal("0.00"))),
        }
        for r in rows
    ]


def top_customers_view(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "customer_id": r.get("customer_id", r.get("id")),
            "customer_name": r.get("customer_name", r.get("name")),
            "email": r.get("email"),
            "delivered_orders": int(r.get("delivered_orders", 0)),
            "total_spent": format_money(r.get("total_spent", Decimal("0.00"))),
        }
        for r in rows
    ]