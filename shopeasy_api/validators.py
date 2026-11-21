from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from shopeasy_api.errors import ApiError

VALID_ORDER_STATUSES = {"pending", "delivered", "cancelled"}
VALID_PRODUCT_SORTS = {"price", "-price", "name", "-name"}


def parse_positive_int(value: Any, field_name: str, status_code: int = 400) -> int:
    if isinstance(value, bool) or value is None:
        raise ApiError(status_code, f"{field_name} must be a positive integer")
    try:
        ivalue = int(str(value).strip())
    except (ValueError, TypeError) as exc:
        raise ApiError(status_code, f"{field_name} must be a positive integer") from exc
    if ivalue <= 0:
        raise ApiError(status_code, f"{field_name} must be greater than 0")
    return ivalue


def parse_non_negative_int(value: Any, field_name: str, status_code: int = 422) -> int:
    if isinstance(value, bool) or value is None:
        raise ApiError(status_code, f"{field_name} must be a non-negative integer")
    try:
        str_val = str(value).strip()
        if "." in str_val:
            raise ApiError(status_code, f"{field_name} must be a whole number")
        ivalue = int(str_val)
    except (ValueError, TypeError) as exc:
        raise ApiError(status_code, f"{field_name} must be a whole number") from exc
    if ivalue < 0:
        raise ApiError(status_code, f"{field_name} cannot be negative")
    return ivalue


def parse_non_negative_decimal(value: Any, field_name: str, status_code: int = 422) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ApiError(status_code, f"{field_name} must be a valid number")
    try:
        dval = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ApiError(status_code, f"{field_name} must be a valid number") from exc
    if dval.is_nan() or dval.is_infinite():
        raise ApiError(status_code, f"{field_name} must be a finite number")
    if dval < Decimal("0"):
        raise ApiError(status_code, f"{field_name} cannot be negative")
    return dval


def require_non_empty_string(value: Any, field_name: str, max_len: int = 200) -> str:
    if not isinstance(value, str):
        raise ApiError(400, f"{field_name} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ApiError(400, f"{field_name} is required")
    if len(cleaned) > max_len:
        raise ApiError(422, f"{field_name} must be at most {max_len} characters")
    return cleaned


def validate_email(value: Any) -> str:
    if value is None:
        raise ApiError(400, "email is required")
    if not isinstance(value, str):
        raise ApiError(422, "email must be a string")
    email = value.strip()
    if not email:
        raise ApiError(400, "email is required")
    if len(email) > 150 or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ApiError(422, "email is invalid")
    return email


def validate_optional_city(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ApiError(422, "city must be a string or null")
    cleaned = value.strip()
    if len(cleaned) > 100:
        raise ApiError(422, "city must be at most 100 characters")
    return cleaned if cleaned else None


def validate_order_status(value: Any) -> str:
    if not isinstance(value, str) or value.strip() not in VALID_ORDER_STATUSES:
        raise ApiError(422, "status must be one of: pending, delivered, cancelled")
    return value.strip()