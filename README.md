# ShopEasy API

A modular RESTful backend built with **Python's standard library** (`http.server`, `urllib.parse`, `json`, `re`, `argparse`, `time`) and **PostgreSQL** (`psycopg2` with `SimpleConnectionPool`), structured cleanly around the **Model–View–Controller (MVC)** pattern.

---

## Table of Contents

1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [Directory Structure](#2-directory-structure)
3. [Database Prerequisites](#3-database-prerequisites)
4. [Environment Configuration](#4-environment-configuration)
5. [Installation & Setup](#5-installation--setup)
6. [Running the Server](#6-running-the-server)
7. [API Specification & Endpoints](#7-api-specification--endpoints)
8. [Order Processing & Transaction Rules](#8-order-processing--transaction-rules)
9. [Running the Test Suite (`test_api.py`)](#9-running-the-test-suite-test_apipy)
10. [Request Lifecycle Trace (`GET /products/3`)](#10-request-lifecycle-trace-get-products3)
11. [Submission & Security Checklist](#11-submission--security-checklist)

---

## 1. Project Overview & Architecture

ShopEasy API implements a layered MVC architecture with strict separation of responsibilities:

| Layer | Files | Responsibilities | Restrictions |
| :--- | :--- | :--- | :--- |
| **HTTP / Routing** | `server.py`, `router.py`, `http_utils.py` | Parse URLs/queries/JSON, match routes, dispatch handlers, log request timing, send JSON responses | Must **NOT** contain SQL or business rules |
| **Controller** | `controllers/*.py`, `validators.py` | Validate input, call models, select HTTP status codes, raise `ApiError` | Must **NOT** contain SQL |
| **Model** | `models/*.py`, `db.py` | Execute parameterized SQL queries, manage connection pool, transactions, and row locks (`FOR UPDATE`) | Must **NOT** know about HTTP or JSON |
| **View** | `views.py` | Format response payloads, monetary strings (`"0.00"`), and ISO 8601 dates | Must **NOT** query the database |

---

## 2. Directory Structure

```text
shopeasy-api/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── test_api.py
└── shopeasy_api/
    ├── __init__.py
    ├── server.py                  # Entry point, HTTP request handler & timing logs
    ├── config.py                  # Environment variable loader & settings
    ├── errors.py                  # Custom ApiError exception
    ├── db.py                      # PostgreSQL connection pool & transaction helpers
    ├── http_utils.py              # Request dataclass, JSON body parser & response writer
    ├── validators.py              # Input validation helpers
    ├── router.py                  # Regex URL pattern matcher & method dispatcher
    ├── views.py                   # JSON response formatters
    ├── models/
    │   ├── __init__.py
    │   ├── product.py             # SQL queries & pagination for products
    │   ├── customer.py            # SQL queries for customers
    │   ├── order.py               # SQL queries & atomic transactions for orders/items
    │   └── report.py              # Reporting queries (sales by product, top customers, reports list)
    └── controllers/
        ├── __init__.py
        ├── health_controller.py   # Health check endpoint logic
        ├── product_controller.py  # Product CRUD & pagination orchestration
        ├── customer_controller.py # Customer CRUD & customer orders orchestration
        ├── order_controller.py    # Order & order items validation & orchestration
        └── report_controller.py   # Reporting endpoints orchestration
```

---

## 3. Database Prerequisites

The API requires PostgreSQL with the core tables initialized and populated:

| Table | Columns & Constraints |
| :--- | :--- |
| `customers` | `id` (PK), `name`, `email` (`UNIQUE`), `city`, `created_at` |
| `products` | `id` (PK), `name`, `price` ($\ge 0$), `stock` ($\ge 0$) |
| `orders` | `id` (PK), `customer_id` (FK $\rightarrow$ `customers.id`), `order_date`, `status` (`pending` / `delivered` / `cancelled`) |
| `order_items` | `id` (PK), `order_id` (FK $\rightarrow$ `orders.id`), `product_id` (FK $\rightarrow$ `products.id`), `quantity` ($> 0$) |
| `reports` | `id` (PK), `name` (`UNIQUE`), `endpoint`, `description` (optional metadata table for `GET /reports`) |

### Schema SQL

```sql
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    city VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    stock INT NOT NULL DEFAULT 0 CHECK (stock >= 0)
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id),
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'delivered', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(id),
    product_id INT NOT NULL REFERENCES products(id),
    quantity INT NOT NULL CHECK (quantity > 0)
);

CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    endpoint VARCHAR(255) NOT NULL,
    description TEXT
);
```

### Verify Table Readiness

```sql
SELECT COUNT(*) FROM customers;
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM orders;
SELECT COUNT(*) FROM order_items;
SELECT COUNT(*) FROM reports;
```

---

## 4. Environment Configuration

Database credentials, connection pool limits, and server ports are loaded from environment variables (or a local `.env` file). Never hardcode passwords in source code.

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Update `.env` with your PostgreSQL credentials:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=shopeasy
   DB_USER=shop_user
   DB_PASSWORD=your_password
   DB_MIN_CONN=1
   DB_MAX_CONN=10
   API_HOST=127.0.0.1
   API_PORT=8000
   ```

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DB_HOST` | `localhost` | PostgreSQL server hostname |
| `DB_PORT` | `5432` | PostgreSQL server port |
| `DB_NAME` | `shopeasy` | Target PostgreSQL database name |
| `DB_USER` | `shop_user` | PostgreSQL role with `SELECT`, `INSERT`, `UPDATE`, `DELETE` privileges |
| `DB_PASSWORD` | `""` | Password for `DB_USER` |
| `DB_MIN_CONN` | `1` | Minimum connections in `SimpleConnectionPool` |
| `DB_MAX_CONN` | `10` | Maximum connections in `SimpleConnectionPool` |
| `API_HOST` | `127.0.0.1` | Host interface to bind the HTTP server |
| `API_PORT` | `8000` | Port to listen on |

---

## 5. Installation & Setup

1. **Clone the repository and enter the directory:**
   ```bash
   git clone https://github.com/saswata35/shopeasy_api.git
   cd shopeasy_api
   ```

2. **Create and activate a virtual environment:**
   * **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   * **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 6. Running the Server

Start the HTTP server from the project root directory:

```bash
python -m shopeasy_api.server
```

Expected output:
```text
ShopEasy API listening on http://127.0.0.1:8000
```

---

## 7. API Specification & Endpoints

### Global Conventions
* **Content Type:** All request and response bodies use `application/json`.
* **Monetary Values:** Formatted as fixed 2-decimal strings (e.g., `"799.00"`).
* **Dates:** Formatted as ISO 8601 strings (e.g., `"2026-03-15"`).
* **Error Responses:** Always returned as `{"error": "human readable message"}`.
* **Empty Success:** `204 No Content` returns an empty body.

### HTTP Status Codes

| Code | Meaning |
| :--- | :--- |
| `200` | Read or update succeeded |
| `201` | New resource created |
| `204` | Resource deleted successfully |
| `400` | Malformed request (invalid JSON, non-object body, missing required field, invalid query/path param) |
| `404` | Resource or route does not exist |
| `405` | Route exists, but HTTP method is not allowed |
| `409` | Data conflict (duplicate email, insufficient stock, foreign key reference, illegal status transition) |
| `422` | Semantic validation failure (negative price, invalid email, unknown order status, empty items list) |
| `500` | Internal server error (logged on server; details hidden from client) |

### Endpoint Reference

#### Health
| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Verifies server and PostgreSQL database connectivity | `200`, `500` |

#### Products
| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/products` | List products. Optional filters: `?max_price=`, `?min_price=`, `?in_stock=true`, `?sort=price` (`-price`, `name`, `-name`), `?page=`, `?limit=` | `200`, `400` |
| `GET` | `/products/{id}` | Retrieve a single product by ID | `200`, `400`, `404` |
| `POST` | `/products` | Create a product (`name`, `price`, optional `stock`) | `201`, `400`, `422` |
| `PATCH` | `/products/{id}` | Update any of `name`, `price`, `stock` | `200`, `400`, `404`, `422` |
| `DELETE` | `/products/{id}` | Delete a product (refused if referenced by any order item) | `204`, `400`, `404`, `409` |

#### Customers
| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/customers` | List customers. Optional filter: `?city=` | `200` |
| `GET` | `/customers/{id}` | Retrieve a single customer by ID | `200`, `400`, `404` |
| `GET` | `/customers/{id}/orders` | List all orders belonging to a single customer | `200`, `400`, `404` |
| `POST` | `/customers` | Create a customer (`name`, `email`, optional `city`) | `201`, `400`, `409`, `422` |
| `PATCH` | `/customers/{id}` | Update any of `name`, `email`, `city` | `200`, `400`, `404`, `409`, `422` |
| `DELETE` | `/customers/{id}` | Delete a customer (refused if customer has existing orders) | `204`, `400`, `404`, `409` |

#### Orders & Order Items
| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/orders` | List orders with `customer_name` and calculated `total`. Optional filters: `?status=`, `?customer_id=` | `200`, `400`, `422` |
| `GET` | `/orders/{id}` | Retrieve full order detail (`customer`, `items`, `total`) | `200`, `400`, `404` |
| `POST` | `/orders` | Place an order atomically (`customer_id`, `items`) | `201`, `400`, `404`, `409`, `422` |
| `PATCH` | `/orders/{id}` | Update order status (`{"status": "delivered" \| "cancelled"}`) | `200`, `400`, `404`, `409`, `422` |
| `DELETE` | `/orders/{id}` | Delete a `cancelled` order and its items | `204`, `400`, `404`, `409` |
| `GET` | `/orders/{id}/items` | Retrieve line items for a single order with `line_total` | `200`, `400`, `404` |
| `POST` | `/orders/{id}/items` | Add an item to a `pending` order and decrement stock atomically | `201`, `400`, `404`, `409`, `422` |
| `DELETE` | `/orders/{id}/items/{item_id}` | Remove an item from a `pending` order and restore stock atomically | `204`, `400`, `404`, `409` |

#### Reports
| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/reports` | List available report endpoints from the `reports` table | `200` |
| `GET` | `/reports/sales-by-product` | Units sold and revenue aggregated per product | `200` |
| `GET` | `/reports/top-customers` | Top customers ranked by total spent on `delivered` orders (`?limit=3`) | `200`, `400` |

---

## 8. Order Processing & Transaction Rules

### Placing an Order (`POST /orders`)
* **Validation:** Requires `customer_id` and a non-empty `items` array (`400` if missing, `422` if `items` is empty, `quantity < 1`, or a `product_id` appears more than once).
* **Atomicity & Locking:** Locks product rows with `SELECT ... FOR UPDATE`, verifies customer and product existence (`404`), and checks available stock (`409` if insufficient). If any check fails, the entire transaction rolls back so no partial order or stock change is saved.
* **Success (`201`):** Creates the order with status `pending`, inserts all `order_items`, and decrements each product's `stock` in a single database transaction.

### Updating Order Status (`PATCH /orders/{id}`)
* `pending` $\rightarrow$ `delivered`: Succeeds (`200`).
* `pending` $\rightarrow$ `cancelled`: Succeeds (`200`) and restores all ordered item quantities back to `products.stock` within the same transaction.
* Any other status transition (e.g., `cancelled` $\rightarrow$ `delivered` or `delivered` $\rightarrow$ `cancelled`): Rejected with `409`.
* Unrecognized status string: Rejected with `422`.

### Deleting an Order (`DELETE /orders/{id}`)
* Only orders with status `cancelled` can be deleted (`409` if `pending` or `delivered`).
* Deletes child rows in `order_items` first, then deletes the parent row in `orders` within a single transaction (`204`).

---

## 9. Running the Test Suite (`test_api.py`)

With the server running in one terminal, open a second terminal and run `test_api.py`:

```bash
# Run all automated checks across all groups
python test_api.py --all

# Run specific endpoint groups
python test_api.py --group products customers
python test_api.py --group orders errors stretch

# List available test groups
python test_api.py --list

# Target a custom server URL
python test_api.py --base-url http://localhost:9000 --all

# Launch interactive menu mode
python test_api.py
```

* Exit code `0` indicates all tests passed (`0` failed).
* Exit code `1` indicates one or more assertions failed.

---

## 10. Request Lifecycle Trace (`GET /products/3`)

1. **URL & Query Parsing:** `shopeasy_api/server.py` (`ShopEasyHandler._handle`) parses `/products/3` via `urllib.parse.urlparse`.
2. **Route Matching:** `shopeasy_api/router.py` (`Router.resolve`) matches `/products/{id}` for `GET` and maps to `product_controller.get_product` with `params={"id": "3"}`.
3. **Database Query:** `shopeasy_api/models/product.py` (`get_by_id(3)`) runs `SELECT id, name, price, stock FROM products WHERE id = %s` using a pooled connection from `db.py`.
4. **Response Formatting:** `shopeasy_api/views.py` (`product_view`) selects `id`, `name`, `price` (formatted to 2 decimal places), and `stock`.
5. **Status Code Decision:** `shopeasy_api/controllers/product_controller.py` (`get_product`) returns `(200, product_view(row))`.
6. **Invalid ID Handling (`GET /products/abc`):** `parse_positive_int` in `validators.py` raises `ApiError(400, "id must be a positive integer")`, returning HTTP `400` with `{"error": "id must be a positive integer"}` without querying PostgreSQL.

---

## 11. Submission & Security Checklist

- [x] Folder layout matches specification with clean separation between HTTP/routing, Controllers, Models, and Views.
- [x] All Health, Product, Customer, Order, Order Item, and Report endpoints return the specified HTTP status codes.
- [x] All credentials are externalized via `.env`; no passwords or secrets exist in source code.
- [x] `.gitignore` excludes `venv/`, `.venv/`, `__pycache__/`, `*.py[cod]`, and `.env`.
- [x] Order creation rollback proof (`409` on insufficient stock with zero partial writes) and cancellation stock restoration are verified in `test_api.py`.
- [x] `python test_api.py --all` passes with `0` failed checks.