"""Settings read/write from PostgreSQL."""

import json
from typing import Any

from db.connection import get_connection

DEFAULT_SETTINGS: dict[str, Any] = {
    "concurrency": 10,
    "timeout_seconds": 15,
    "retry_count": 1,
    "smtp_helo_domain": "",
    "chunk_time_budget_seconds": 50,
    "theme": "dark",
    "max_upload_size_mb": 50,
}


def _parse_value(raw: Any) -> Any:
    if isinstance(raw, (dict, list, int, float, bool)) or raw is None:
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


def get_all_settings(conn=None) -> dict[str, Any]:
    query = "SELECT key, value FROM settings"

    if conn is not None:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
    else:
        with get_connection() as c:
            with c.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()

    result = dict(DEFAULT_SETTINGS)
    for row in rows:
        result[row["key"]] = _parse_value(row["value"])
    return result


def get_settings_snapshot(conn=None) -> dict[str, Any]:
    """Settings frozen for list processing."""
    settings = get_all_settings(conn)
    return {
        "concurrency": settings["concurrency"],
        "timeout_seconds": settings["timeout_seconds"],
        "retry_count": settings["retry_count"],
        "smtp_helo_domain": settings["smtp_helo_domain"],
        "chunk_time_budget_seconds": settings["chunk_time_budget_seconds"],
    }


SETTINGS_RULES = {
    "concurrency": {"type": int, "min": 1, "max": 50},
    "timeout_seconds": {"type": int, "min": 5, "max": 60},
    "retry_count": {"type": int, "min": 0, "max": 3},
    "chunk_time_budget_seconds": {"type": int, "min": 10, "max": 120},
    "max_upload_size_mb": {"type": int, "min": 1, "max": 500},
    "smtp_helo_domain": {"type": str},
    "theme": {"type": str, "choices": {"dark", "light"}},
}


def validate_settings_update(updates: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    validated: dict[str, Any] = {}
    for key, value in updates.items():
        if key not in DEFAULT_SETTINGS:
            return {}, f"Unknown setting: {key}"

        rules = SETTINGS_RULES.get(key, {})
        expected_type = rules.get("type")
        if expected_type is int:
            try:
                value = int(value)
            except (TypeError, ValueError):
                return {}, f"{key} must be an integer"
        elif expected_type is str:
            value = str(value)

        if "min" in rules and value < rules["min"]:
            return {}, f"{key} must be >= {rules['min']}"
        if "max" in rules and value > rules["max"]:
            return {}, f"{key} must be <= {rules['max']}"
        if "choices" in rules and value not in rules["choices"]:
            return {}, f"{key} must be one of: {', '.join(sorted(rules['choices']))}"

        validated[key] = value

    return validated, None


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    validated, error = validate_settings_update(updates)
    if error:
        raise ValueError(error)

    if not validated:
        return get_all_settings()

    with get_connection() as conn:
        with conn.cursor() as cur:
            for key, value in validated.items():
                cur.execute(
                    """
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (%s, %s::jsonb, now())
                    ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value, updated_at = now()
                    """,
                    (key, json.dumps(value)),
                )
    return get_all_settings()

