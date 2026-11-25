import math
from typing import Any, Dict, List, Optional
from shopeasy_api.errors import ApiError
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


def list_orders_service(query: Dict[str, str]) -> Any:
    status = None
    customer_id = None
    page = None
    limit = None

    if "status" in query:
        status = validate_order_status(query["status"])

    if "customer_id" in query:
        customer_id = parse_positive_int(query["customer_id"], "customer_id", status_code=400)

    if "page" in query:
        page = parse_positive_int(query["page"], "page", status_code=400)
    if "limit" in query:
        limit = parse_positive_int(query["limit"], "limit", status_code=400)
        if limit > 100:
            raise ApiError(400, "limit cannot exceed 100")

    rows, total = order_model.get_all(
        status=status,
        customer_id=customer_id,
        page=page,
        limit=limit,
    )
    items = order_list_view(rows)

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


def get_order_service(raw_id: Any) -> Dict[str, Any]:
    order_id = parse_positive_int(raw_id, "id", status_code=400)
    header = order_model.get_by_id(order_id)
    if header is None:
        raise ApiError(404, f"Order {order_id} not found")

    items = order_model.get_items(order_id) or []
    return order_detail_view(header, items)


def get_order_items_service(raw_id: Any) -> List[Dict[str, Any]]:
    order_id = parse_positive_int(raw_id, "id", status_code=400)
    items = order_model.get_items(order_id)
    if items is None:
        raise ApiError(404, f"Order {order_id} not found")
    return [order_item_view(item) for item in items]


def add_order_item_service(raw_order_id: Any, body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    order_id = parse_positive_int(raw_order_id, "id", status_code=400)
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
    return order_item_view(item)


def delete_order_item_service(raw_order_id: Any, raw_item_id: Any) -> None:
    order_id = parse_positive_int(raw_order_id, "id", status_code=400)
    item_id = parse_positive_int(raw_item_id, "item_id", status_code=400)
    order_model.remove_item_from_pending_order(order_id=order_id, item_id=item_id)


def create_order_service(body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
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
    return order_detail_view(header, items)


def update_order_status_service(raw_id: Any, body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    order_id = parse_positive_int(raw_id, "id", status_code=400)
    if body is None or "status" not in body:
        raise ApiError(400, "status is required")

    new_status = validate_order_status(body.get("status"))
    result = order_model.update_status(order_id, new_status)
    return order_detail_view(result["order"], result["items"])


def delete_order_service(raw_id: Any) -> None:
    order_id = parse_positive_int(raw_id, "id", status_code=400)
    order_model.delete_cancelled_order(order_id)
