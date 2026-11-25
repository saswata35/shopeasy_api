import math
from typing import Any, Dict, Optional
from shopeasy_api.db import ForeignKeyViolation
from shopeasy_api.errors import ApiError
from shopeasy_api.models import product as product_model
from shopeasy_api.validators import (
    VALID_PRODUCT_SORTS,
    parse_non_negative_decimal,
    parse_non_negative_int,
    parse_positive_int,
    require_non_empty_string,
)
from shopeasy_api.views import product_list_view, product_view


def list_products_service(query: Dict[str, str]) -> Any:
    max_price = None
    min_price = None
    in_stock = None
    sort = None
    page = None
    limit = None

    if "max_price" in query:
        max_price = parse_non_negative_decimal(query["max_price"], "max_price", status_code=400)
    if "min_price" in query:
        min_price = parse_non_negative_decimal(query["min_price"], "min_price", status_code=400)
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ApiError(400, "min_price cannot be greater than max_price")

    if "in_stock" in query:
        raw = query["in_stock"].strip().lower()
        if raw == "true":
            in_stock = True
        elif raw == "false":
            in_stock = False
        else:
            raise ApiError(400, "in_stock must be 'true' or 'false'")

    if "sort" in query:
        sort = query["sort"].strip()
        if sort not in VALID_PRODUCT_SORTS:
            raise ApiError(400, "sort must be one of: price, -price, name, -name")

    if "page" in query:
        page = parse_positive_int(query["page"], "page", status_code=400)
    if "limit" in query:
        limit = parse_positive_int(query["limit"], "limit", status_code=400)
        if limit > 100:
            raise ApiError(400, "limit cannot exceed 100")

    rows, total = product_model.get_all(
        max_price=max_price,
        min_price=min_price,
        in_stock=in_stock,
        sort=sort,
        page=page,
        limit=limit,
    )
    items = product_list_view(rows)

    if page is not None or limit is not None:
        effective_page = page or 1
        effective_limit = limit or 10
        total_pages = math.ceil(total / effective_limit) if total > 0 else 0
        return {
            "items": items,
            "total": total,
            "page": effective_page,
            "limit": effective_limit,
            "total_pages": total_pages,
            "has_next": effective_page < total_pages,
            "has_prev": effective_page > 1 and total_pages > 0,
        }

    return items


def get_product_service(raw_id: Any) -> Dict[str, Any]:
    product_id = parse_positive_int(raw_id, "id", status_code=400)
    row = product_model.get_by_id(product_id)
    if row is None:
        raise ApiError(404, f"Product {product_id} not found")
    return product_view(row)


def create_product_service(body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if body is None:
        raise ApiError(400, "Request body is required")

    name = require_non_empty_string(body.get("name"), "name", max_len=150)

    if "price" not in body:
        raise ApiError(400, "price is required")
    price = parse_non_negative_decimal(body.get("price"), "price", status_code=422)

    stock = 0
    if "stock" in body and body.get("stock") is not None:
        stock = parse_non_negative_int(body.get("stock"), "stock", status_code=422)

    created = product_model.create(name=name, price=price, stock=stock)
    return product_view(created)


def update_product_service(raw_id: Any, body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    product_id = parse_positive_int(raw_id, "id", status_code=400)
    if body is None or not body:
        raise ApiError(400, "Request body is required")

    existing = product_model.get_by_id(product_id)
    if existing is None:
        raise ApiError(404, f"Product {product_id} not found")

    updates: Dict[str, Any] = {}
    if "name" in body:
        updates["name"] = require_non_empty_string(body.get("name"), "name", max_len=150)
    if "price" in body:
        updates["price"] = parse_non_negative_decimal(body.get("price"), "price", status_code=422)
    if "stock" in body:
        updates["stock"] = parse_non_negative_int(body.get("stock"), "stock", status_code=422)

    updated = product_model.update(product_id, updates)
    return product_view(updated)


def delete_product_service(raw_id: Any) -> None:
    product_id = parse_positive_int(raw_id, "id", status_code=400)
    try:
        deleted = product_model.delete(product_id)
    except ForeignKeyViolation as exc:
        raise ApiError(409, "Cannot delete product because it appears in existing orders") from exc

    if not deleted:
        raise ApiError(404, f"Product {product_id} not found")
