from typing import Tuple
from shopeasy_api.db import get_cursor
from shopeasy_api.errors import ApiError
from shopeasy_api.http_utils import Request


def health_check(request: Request) -> Tuple[int, dict]:
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return 200, {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise ApiError(500, "Database health check failed") from exc