from typing import Tuple
from shopeasy_api.http_utils import Request
from shopeasy_api.models import report as report_model
from shopeasy_api.validators import parse_positive_int
from shopeasy_api.views import sales_by_product_view, top_customers_view

def list_reports(request: Request) -> Tuple[int, list]:
    rows = report_model.get_all_reports()
    return 200, [
        {
            "id": r["id"],
            "name": r["name"],
            "endpoint": r["endpoint"],
            "description": r.get("description"),
        }
        for r in rows
    ]

def get_sales_by_product(request: Request) -> Tuple[int, list]:
    rows = report_model.sales_by_product()
    return 200, sales_by_product_view(rows)


def get_top_customers(request: Request) -> Tuple[int, list]:
    limit = 3
    if "limit" in request.query:
        limit = parse_positive_int(request.query["limit"], "limit", status_code=400)
    rows = report_model.top_customers(limit=limit)
    return 200, top_customers_view(rows)