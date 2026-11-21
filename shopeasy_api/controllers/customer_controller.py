from typing import Tuple
from shopeasy_api.db import ForeignKeyViolation, UniqueViolation
from shopeasy_api.errors import ApiError
from shopeasy_api.http_utils import Request
from shopeasy_api.models import customer as customer_model
from shopeasy_api.models import order as order_model
from shopeasy_api.validators import (
    parse_positive_int,
    require_non_empty_string,
    validate_email,
    validate_optional_city,
)
from shopeasy_api.views import customer_list_view, customer_view, order_list_view


def list_customers(request: Request) -> Tuple[int, list]:
    city = request.query.get("city")
    rows = customer_model.get_all(city=city)
    return 200, customer_list_view(rows)


def get_customer(request: Request) -> Tuple[int, dict]:
    customer_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    row = customer_model.get_by_id(customer_id)
    if row is None:
        raise ApiError(404, f"Customer {customer_id} not found")
    return 200, customer_view(row)


def get_customer_orders(request: Request) -> Tuple[int, list]:
    customer_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    if customer_model.get_by_id(customer_id) is None:
        raise ApiError(404, f"Customer {customer_id} not found")
    rows = order_model.get_all(customer_id=customer_id)
    return 200, order_list_view(rows)


def create_customer(request: Request) -> Tuple[int, dict]:
    body = request.body
    if body is None:
        raise ApiError(400, "Request body is required")

    name = require_non_empty_string(body.get("name"), "name", max_len=150)
    email = validate_email(body.get("email"))
    city = validate_optional_city(body.get("city"))

    try:
        created = customer_model.create(name=name, email=email, city=city)
    except UniqueViolation as exc:
        raise ApiError(409, "A customer with this email already exists") from exc

    return 201, customer_view(created)


def update_customer(request: Request) -> Tuple[int, dict]:
    customer_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    body = request.body
    if body is None or not body:
        raise ApiError(400, "Request body is required")

    existing = customer_model.get_by_id(customer_id)
    if existing is None:
        raise ApiError(404, f"Customer {customer_id} not found")

    updates = {}
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

    return 200, customer_view(updated)


def delete_customer(request: Request) -> Tuple[int, None]:
    customer_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    try:
        deleted = customer_model.delete(customer_id)
    except ForeignKeyViolation as exc:
        raise ApiError(409, "Cannot delete customer because they have existing orders") from exc

    if not deleted:
        raise ApiError(404, f"Customer {customer_id} not found")
    return 204, None