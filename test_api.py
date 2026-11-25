import argparse
import json
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class _Response:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text

    def json(self) -> object:
        try:
            return json.loads(self.text)
        except (json.JSONDecodeError, TypeError):
            return {}


class _Requests:
    @staticmethod
    def _request(method: str, url: str, *, timeout: int = 5, json=None, data=None, headers=None) -> _Response:
        request_headers = dict(headers or {})
        body = None
        if json is not None:
            body = json_module.dumps(json).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        elif data is not None:
            body = data.encode("utf-8") if isinstance(data, str) else data

        request = Request(url, data=body, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8")
                return _Response(response.status, text)
        except HTTPError as error:
            text = error.read().decode("utf-8")
            return _Response(error.code, text)
        except URLError as error:
            return _Response(0, str(error.reason))

    def get(self, url: str, **kwargs) -> _Response:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> _Response:
        return self._request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs) -> _Response:
        return self._request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs) -> _Response:
        return self._request("DELETE", url, **kwargs)


json_module = json
requests = _Requests()


class TestRunner:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.passed = 0
        self.failed = 0

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.passed += 1
            print(f"[PASS] {name}")
        else:
            self.failed += 1
            msg = f"[FAIL] {name}"
            if detail:
                msg += f" -- {detail}"
            print(msg)

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"


def test_health(r: TestRunner) -> None:
    resp = requests.get(r.url("/health"), timeout=5)
    r.check("Health returns 200", resp.status_code == 200, f"got {resp.status_code}")
    data = resp.json() if resp.status_code == 200 else {}
    r.check("Health status is ok", data.get("status") == "ok", f"got {data}")


def test_products(r: TestRunner) -> None:
    resp = requests.get(r.url("/products"), timeout=5)
    r.check("GET /products returns 200", resp.status_code == 200, f"got {resp.status_code}")
    products = resp.json() if resp.status_code == 200 else []
    r.check("GET /products returns list", isinstance(products, list))

    resp_q = requests.get(r.url("/products?max_price=100&sort=-price"), timeout=5)
    r.check("GET /products with query params returns 200", resp_q.status_code == 200)

    resp_bad_q = requests.get(r.url("/products?max_price=abc"), timeout=5)
    r.check("GET /products bad max_price returns 400", resp_bad_q.status_code == 400)

    resp_404 = requests.get(r.url("/products/999999"), timeout=5)
    r.check("GET unknown product returns 404", resp_404.status_code == 404)

    resp_bad_id = requests.get(r.url("/products/abc"), timeout=5)
    r.check("GET /products/abc returns 400", resp_bad_id.status_code == 400)

    create_resp = requests.post(
        r.url("/products"),
        json={"name": "Test Stapler", "price": 45.0, "stock": 20},
        timeout=5,
    )
    r.check("POST /products returns 201", create_resp.status_code == 201, create_resp.text)
    created = create_resp.json() if create_resp.status_code == 201 else {}
    pid = created.get("id")
    r.check("Created product price formatted as string", created.get("price") == "45.00")

    if pid:
        one_resp = requests.get(r.url(f"/products/{pid}"), timeout=5)
        r.check("GET created product returns 200", one_resp.status_code == 200)

        patch_resp = requests.patch(
            r.url(f"/products/{pid}"),
            json={"price": 49.5, "stock": 15},
            timeout=5,
        )
        r.check("PATCH product returns 200", patch_resp.status_code == 200)
        patched = patch_resp.json() if patch_resp.status_code == 200 else {}
        r.check("PATCH updated price & stock", patched.get("price") == "49.50" and patched.get("stock") == 15)

        del_resp = requests.delete(r.url(f"/products/{pid}"), timeout=5)
        r.check("DELETE product returns 204", del_resp.status_code == 204)

        after_del = requests.get(r.url(f"/products/{pid}"), timeout=5)
        r.check("GET deleted product returns 404", after_del.status_code == 404)

    neg_resp = requests.post(
        r.url("/products"),
        json={"name": "Bad Price", "price": -5},
        timeout=5,
    )
    r.check("POST product with negative price returns 422", neg_resp.status_code == 422)


def test_customers(r: TestRunner) -> None:
    resp = requests.get(r.url("/customers"), timeout=5)
    r.check("1. GET /customers returns 200", resp.status_code == 200)

    resp_city = requests.get(r.url("/customers?city=Delhi"), timeout=5)
    r.check("2. GET /customers?city= returns 200", resp_city.status_code == 200)

    r.check("3. GET /customers/1 returns 200", requests.get(r.url("/customers/1"), timeout=5).status_code == 200)
    r.check("4. GET unknown customer returns 404", requests.get(r.url("/customers/999999"), timeout=5).status_code == 404)

    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    c_resp = requests.post(
        r.url("/customers"),
        json={"name": "Test Customer", "email": unique_email, "city": "Mumbai"},
        timeout=5,
    )
    r.check("5. POST /customers returns 201", c_resp.status_code == 201, c_resp.text)
    created = c_resp.json() if c_resp.status_code == 201 else {}
    cid = created.get("id")

    dup_resp = requests.post(
        r.url("/customers"),
        json={"name": "Dup Customer", "email": unique_email, "city": "Mumbai"},
        timeout=5,
    )
    r.check("6. Duplicate email returns 409", dup_resp.status_code == 409)

    missing_email = requests.post(
        r.url("/customers"),
        json={"name": "No Email"},
        timeout=5,
    )
    r.check("7. Missing email returns 400", missing_email.status_code == 400)

    bad_email = requests.post(
        r.url("/customers"),
        json={"name": "Bad Email", "email": "not-an-email"},
        timeout=5,
    )
    r.check("8. Bad email returns 422", bad_email.status_code == 422)

    if cid:
        patch_resp = requests.patch(
            r.url(f"/customers/{cid}"),
            json={"city": "Pune"},
            timeout=5,
        )
        r.check("9. PATCH customer city returns 200", patch_resp.status_code == 200)

        del_resp = requests.delete(r.url(f"/customers/{cid}"), timeout=5)
        r.check("10. DELETE customer returns 204", del_resp.status_code == 204)
        r.check("10b. GET deleted customer returns 404", requests.get(r.url(f"/customers/{cid}"), timeout=5).status_code == 404)

    del_with_orders = requests.delete(r.url("/customers/1"), timeout=5)
    r.check("11. DELETE customer with orders returns 409", del_with_orders.status_code == 409)


def test_orders_and_items(r: TestRunner) -> None:
    r.check("1. GET /orders returns 200", requests.get(r.url("/orders"), timeout=5).status_code == 200)
    r.check("2. GET /orders?status=pending returns 200", requests.get(r.url("/orders?status=pending"), timeout=5).status_code == 200)
    r.check("3. GET /orders?customer_id=1 returns 200", requests.get(r.url("/orders?customer_id=1"), timeout=5).status_code == 200)
    r.check("4. GET /orders?customer_id=abc returns 400", requests.get(r.url("/orders?customer_id=abc"), timeout=5).status_code == 400)

    detail_resp = requests.get(r.url("/orders/1"), timeout=5)
    r.check("5. GET /orders/1 returns 200", detail_resp.status_code == 200)
    detail = detail_resp.json() if detail_resp.status_code == 200 else {}
    r.check(
        "5b. Order detail has customer, items, total",
        "customer" in detail and "items" in detail and "total" in detail,
    )

    r.check("6. GET unknown order returns 404", requests.get(r.url("/orders/999999"), timeout=5).status_code == 404)

    # Create a fresh product with stock=10 for lifecycle & rollback testing
    p_resp = requests.post(
        r.url("/products"),
        json={"name": "Order Lifecycle Item", "price": 25.00, "stock": 10},
        timeout=5,
    )
    r.check("Setup test product with stock=10", p_resp.status_code == 201)
    test_pid = p_resp.json()["id"]

    # Rollback test: item 1 valid (qty 2), item 2 exceeds stock (qty 999) -> 409 & stock stays 10
    rollback_resp = requests.post(
        r.url("/orders"),
        json={
            "customer_id": 1,
            "items": [
                {"product_id": test_pid, "quantity": 2},
                {"product_id": test_pid, "quantity": 999},
            ],
        },
        timeout=5,
    )
    r.check("Duplicate product_id in order returns 422", rollback_resp.status_code == 422)

    p2_resp = requests.post(
        r.url("/products"),
        json={"name": "Second Item", "price": 10.00, "stock": 1},
        timeout=5,
    )
    p2_id = p2_resp.json()["id"]

    insufficient_resp = requests.post(
        r.url("/orders"),
        json={
            "customer_id": 1,
            "items": [
                {"product_id": test_pid, "quantity": 4},
                {"product_id": p2_id, "quantity": 5},
            ],
        },
        timeout=5,
    )
    r.check("12. Insufficient stock returns 409", insufficient_resp.status_code == 409)
    stock_after_fail = requests.get(r.url(f"/products/{test_pid}"), timeout=5).json()["stock"]
    r.check("12b. Stock unchanged after failed order (rollback)", stock_after_fail == 10, f"got {stock_after_fail}")

    r.check("9. Unknown customer order returns 404", requests.post(r.url("/orders"), json={"customer_id": 999999, "items": [{"product_id": test_pid, "quantity": 1}]}, timeout=5).status_code == 404)
    r.check("10. Unknown product order returns 404", requests.post(r.url("/orders"), json={"customer_id": 1, "items": [{"product_id": 999999, "quantity": 1}]}, timeout=5).status_code == 404)
    r.check("11. Empty items order returns 422", requests.post(r.url("/orders"), json={"customer_id": 1, "items": []}, timeout=5).status_code == 422)

    # Create order for 3 units -> stock becomes 7
    order_resp = requests.post(
        r.url("/orders"),
        json={"customer_id": 1, "items": [{"product_id": test_pid, "quantity": 3}]},
        timeout=5,
    )
    r.check("7. Create order returns 201", order_resp.status_code == 201, order_resp.text)
    order_data = order_resp.json() if order_resp.status_code == 201 else {}
    oid = order_data.get("id")

    stock_after_order = requests.get(r.url(f"/products/{test_pid}"), timeout=5).json()["stock"]
    r.check("8. Stock decreased to 7 after order", stock_after_order == 7, f"got {stock_after_order}")

    if oid:
        items_resp = requests.get(r.url(f"/orders/{oid}/items"), timeout=5)
        r.check("Order items GET /orders/{id}/items returns 200", items_resp.status_code == 200)
        items_list = items_resp.json() if items_resp.status_code == 200 else []
        r.check("Order items count is 1", len(items_list) == 1)
        if items_list:
            r.check("Order item line_total is 75.00", items_list[0].get("line_total") == "75.00")

        r.check("14. PATCH invalid status returns 422", requests.patch(r.url(f"/orders/{oid}"), json={"status": "shipped"}, timeout=5).status_code == 422)
        r.check("17. DELETE pending order returns 409", requests.delete(r.url(f"/orders/{oid}"), timeout=5).status_code == 409)

        cancel_resp = requests.patch(r.url(f"/orders/{oid}"), json={"status": "cancelled"}, timeout=5)
        r.check("PATCH pending to cancelled returns 200", cancel_resp.status_code == 200)

        stock_restored = requests.get(r.url(f"/products/{test_pid}"), timeout=5).json()["stock"]
        r.check("16. Cancel restores stock back to 10", stock_restored == 10, f"got {stock_restored}")

        r.check("15. PATCH after cancel returns 409", requests.patch(r.url(f"/orders/{oid}"), json={"status": "delivered"}, timeout=5).status_code == 409)

        del_order_resp = requests.delete(r.url(f"/orders/{oid}"), timeout=5)
        r.check("18. DELETE cancelled order returns 204", del_order_resp.status_code == 204)

    # Also test delivered transition on a separate order
    deliv_order = requests.post(
        r.url("/orders"),
        json={"customer_id": 1, "items": [{"product_id": test_pid, "quantity": 1}]},
        timeout=5,
    )
    if deliv_order.status_code == 201:
        d_oid = deliv_order.json()["id"]
        d_patch = requests.patch(r.url(f"/orders/{d_oid}"), json={"status": "delivered"}, timeout=5)
        r.check("13. PATCH pending to delivered returns 200", d_patch.status_code == 200)
        r.check("DELETE delivered order returns 409", requests.delete(r.url(f"/orders/{d_oid}"), timeout=5).status_code == 409)

    # Cleanup temporary products
    requests.delete(r.url(f"/products/{p2_id}"), timeout=5)
    requests.delete(r.url(f"/products/{test_pid}"), timeout=5)


def test_errors(r: TestRunner) -> None:
    patch_no_id = requests.patch(r.url("/orders"), json={"status": "delivered"}, timeout=5)
    r.check("1. PATCH /orders without id returns 405", patch_no_id.status_code == 405)

    bad_json = requests.post(
        r.url("/products"),
        data="{invalid-json",
        headers={"Content-Type": "application/json"},
        timeout=5,
    )
    r.check("Malformed JSON returns 400", bad_json.status_code == 400)

    unknown_route = requests.get(r.url("/does-not-exist"), timeout=5)
    r.check("Unknown route returns 404", unknown_route.status_code == 404)


def test_stretch(r: TestRunner) -> None:
    page_resp = requests.get(r.url("/products?page=1&limit=2"), timeout=5)
    r.check("GET /products?page=1&limit=2 returns 200", page_resp.status_code == 200)
    page_data = page_resp.json() if page_resp.status_code == 200 else {}
    r.check(
        "Paginated products has items, total, page, limit, total_pages, has_next, has_prev",
        all(k in page_data for k in ("items", "total", "page", "limit", "total_pages", "has_next", "has_prev")),
    )
    r.check("GET /products?limit=200 returns 400", requests.get(r.url("/products?limit=200"), timeout=5).status_code == 400)

    cust_page = requests.get(r.url("/customers?page=1&limit=2"), timeout=5)
    r.check("GET /customers?page=1&limit=2 returns 200", cust_page.status_code == 200)
    cust_data = cust_page.json() if cust_page.status_code == 200 else {}
    r.check("Paginated customers has items and total_pages", "items" in cust_data and "total_pages" in cust_data)

    ord_page = requests.get(r.url("/orders?page=1&limit=2"), timeout=5)
    r.check("GET /orders?page=1&limit=2 returns 200", ord_page.status_code == 200)
    ord_data = ord_page.json() if ord_page.status_code == 200 else {}
    r.check("Paginated orders has items and total_pages", "items" in ord_data and "total_pages" in ord_data)

    cust_orders = requests.get(r.url("/customers/1/orders"), timeout=5)
    r.check("GET /customers/1/orders returns 200", cust_orders.status_code == 200)
    r.check("GET /customers/1/orders returns list", isinstance(cust_orders.json(), list))

    reports_index = requests.get(r.url("/reports"), timeout=5)
    r.check("GET /reports returns 200", reports_index.status_code == 200)

    sales_resp = requests.get(r.url("/reports/sales-by-product"), timeout=5)
    r.check("GET /reports/sales-by-product returns 200", sales_resp.status_code == 200)

    top_resp = requests.get(r.url("/reports/top-customers?limit=3"), timeout=5)
    r.check("GET /reports/top-customers?limit=3 returns 200", top_resp.status_code == 200)


GROUPS = {
    "health": test_health,
    "products": test_products,
    "customers": test_customers,
    "orders": test_orders_and_items,
    "errors": test_errors,
    "stretch": test_stretch,
}


def interactive_menu(runner: TestRunner) -> None:
    group_names = list(GROUPS.keys())
    while True:
        print("\n=== ShopEasy API Test Menu ===")
        for idx, name in enumerate(group_names, start=1):
            print(f"  {idx}. {name}")
        print(f"  {len(group_names) + 1}. all")
        print("  0. exit")
        choice = input("Select an option: ").strip().lower()
        if choice in {"0", "exit", "q"}:
            break
        if choice == str(len(group_names) + 1) or choice == "all":
            for fn in GROUPS.values():
                fn(runner)
        elif choice.isdigit() and 1 <= int(choice) <= len(group_names):
            GROUPS[group_names[int(choice) - 1]](runner)
        else:
            print("Invalid selection.")


def main() -> int:
    parser = argparse.ArgumentParser(description="ShopEasy API test client")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--all", action="store_true", help="Run all test groups")
    parser.add_argument("--group", nargs="+", choices=list(GROUPS.keys()), help="Run specific groups")
    parser.add_argument("--list", action="store_true", help="List available test groups")
    args = parser.parse_args()

    if args.list:
        for name in GROUPS:
            print(name)
        return 0

    runner = TestRunner(args.base_url)

    if args.all:
        for fn in GROUPS.values():
            fn(runner)
    elif args.group:
        for name in args.group:
            GROUPS[name](runner)
    else:
        interactive_menu(runner)

    print(f"\nSummary: {runner.passed} passed, {runner.failed} failed")
    return 0 if runner.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())