from typing import Tuple
from shopeasy_api.db import ForeignKeyViolation
from shopeasy_api.errors import ApiError
from shopeasy_api.http_utils import Request
from shopeasy_api.models import product as product_model
from shopeasy_api.validators import (
    VALID_PRODUCT_SORTS,
    parse_non_negative_decimal,
    parse_non_negative_int,
    parse_positive_int,
    require_non_empty_string,
)
from shopeasy_api.views import product_list_view, product_view


def list_products(request: Request) -> Tuple[int, object]:
    max_price = None
    min_price = None
    in_stock = None
    sort = None
    page = None
    limit = None

    if "max_price" in request.query:
        max_price = parse_non_negative_decimal(request.query["max_price"], "max_price", status_code=400)
    if "min_price" in request.query:
        min_price = parse_non_negative_decimal(request.query["min_price"], "min_price", status_code=400)
    if "in_stock" in request.query:
        raw = request.query["in_stock"].strip().lower()
        if raw == "true":
            in_stock = True
        elif raw == "false":
            in_stock = False
        else:
            raise ApiError(400, "in_stock must be 'true' or 'false'")
    if "sort" in request.query:
        sort = request.query["sort"].strip()
        if sort not in VALID_PRODUCT_SORTS:
            raise ApiError(400, "sort must be one of: price, -price, name, -name")
    if "page" in request.query:
        page = parse_positive_int(request.query["page"], "page", status_code=400)
    if "limit" in request.query:
        limit = parse_positive_int(request.query["limit"], "limit", status_code=400)

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
        return 200, {
            "items": items,
            "total": total,
            "page": page or 1,
            "limit": limit or 10,
        }
    return 200, items

def get_product(request: Request) -> Tuple[int, dict]:
    product_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    row = product_model.get_by_id(product_id)
    if row is None:
        raise ApiError(404, f"Product {product_id} not found")
    return 200, product_view(row)


def create_product(request: Request) -> Tuple[int, dict]:
    body = request.body
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
    return 201, product_view(created)


def update_product(request: Request) -> Tuple[int, dict]:
    product_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    body = request.body
    if body is None or not body:
        raise ApiError(400, "Request body is required")

    existing = product_model.get_by_id(product_id)
    if existing is None:
        raise ApiError(404, f"Product {product_id} not found")

    updates = {}
    if "name" in body:
        updates["name"] = require_non_empty_string(body.get("name"), "name", max_len=150)
    if "price" in body:
        updates["price"] = parse_non_negative_decimal(body.get("price"), "price", status_code=422)
    if "stock" in body:
        updates["stock"] = parse_non_negative_int(body.get("stock"), "stock", status_code=422)

    updated = product_model.update(product_id, updates)
    return 200, product_view(updated)


def delete_product(request: Request) -> Tuple[int, None]:
    product_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    try:
        deleted = product_model.delete(product_id)
    except ForeignKeyViolation as exc:
        raise ApiError(409, "Cannot delete product because it appears in existing orders") from exc

    if not deleted:
        raise ApiError(404, f"Product {product_id} not found")
    return 204, None