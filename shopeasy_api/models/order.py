from typing import Any, Dict, List, Optional
from shopeasy_api.db import get_cursor, transaction
from shopeasy_api.errors import ApiError


def _fetch_order_item_with_product(cur, item_id: int) -> Optional[Dict[str, Any]]:
    cur.execute(
        """
        SELECT
            oi.id,
            oi.order_id,
            oi.product_id,
            p.name AS product_name,
            p.price,
            oi.quantity
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.id = %s
        """,
        (item_id,),
    )
    return cur.fetchone()


def get_all(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            o.id,
            o.order_date,
            o.status,
            o.customer_id,
            c.name AS customer_name,
            COALESCE(SUM(oi.quantity * p.price), 0) AS total
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.id = oi.product_id
        WHERE 1=1
    """
    params: List[Any] = []

    if status is not None and status.strip() != "":
        sql += " AND o.status = %s"
        params.append(status.strip())
    if customer_id is not None:
        sql += " AND o.customer_id = %s"
        params.append(customer_id)

    sql += """
        GROUP BY o.id, o.order_date, o.status, o.customer_id, c.name
        ORDER BY o.id ASC
    """

    with get_cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def get_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                o.id,
                o.order_date,
                o.status,
                o.customer_id,
                c.name AS customer_name,
                c.email AS customer_email
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            WHERE o.id = %s
            """,
            (order_id,),
        )
        return cur.fetchone()


def get_items(order_id: int) -> Optional[List[Dict[str, Any]]]:
    with get_cursor() as cur:
        cur.execute("SELECT id FROM orders WHERE id = %s", (order_id,))
        if cur.fetchone() is None:
            return None

        cur.execute(
            """
            SELECT
                oi.id,
                oi.order_id,
                oi.product_id,
                p.name AS product_name,
                p.price,
                oi.quantity
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = %s
            ORDER BY oi.id ASC
            """,
            (order_id,),
        )
        return list(cur.fetchall())


def create_order(customer_id: int, items: List[Dict[str, int]]) -> int:
    """
    Creates an order, order_items, and decrements product stock atomically.
    Raises ApiError (404 or 409) so the transaction rolls back cleanly.
    """
    with transaction() as cur:
        cur.execute("SELECT id FROM customers WHERE id = %s", (customer_id,))
        if cur.fetchone() is None:
            raise ApiError(404, f"Customer {customer_id} does not exist")

        # Lock and validate all products before inserting any rows
        for item in items:
            pid = item["product_id"]
            qty = item["quantity"]
            cur.execute(
                "SELECT id, name, stock FROM products WHERE id = %s FOR UPDATE",
                (pid,),
            )
            prod = cur.fetchone()
            if prod is None:
                raise ApiError(404, f"Product {pid} does not exist")
            if prod["stock"] < qty:
                raise ApiError(
                    409,
                    f"Insufficient stock for product {pid} (available: {prod['stock']}, requested: {qty})",
                )

        cur.execute(
            """
            INSERT INTO orders (customer_id, order_date, status)
            VALUES (%s, CURRENT_DATE, 'pending')
            RETURNING id
            """,
            (customer_id,),
        )
        order_id = cur.fetchone()["id"]

        for item in items:
            pid = item["product_id"]
            qty = item["quantity"]
            cur.execute(
                """
                INSERT INTO order_items (order_id, product_id, quantity)
                VALUES (%s, %s, %s)
                """,
                (order_id, pid, qty),
            )
            cur.execute(
                """
                UPDATE products
                SET stock = stock - %s
                WHERE id = %s
                """,
                (qty, pid),
            )

        return order_id


def update_status(order_id: int, new_status: str) -> Dict[str, Any]:
    with transaction() as cur:
        cur.execute(
            "SELECT id, status FROM orders WHERE id = %s FOR UPDATE",
            (order_id,),
        )
        existing = cur.fetchone()
        if existing is None:
            raise ApiError(404, f"Order {order_id} does not exist")

        current_status = existing["status"]
        if current_status == new_status:
            raise ApiError(409, f"Order is already {current_status}")

        if current_status != "pending":
            raise ApiError(
                409,
                f"Cannot transition order status from '{current_status}' to '{new_status}'",
            )

        if new_status == "cancelled":
            cur.execute(
                "SELECT product_id, quantity FROM order_items WHERE order_id = %s",
                (order_id,),
            )
            order_rows = cur.fetchall()
            for r in order_rows:
                cur.execute(
                    "UPDATE products SET stock = stock + %s WHERE id = %s",
                    (r["quantity"], r["product_id"]),
                )

        cur.execute(
            "UPDATE orders SET status = %s WHERE id = %s",
            (new_status, order_id),
        )

    detail = get_by_id(order_id)
    items = get_items(order_id) or []
    return {"order": detail, "items": items}


def delete_cancelled_order(order_id: int) -> None:
    with transaction() as cur:
        cur.execute(
            "SELECT id, status FROM orders WHERE id = %s FOR UPDATE",
            (order_id,),
        )
        existing = cur.fetchone()
        if existing is None:
            raise ApiError(404, f"Order {order_id} does not exist")

        if existing["status"] != "cancelled":
            raise ApiError(
                409,
                f"Only cancelled orders can be deleted (current status: '{existing['status']}')",
            )

        cur.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))
        cur.execute("DELETE FROM orders WHERE id = %s", (order_id,))


def add_item_to_pending_order(order_id: int, product_id: int, quantity: int) -> Dict[str, Any]:
    """Adds an item (or increases quantity if already present) on a pending order and decrements stock."""
    with transaction() as cur:
        cur.execute("SELECT id, status FROM orders WHERE id = %s FOR UPDATE", (order_id,))
        order_row = cur.fetchone()
        if order_row is None:
            raise ApiError(404, f"Order {order_id} does not exist")
        if order_row["status"] != "pending":
            raise ApiError(409, "Items can only be added to pending orders")

        cur.execute("SELECT id, stock FROM products WHERE id = %s FOR UPDATE", (product_id,))
        prod = cur.fetchone()
        if prod is None:
            raise ApiError(404, f"Product {product_id} does not exist")
        if prod["stock"] < quantity:
            raise ApiError(
                409,
                f"Insufficient stock for product {product_id} (available: {prod['stock']}, requested: {quantity})",
            )

        cur.execute(
            "SELECT id, quantity FROM order_items WHERE order_id = %s AND product_id = %s FOR UPDATE",
            (order_id, product_id),
        )
        existing_item = cur.fetchone()
        if existing_item:
            cur.execute(
                "UPDATE order_items SET quantity = quantity + %s WHERE id = %s RETURNING id",
                (quantity, existing_item["id"]),
            )
            item_id = existing_item["id"]
        else:
            cur.execute(
                """
                INSERT INTO order_items (order_id, product_id, quantity)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (order_id, product_id, quantity),
            )
            item_id = cur.fetchone()["id"]

        cur.execute(
            "UPDATE products SET stock = stock - %s WHERE id = %s",
            (quantity, product_id),
        )

        return _fetch_order_item_with_product(cur, item_id)


def remove_item_from_pending_order(order_id: int, item_id: int) -> None:
    """Removes an item from a pending order and restores its quantity to product stock."""
    with transaction() as cur:
        cur.execute("SELECT id, status FROM orders WHERE id = %s FOR UPDATE", (order_id,))
        order_row = cur.fetchone()
        if order_row is None:
            raise ApiError(404, f"Order {order_id} does not exist")
        if order_row["status"] != "pending":
            raise ApiError(409, "Items can only be removed from pending orders")

        cur.execute(
            "SELECT id, product_id, quantity FROM order_items WHERE id = %s AND order_id = %s FOR UPDATE",
            (item_id, order_id),
        )
        item_row = cur.fetchone()
        if item_row is None:
            raise ApiError(404, f"Order item {item_id} not found in order {order_id}")

        cur.execute("DELETE FROM order_items WHERE id = %s", (item_id,))
        cur.execute(
            "UPDATE products SET stock = stock + %s WHERE id = %s",
            (item_row["quantity"], item_row["product_id"]),
        )