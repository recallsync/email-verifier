"""JSON serialization helpers."""

from datetime import datetime
from typing import Any
from uuid import UUID


def serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [serialize_value(v) for v in value]
    return value


def serialize_list(row: dict | None) -> dict | None:
    if not row:
        return None
    return serialize_value(dict(row))
