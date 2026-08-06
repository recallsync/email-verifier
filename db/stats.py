"""Dashboard statistics."""

from db.connection import get_connection


def get_stats() -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COALESCE(SUM(processed_rows), 0)::BIGINT AS total_emails_verified,
                    COUNT(*) FILTER (WHERE status = 'completed')::INTEGER AS total_lists_completed,
                    COUNT(*)::INTEGER AS total_lists
                FROM lists
                """
            )
            row = cur.fetchone()
    return {
        "total_emails_verified": row["total_emails_verified"],
        "total_lists_completed": row["total_lists_completed"],
        "total_lists": row["total_lists"],
    }
