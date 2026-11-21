from typing import Dict, List, Tuple
from shopeasy_api.errors import ApiError
from shopeasy_api.http_utils import Request
from shopeasy_api.models import order as order_model
from shopeasy_api.validators import (
    parse_positive_int,
    validate_order_status,
)
from shopeasy_api.views import (
    order_detail_view,
    order_item_view,
    order_list_view,
)


def list_orders(request: Request) -> Tuple[int, list]:
    status = None
    customer_id = None

    if "status" in request.query:
        status = validate_order_status(request.query["status"])

    if "customer_id" in request.query:
        customer_id = parse_positive_int(
            request.query["customer_id"], "customer_id", status_code=400
        )

    rows = order_model.get_all(status=status, customer_id=customer_id)
    return 200, order_list_view(rows)


def get_order(request: Request) -> Tuple[int, dict]:
    order_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    header = order_model.get_by_id(order_id)
    if header is None:
        raise ApiError(404, f"Order {order_id} not found")

    items = order_model.get_items(order_id) or []
    return 200, order_detail_view(header, items)


def get_order_items(request: Request) -> Tuple[int, list]:
    order_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    items = order_model.get_items(order_id)
    if items is None:
        raise ApiError(404, f"Order {order_id} not found")
    return 200, [order_item_view(item) for item in items]


def add_order_item(request: Request) -> Tuple[int, dict]:
    order_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    body = request.body
    if body is None or not isinstance(body, dict):
        raise ApiError(400, "Request body is required")

    if "product_id" not in body or "quantity" not in body:
        raise ApiError(400, "Both product_id and quantity are required")

    product_id = parse_positive_int(body.get("product_id"), "product_id", status_code=422)
    quantity = parse_positive_int(body.get("quantity"), "quantity", status_code=422)

    item = order_model.add_item_to_pending_order(
        order_id=order_id,
        product_id=product_id,
        quantity=quantity,
    )
    return 201, order_item_view(item)


def delete_order_item(request: Request) -> Tuple[int, None]:
    order_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    item_id = parse_positive_int(request.params.get("item_id"), "item_id", status_code=400)
    order_model.remove_item_from_pending_order(order_id=order_id, item_id=item_id)
    return 204, None


def create_order(request: Request) -> Tuple[int, dict]:
    body = request.body
    if body is None:
        raise ApiError(400, "Request body is required")

    if "customer_id" not in body or "items" not in body:
        raise ApiError(400, "Both customer_id and items are required")

    customer_id = parse_positive_int(body.get("customer_id"), "customer_id", status_code=400)

    raw_items = body.get("items")
    if not isinstance(raw_items, list) or len(raw_items) == 0:
        raise ApiError(422, "items must be a non-empty list")

    parsed_items: List[Dict[str, int]] = []
    seen_products = set()

    for entry in raw_items:
        if not isinstance(entry, dict):
            raise ApiError(422, "Each item must be an object with product_id and quantity")
        if "product_id" not in entry or "quantity" not in entry:
            raise ApiError(422, "Each item requires product_id and quantity")

        pid = parse_positive_int(entry.get("product_id"), "product_id", status_code=422)
        qty = parse_positive_int(entry.get("quantity"), "quantity", status_code=422)

        if pid in seen_products:
            raise ApiError(422, f"Duplicate product_id {pid} in order items")
        seen_products.add(pid)
        parsed_items.append({"product_id": pid, "quantity": qty})

    order_id = order_model.create_order(customer_id=customer_id, items=parsed_items)
    header = order_model.get_by_id(order_id)
    items = order_model.get_items(order_id) or []
    return 201, order_detail_view(header, items)


def update_order_status(request: Request) -> Tuple[int, dict]:
    order_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    body = request.body
    if body is None or "status" not in body:
        raise ApiError(400, "status is required")

    new_status = validate_order_status(body.get("status"))
    result = order_model.update_status(order_id, new_status)
    return 200, order_detail_view(result["order"], result["items"])


def delete_order(request: Request) -> Tuple[int, None]:
    order_id = parse_positive_int(request.params.get("id"), "id", status_code=400)
    order_model.delete_cancelled_order(order_id)
    return 204, None