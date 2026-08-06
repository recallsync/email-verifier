"""List and list_row queries for the chunk processor."""

from typing import Any
from uuid import UUID

RowResult = dict[str, Any]


def promote_queued_list(cur) -> RowResult | None:
    """Promote oldest queued list if no list is currently processing."""
    cur.execute(
        """
        UPDATE lists
        SET status = 'processing',
            started_at = COALESCE(started_at, now()),
            updated_at = now()
        WHERE id = (
            SELECT id FROM lists
            WHERE status = 'queued'
            ORDER BY created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        AND NOT EXISTS (
            SELECT 1 FROM lists WHERE status = 'processing'
        )
        RETURNING *
        """
    )
    return cur.fetchone()


def get_processing_list(cur) -> RowResult | None:
    cur.execute(
        """
        SELECT * FROM lists
        WHERE status = 'processing'
        ORDER BY started_at ASC NULLS LAST
        LIMIT 1
        """
    )
    return cur.fetchone()


def get_list_status(cur, list_id: UUID) -> str | None:
    cur.execute("SELECT status FROM lists WHERE id = %s", (list_id,))
    row = cur.fetchone()
    return row["status"] if row else None


def claim_rows(cur, list_id: UUID, limit: int) -> list[RowResult]:
    cur.execute(
        """
        UPDATE list_rows
        SET status = 'processing', picked_at = now()
        WHERE id IN (
            SELECT id FROM list_rows
            WHERE list_id = %s AND status = 'pending'
            ORDER BY row_index
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id, list_id, row_index, raw_row, email, status
        """,
        (list_id, limit),
    )
    return cur.fetchall()


def count_pending_rows(cur, list_id: UUID) -> int:
    cur.execute(
        """
        SELECT COUNT(*) AS count FROM list_rows
        WHERE list_id = %s AND status IN ('pending', 'processing')
        """,
        (list_id,),
    )
    return cur.fetchone()["count"]


def write_row_results(cur, list_id: UUID, results: list[tuple[int, str, str]]) -> None:
    """Write verification results. results: [(row_id, status, reason), ...]"""
    for row_id, status, reason in results:
        cur.execute(
            """
            UPDATE list_rows
            SET status = %s::row_status,
                reason = %s,
                checked_at = now()
            WHERE id = %s AND list_id = %s
            """,
            (status, reason, row_id, list_id),
        )

        cur.execute(
            """
            UPDATE lists SET
                processed_rows = processed_rows + 1,
                verified_count = verified_count + CASE WHEN %s = 'verified' THEN 1 ELSE 0 END,
                risky_count = risky_count + CASE WHEN %s = 'risky' THEN 1 ELSE 0 END,
                failed_count = failed_count + CASE WHEN %s = 'failed' THEN 1 ELSE 0 END,
                updated_at = now()
            WHERE id = %s
            """,
            (status, status, status, list_id),
        )


def finalize_list_if_done(cur, list_id: UUID) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS count FROM list_rows
        WHERE list_id = %s AND status IN ('pending', 'processing')
        """,
        (list_id,),
    )
    if cur.fetchone()["count"] > 0:
        return False

    cur.execute(
        """
        UPDATE lists
        SET status = 'completed',
            completed_at = now(),
            updated_at = now()
        WHERE id = %s AND status = 'processing'
        RETURNING id
        """,
        (list_id,),
    )
    return cur.fetchone() is not None


def touch_list(cur, list_id: UUID) -> None:
    cur.execute(
        "UPDATE lists SET updated_at = now() WHERE id = %s",
        (list_id,),
    )


def recover_stale_rows(cur) -> int:
    """Fallback when pg_cron is unavailable."""
    cur.execute(
        """
        UPDATE list_rows
        SET status = 'pending', picked_at = NULL
        WHERE status = 'processing'
          AND picked_at < now() - interval '10 minutes'
        """
    )
    return cur.rowcount
