import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlparse
from shopeasy_api.config import Config
from shopeasy_api.controllers import (
    customer_controller,
    health_controller,
    order_controller,
    product_controller,
    report_controller,
)
from shopeasy_api.errors import ApiError
from shopeasy_api.http_utils import Request, parse_json_body, send_json
from shopeasy_api.router import Router


def build_router() -> Router:
    router = Router()

    router.add_route("/health", {
        "GET": health_controller.health_check,
    })

    router.add_route("/products", {
        "GET": product_controller.list_products,
        "POST": product_controller.create_product,
    })
    router.add_route("/products/{id}", {
        "GET": product_controller.get_product,
        "PATCH": product_controller.update_product,
        "DELETE": product_controller.delete_product,
    })

    router.add_route("/customers", {
        "GET": customer_controller.list_customers,
        "POST": customer_controller.create_customer,
    })
    router.add_route("/customers/{id}", {
        "GET": customer_controller.get_customer,
        "PATCH": customer_controller.update_customer,
        "DELETE": customer_controller.delete_customer,
    })
    router.add_route("/customers/{id}/orders", {
        "GET": customer_controller.get_customer_orders,
    })

    router.add_route("/orders", {
        "GET": order_controller.list_orders,
        "POST": order_controller.create_order,
    })
    router.add_route("/orders/{id}", {
        "GET": order_controller.get_order,
        "PATCH": order_controller.update_order_status,
        "DELETE": order_controller.delete_order,
    })
    router.add_route("/orders/{id}/items", {
        "GET": order_controller.get_order_items,
        "POST": order_controller.add_order_item,
    })
    router.add_route("/orders/{id}/items/{item_id}", {
        "DELETE": order_controller.delete_order_item,
    })

    router.add_route("/reports", {
        "GET": report_controller.list_reports,
    })

    router.add_route("/reports/sales-by-product", {
        "GET": report_controller.get_sales_by_product,
    })
    router.add_route("/reports/top-customers", {
        "GET": report_controller.get_top_customers,
    })

    return router


ROUTER = build_router()


class ShopEasyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args) -> None:
        # Suppress default stderr chatter; we log clean request lines in _handle().
        return

    def _handle(self, method: str) -> None:
        start_time = time.perf_counter()
        parsed = urlparse(self.path)
        path = parsed.path or "/"
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""

        status_code = 500
        try:
            body = parse_json_body(raw_body)
            handler_fn, params = ROUTER.resolve(method, path)
            req = Request(
                method=method,
                path=path,
                query=query,
                params=params,
                body=body,
            )
            status_code, payload = handler_fn(req)
            send_json(self, status_code, payload)
        except ApiError as err:
            status_code = err.status_code
            send_json(self, status_code, {"error": err.message})
        except Exception as exc:
            status_code = 500
            print(f"[ERROR] Unhandled exception on {method} {self.path}: {exc}")
            send_json(self, 500, {"error": "Internal server error"})
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            print(f"{method} {self.path} -> {status_code} (took {elapsed_ms:.1f} ms)")

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PATCH(self) -> None:
        self._handle("PATCH")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    def do_PUT(self) -> None:
        self._handle("PUT")


def run_server() -> None:
    server = ThreadingHTTPServer((Config.API_HOST, Config.API_PORT), ShopEasyHandler)
    print(f"ShopEasy API listening on http://{Config.API_HOST}:{Config.API_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down ShopEasy API...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()