import math
from typing import Any, Dict, Optional
from shopeasy_api.db import ForeignKeyViolation, UniqueViolation
from shopeasy_api.errors import ApiError
from shopeasy_api.models import customer as customer_model
from shopeasy_api.models import order as order_model
from shopeasy_api.validators import (
    parse_positive_int,
    require_non_empty_string,
    validate_email,
    validate_optional_city,
)
from shopeasy_api.views import customer_list_view, customer_view, order_list_view


def list_customers_service(query: Dict[str, str]) -> Any:
    city = query.get("city")
    page = None
    limit = None

    if "page" in query:
        page = parse_positive_int(query["page"], "page", status_code=400)
    if "limit" in query:
        limit = parse_positive_int(query["limit"], "limit", status_code=400)
        if limit > 100:
            raise ApiError(400, "limit cannot exceed 100")

    rows, total = customer_model.get_all(city=city, page=page, limit=limit)
    items = customer_list_view(rows)

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


def get_customer_service(raw_id: Any) -> Dict[str, Any]:
    customer_id = parse_positive_int(raw_id, "id", status_code=400)
    row = customer_model.get_by_id(customer_id)
    if row is None:
        raise ApiError(404, f"Customer {customer_id} not found")
    return customer_view(row)


def get_customer_orders_service(raw_id: Any) -> list:
    customer_id = parse_positive_int(raw_id, "id", status_code=400)
    if customer_model.get_by_id(customer_id) is None:
        raise ApiError(404, f"Customer {customer_id} not found")
    rows, _ = order_model.get_all(customer_id=customer_id)
    return order_list_view(rows)


def create_customer_service(body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if body is None:
        raise ApiError(400, "Request body is required")

    name = require_non_empty_string(body.get("name"), "name", max_len=150)
    email = validate_email(body.get("email"))
    city = validate_optional_city(body.get("city"))

    try:
        created = customer_model.create(name=name, email=email, city=city)
    except UniqueViolation as exc:
        raise ApiError(409, "A customer with this email already exists") from exc

    return customer_view(created)


def update_customer_service(raw_id: Any, body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    customer_id = parse_positive_int(raw_id, "id", status_code=400)
    if body is None or not body:
        raise ApiError(400, "Request body is required")

    existing = customer_model.get_by_id(customer_id)
    if existing is None:
        raise ApiError(404, f"Customer {customer_id} not found")

    updates: Dict[str, Any] = {}
    if "name" in body:
        updates["name"] = require_non_empty_string(body.get("name"), "name", max_len=150)
    if "email" in body:
        updates["email"] = validate_email(body.get("email"))
    if "city" in body:
        updates["city"] = validate_optional_city(body.get("city"))

    try:
        updated = customer_model.update(customer_id, updates)
    except UniqueViolation as exc:
        raise ApiError(409, "A customer with this email already exists") from exc

    return customer_view(updated)


def delete_customer_service(raw_id: Any) -> None:
    customer_id = parse_positive_int(raw_id, "id", status_code=400)
    try:
        deleted = customer_model.delete(customer_id)
    except ForeignKeyViolation as exc:
        raise ApiError(409, "Cannot delete customer because they have existing orders") from exc

    if not deleted:
        raise ApiError(404, f"Customer {customer_id} not found")
