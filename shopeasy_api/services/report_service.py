from typing import Any, Dict, List
from shopeasy_api.models import report as report_model
from shopeasy_api.validators import parse_positive_int
from shopeasy_api.views import sales_by_product_view, top_customers_view


def list_reports_service() -> List[Dict[str, Any]]:
    rows = report_model.get_all_reports()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "endpoint": r["endpoint"],
            "description": r.get("description"),
        }
        for r in rows
    ]


def get_sales_by_product_service() -> List[Dict[str, Any]]:
    rows = report_model.sales_by_product()
    return sales_by_product_view(rows)


def get_top_customers_service(query: Dict[str, str]) -> List[Dict[str, Any]]:
    limit = 3
    if "limit" in query:
        limit = parse_positive_int(query["limit"], "limit", status_code=400)
    rows = report_model.top_customers(limit=limit)
    return top_customers_view(rows)
