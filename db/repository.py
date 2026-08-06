"""List repository — CRUD and state transitions."""

import json
from typing import Any
from uuid import UUID

RowResult = dict[str, Any]


LIST_COLUMNS = """
    id, name, filename, status, email_column,
    total_rows, processed_rows, verified_count, risky_count,
    failed_count, skipped_count, settings_snapshot,
    original_file_path, created_at, started_at, completed_at, updated_at
"""


def create_list(cur, name: str) -> RowResult:
    cur.execute(
        """
        INSERT INTO lists (name)
        VALUES (%s)
        RETURNING *
        """,
        (name.strip(),),
    )
    return cur.fetchone()


def get_list(cur, list_id: UUID) -> RowResult | None:
    cur.execute("SELECT * FROM lists WHERE id = %s", (list_id,))
    return cur.fetchone()


def list_lists(
    cur,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[RowResult], int]:
    if status:
        cur.execute(
            """
            SELECT * FROM lists WHERE status = %s::list_status
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (status, limit, offset),
        )
        rows = cur.fetchall()
        cur.execute(
            "SELECT COUNT(*) AS count FROM lists WHERE status = %s::list_status",
            (status,),
        )
    else:
        cur.execute(
            """
            SELECT * FROM lists
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(*) AS count FROM lists")

    total = cur.fetchone()["count"]
    return rows, total


def delete_list(cur, list_id: UUID) -> bool:
    cur.execute(
        """
        DELETE FROM lists
        WHERE id = %s AND status != 'processing'
        RETURNING id
        """,
        (list_id,),
    )
    return cur.fetchone() is not None


def clear_list_rows(cur, list_id: UUID) -> None:
    cur.execute("DELETE FROM list_rows WHERE list_id = %s", (list_id,))


def insert_list_rows_batch(cur, list_id: UUID, rows: list[tuple[int, dict, str]]) -> None:
    """rows: [(row_index, raw_row_dict, email), ...]"""
    if not rows:
        return
    cur.executemany(
        """
        INSERT INTO list_rows (list_id, row_index, raw_row, email, status)
        VALUES (%s, %s, %s::jsonb, %s, 'pending')
        """,
        [(list_id, idx, json.dumps(raw), email) for idx, raw, email in rows],
    )


def update_list_after_upload(
    cur,
    list_id: UUID,
    filename: str,
    email_column: str,
    total_rows: int,
    file_path: str,
) -> RowResult:
    cur.execute(
        """
        UPDATE lists SET
            filename = %s,
            email_column = %s,
            total_rows = %s,
            original_file_path = %s,
            processed_rows = 0,
            verified_count = 0,
            risky_count = 0,
            failed_count = 0,
            skipped_count = 0,
            updated_at = now()
        WHERE id = %s AND status = 'draft'
        RETURNING *
        """,
        (filename, email_column, total_rows, file_path, list_id),
    )
    return cur.fetchone()


def queue_list(cur, list_id: UUID, settings_snapshot: dict) -> RowResult | None:
    cur.execute(
        """
        UPDATE lists SET
            status = 'queued',
            settings_snapshot = %s::jsonb,
            updated_at = now()
        WHERE id = %s AND status = 'draft' AND total_rows > 0 AND email_column IS NOT NULL
        RETURNING *
        """,
        (json.dumps(settings_snapshot), list_id),
    )
    return cur.fetchone()


def get_queue_position(cur, list_id: UUID) -> int:
    cur.execute(
        """
        SELECT COUNT(*) AS position
        FROM lists
        WHERE status = 'queued'
          AND created_at <= (SELECT created_at FROM lists WHERE id = %s)
        """,
        (list_id,),
    )
    return cur.fetchone()["position"]


def pause_list(cur, list_id: UUID) -> RowResult | None:
    cur.execute(
        """
        UPDATE lists SET status = 'paused', updated_at = now()
        WHERE id = %s AND status = 'processing'
        RETURNING *
        """,
        (list_id,),
    )
    return cur.fetchone()


def resume_list(cur, list_id: UUID) -> RowResult | None:
    cur.execute(
        "SELECT COUNT(*) AS count FROM lists WHERE status = 'processing'"
    )
    has_active = cur.fetchone()["count"] > 0
    new_status = "queued" if has_active else "processing"

    cur.execute(
        """
        UPDATE lists SET status = %s::list_status, updated_at = now()
        WHERE id = %s AND status = 'paused'
        RETURNING *
        """,
        (new_status, list_id),
    )
    return cur.fetchone()


def cancel_list(cur, list_id: UUID) -> RowResult | None:
    cur.execute(
        """
        UPDATE lists SET
            status = 'cancelled',
            completed_at = now(),
            updated_at = now()
        WHERE id = %s AND status IN ('queued', 'processing', 'paused')
        RETURNING *
        """,
        (list_id,),
    )
    row = cur.fetchone()
    if not row:
        return None

    cur.execute(
        """
        WITH skipped AS (
            UPDATE list_rows SET status = 'skipped'
            WHERE list_id = %s AND status = 'pending'
            RETURNING id
        )
        UPDATE lists SET skipped_count = skipped_count + (SELECT COUNT(*) FROM skipped)
        WHERE id = %s
        """,
        (list_id, list_id),
    )
    return get_list(cur, list_id)


def get_list_rows(
    cur,
    list_id: UUID,
    status: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[RowResult], int]:
    conditions = ["list_id = %s"]
    params: list[Any] = [list_id]

    if status:
        conditions.append("status = %s::row_status")
        params.append(status)
    if search:
        conditions.append("email ILIKE %s")
        params.append(f"%{search}%")

    where = " AND ".join(conditions)

    cur.execute(
        f"""
        SELECT row_index, email, status, reason, raw_row, checked_at
        FROM list_rows
        WHERE {where}
        ORDER BY row_index
        LIMIT %s OFFSET %s
        """,
        (*params, limit, offset),
    )
    rows = cur.fetchall()

    cur.execute(
        f"SELECT COUNT(*) AS count FROM list_rows WHERE {where}",
        tuple(params),
    )
    total = cur.fetchone()["count"]
    return rows, total


def iter_export_rows(cur, list_id: UUID, filter_type: str = "all"):
    """Yield list_rows for CSV export ordered by row_index."""
    if filter_type == "risky_failed":
        status_filter = "AND status IN ('risky', 'failed')"
    else:
        status_filter = ""

    cur.execute(
        f"""
        SELECT raw_row, status, reason
        FROM list_rows
        WHERE list_id = %s {status_filter}
        ORDER BY row_index
        """,
        (list_id,),
    )
    while True:
        batch = cur.fetchmany(500)
        if not batch:
            break
        for row in batch:
            yield row


def get_progress(cur, list_id: UUID) -> RowResult | None:
    cur.execute(
        """
        SELECT
            total_rows AS total,
            processed_rows AS processed,
            verified_count AS verified,
            risky_count AS risky,
            failed_count AS failed,
            status
        FROM lists WHERE id = %s
        """,
        (list_id,),
    )
    return cur.fetchone()
