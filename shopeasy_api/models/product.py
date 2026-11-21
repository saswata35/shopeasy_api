from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from shopeasy_api.db import get_cursor

SORT_MAP = {
    "price": "price ASC, id ASC",
    "-price": "price DESC, id ASC",
    "name": "name ASC, id ASC",
    "-name": "name DESC, id ASC",
}


def get_all(
    max_price: Optional[Decimal] = None,
    min_price: Optional[Decimal] = None,
    in_stock: Optional[bool] = None,
    sort: Optional[str] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    where_sql = " FROM products WHERE 1=1"
    params: List[Any] = []

    if max_price is not None:
        where_sql += " AND price <= %s"
        params.append(max_price)
    if min_price is not None:
        where_sql += " AND price >= %s"
        params.append(min_price)
    if in_stock:
        where_sql += " AND stock > 0"

    order_clause = SORT_MAP.get(sort or "", "id ASC")

    with get_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total{where_sql}", params)
        total = int(cur.fetchone()["total"])

        select_sql = f"SELECT id, name, price, stock{where_sql} ORDER BY {order_clause}"
        query_params = list(params)

        if page is not None or limit is not None:
            effective_limit = limit if limit is not None else 10
            effective_page = page if page is not None else 1
            offset = (effective_page - 1) * effective_limit
            select_sql += " LIMIT %s OFFSET %s"
            query_params.extend([effective_limit, offset])

        cur.execute(select_sql, query_params)
        return list(cur.fetchall()), total


def get_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, name, price, stock FROM products WHERE id = %s",
            (product_id,),
        )
        return cur.fetchone()


def create(name: str, price: Decimal, stock: int = 0) -> Dict[str, Any]:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO products (name, price, stock)
            VALUES (%s, %s, %s)
            RETURNING id, name, price, stock
            """,
            (name, price, stock),
        )
        return cur.fetchone()


def update(product_id: int, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    allowed = {"name", "price", "stock"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_by_id(product_id)

    set_clauses = [f"{col} = %s" for col in updates]
    params: List[Any] = list(updates.values()) + [product_id]

    sql = f"""
        UPDATE products
        SET {", ".join(set_clauses)}
        WHERE id = %s
        RETURNING id, name, price, stock
    """
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def delete(product_id: int) -> bool:
    with get_cursor() as cur:
        cur.execute("DELETE FROM products WHERE id = %s RETURNING id", (product_id,))
        return cur.fetchone() is not None