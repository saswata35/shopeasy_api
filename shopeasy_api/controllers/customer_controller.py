from typing import Tuple
from shopeasy_api.http_utils import Request
from shopeasy_api.services import customer_service


def list_customers(request: Request) -> Tuple[int, object]:
    return 200, customer_service.list_customers_service(request.query)


def get_customer(request: Request) -> Tuple[int, dict]:
    return 200, customer_service.get_customer_service(request.params.get("id"))


def get_customer_orders(request: Request) -> Tuple[int, list]:
    return 200, customer_service.get_customer_orders_service(request.params.get("id"))


def create_customer(request: Request) -> Tuple[int, dict]:
    return 201, customer_service.create_customer_service(request.body)


def update_customer(request: Request) -> Tuple[int, dict]:
    return 200, customer_service.update_customer_service(request.params.get("id"), request.body)


def delete_customer(request: Request) -> Tuple[int, None]:
    customer_service.delete_customer_service(request.params.get("id"))
    return 204, None
