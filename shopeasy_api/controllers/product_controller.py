from typing import Tuple
from shopeasy_api.http_utils import Request
from shopeasy_api.services import product_service


def list_products(request: Request) -> Tuple[int, object]:
    return 200, product_service.list_products_service(request.query)


def get_product(request: Request) -> Tuple[int, dict]:
    return 200, product_service.get_product_service(request.params.get("id"))


def create_product(request: Request) -> Tuple[int, dict]:
    return 201, product_service.create_product_service(request.body)


def update_product(request: Request) -> Tuple[int, dict]:
    return 200, product_service.update_product_service(request.params.get("id"), request.body)


def delete_product(request: Request) -> Tuple[int, None]:
    product_service.delete_product_service(request.params.get("id"))
    return 204, None
