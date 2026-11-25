from typing import Any, Dict, List, Optional, Tuple
from shopeasy_api.db import get_cursor


def get_all(
    city: Optional[str] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    where_sql = " FROM customers WHERE 1=1"
    params: List[Any] = []

    if city is not None and city.strip() != "":
        where_sql += " AND LOWER(city) = LOWER(%s)"
        params.append(city.strip())

    with get_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total{where_sql}", params)
        total = int(cur.fetchone()["total"])

        select_sql = f"SELECT id, name, email, city, created_at{where_sql} ORDER BY id ASC"
        query_params = list(params)

        if page is not None or limit is not None:
            effective_limit = limit if limit is not None else 10
            effective_page = page if page is not None else 1
            offset = (effective_page - 1) * effective_limit
            select_sql += " LIMIT %s OFFSET %s"
            query_params.extend([effective_limit, offset])

        cur.execute(select_sql, query_params)
        return list(cur.fetchall()), total


def get_by_id(customer_id: int) -> Optional[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, name, email, city, created_at FROM customers WHERE id = %s",
            (customer_id,),
        )
        return cur.fetchone()


def create(name: str, email: str, city: Optional[str] = None) -> Dict[str, Any]:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO customers (name, email, city)
            VALUES (%s, %s, %s)
            RETURNING id, name, email, city, created_at
            """,
            (name, email, city),
        )
        return cur.fetchone()


def update(customer_id: int, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    allowed = {"name", "email", "city"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_by_id(customer_id)

    set_clauses = [f"{col} = %s" for col in updates]
    params: List[Any] = list(updates.values()) + [customer_id]

    sql = f"""
        UPDATE customers
        SET {", ".join(set_clauses)}
        WHERE id = %s
        RETURNING id, name, email, city, created_at
    """
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def delete(customer_id: int) -> bool:
    with get_cursor() as cur:
        cur.execute("DELETE FROM customers WHERE id = %s RETURNING id", (customer_id,))
        return cur.fetchone() is not None
