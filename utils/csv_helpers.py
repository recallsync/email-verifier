"""CSV parsing helpers for list uploads."""

import re
from typing import Any

EMAIL_PATTERN = re.compile(r"email", re.IGNORECASE)


def detect_email_column(
    columns: list[str],
    override: str | None = None,
) -> tuple[str | None, str | None, list[str]]:
    """
    Returns (column_name, error_code, candidate_columns).
    error_code is None on success.
    """
    if override:
        if override not in columns:
            return None, "invalid_email_column", columns
        return override, None, columns

    exact = [c for c in columns if c.lower().strip() == "email"]
    if len(exact) == 1:
        return exact[0], None, columns

    email_like = [c for c in columns if EMAIL_PATTERN.search(c)]
    if len(exact) > 1:
        return None, "ambiguous_email_column", exact
    if len(email_like) == 1:
        return email_like[0], None, columns
    if len(email_like) > 1:
        return None, "ambiguous_email_column", email_like
    return None, "no_email_column", columns


def estimate_duration(total_rows: int, concurrency: int) -> str:
    if total_rows <= 0:
        return "0m"
    concurrency = max(1, concurrency)
    low_seconds = total_rows * 3 / concurrency
    high_seconds = total_rows * 8 / concurrency
    return f"{_format_seconds(low_seconds)} – {_format_seconds(high_seconds)}"


def _format_seconds(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    rem = minutes % 60
    if rem:
        return f"{hours}h {rem}m"
    return f"{hours}h"
