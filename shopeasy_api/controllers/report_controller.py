from typing import Tuple
from shopeasy_api.http_utils import Request
from shopeasy_api.services import report_service


def list_reports(request: Request) -> Tuple[int, list]:
    return 200, report_service.list_reports_service()


def get_sales_by_product(request: Request) -> Tuple[int, list]:
    return 200, report_service.get_sales_by_product_service()


def get_top_customers(request: Request) -> Tuple[int, list]:
    return 200, report_service.get_top_customers_service(request.query)
