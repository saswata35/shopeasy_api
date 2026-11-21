from typing import Any, Dict, List
from shopeasy_api.db import get_cursor

def get_all_reports() -> List[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, name, endpoint, description
            FROM reports
            ORDER BY id ASC
            """
        )
        return list(cur.fetchall())

def sales_by_product() -> List[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                p.id AS product_id,
                p.name AS product_name,
                COALESCE(SUM(oi.quantity), 0) AS units_sold,
                COALESCE(SUM(oi.quantity * p.price), 0) AS revenue
            FROM products p
            LEFT JOIN order_items oi ON oi.product_id = p.id
            LEFT JOIN orders o ON o.id = oi.order_id AND o.status != 'cancelled'
            GROUP BY p.id, p.name
            ORDER BY revenue DESC, units_sold DESC, p.id ASC
            """
        )
        return list(cur.fetchall())


def top_customers(limit: int = 3) -> List[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                c.id AS customer_id,
                c.name AS customer_name,
                c.email,
                COUNT(DISTINCT o.id) AS delivered_orders,
                COALESCE(SUM(oi.quantity * p.price), 0) AS total_spent
            FROM customers c
            JOIN orders o ON o.customer_id = c.id AND o.status = 'delivered'
            JOIN order_items oi ON oi.order_id = o.id
            JOIN products p ON p.id = oi.product_id
            GROUP BY c.id, c.name, c.email
            ORDER BY total_spent DESC, c.id ASC
            LIMIT %s
            """,
            (limit,),
        )
        return list(cur.fetchall())