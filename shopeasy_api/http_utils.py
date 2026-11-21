import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from shopeasy_api.errors import ApiError


@dataclass
class Request:
    method: str
    path: str
    query: Dict[str, str]
    params: Dict[str, Any]
    body: Optional[Dict[str, Any]]


def parse_json_body(raw_bytes: bytes) -> Optional[Dict[str, Any]]:
    if not raw_bytes:
        return None
    try:
        decoded = raw_bytes.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ApiError(400, "Request body must be valid UTF-8") from exc

    if not decoded:
        return None

    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ApiError(400, "Malformed JSON in request body") from exc

    if not isinstance(parsed, dict):
        raise ApiError(400, "JSON body must be an object")

    return parsed


def send_json(handler, status_code: int, payload: Any = None) -> None:
    if status_code == 204:
        handler.send_response(204)
        handler.end_headers()
        return

    body_bytes = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body_bytes)))
    handler.end_headers()
    handler.wfile.write(body_bytes)