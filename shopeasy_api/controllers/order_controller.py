from typing import Tuple
from shopeasy_api.http_utils import Request
from shopeasy_api.services import order_service


def list_orders(request: Request) -> Tuple[int, object]:
    return 200, order_service.list_orders_service(request.query)


def get_order(request: Request) -> Tuple[int, dict]:
    return 200, order_service.get_order_service(request.params.get("id"))


def get_order_items(request: Request) -> Tuple[int, list]:
    return 200, order_service.get_order_items_service(request.params.get("id"))


def add_order_item(request: Request) -> Tuple[int, dict]:
    return 201, order_service.add_order_item_service(request.params.get("id"), request.body)


def delete_order_item(request: Request) -> Tuple[int, None]:
    order_service.delete_order_item_service(request.params.get("id"), request.params.get("item_id"))
    return 204, None


def create_order(request: Request) -> Tuple[int, dict]:
    return 201, order_service.create_order_service(request.body)


def update_order_status(request: Request) -> Tuple[int, dict]:
    return 200, order_service.update_order_status_service(request.params.get("id"), request.body)


def delete_order(request: Request) -> Tuple[int, None]:
    order_service.delete_order_service(request.params.get("id"))
    return 204, None
