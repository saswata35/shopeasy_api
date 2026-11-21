from typing import Any, Dict, List, Optional
from shopeasy_api.db import get_cursor

def get_all(city: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = "SELECT id, name, email, city, created_at FROM customers WHERE 1=1"
    params: List[Any] = []

    if city is not None and city.strip() != "":
        sql += " AND LOWER(city) = LOWER(%s)"
        params.append(city.strip())

    sql += " ORDER BY id ASC"

    with get_cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


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