"""Bulk list chunk processor."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import UUID

from db.connection import get_connection
from db import lists as list_queries
from db.settings import get_all_settings
from utils.email_utils import check_email
from utils.status import map_internal_status
from utils.verification_settings import VerificationSettings

logger = logging.getLogger(__name__)

_tick_count = 0
MAINTENANCE_EVERY_N_TICKS = 20  # ~5 min at 15s interval


def verify_row(email: str, settings: VerificationSettings) -> tuple[str, str]:
    if not email or not email.strip():
        return "failed", "empty_email"

    internal_status, reason = check_email(email.strip(), settings=settings)
    return map_internal_status(internal_status), reason


def _verify_batch_with_concurrency(
    rows: list[dict],
    settings: VerificationSettings,
    concurrency: int,
) -> list[tuple[int, str, str]]:
    results: list[tuple[int, str, str]] = []

    def _check(row: dict) -> tuple[int, str, str]:
        status, reason = verify_row(row["email"], settings)
        return row["id"], status, reason

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(_check, row): row for row in rows}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                row = futures[future]
                logger.exception("Verification failed for row %s: %s", row["id"], exc)
                results.append((row["id"], "failed", "verification_error"))

    return results


def process_chunk() -> None:
    global _tick_count
    _tick_count += 1

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if _tick_count % MAINTENANCE_EVERY_N_TICKS == 0:
                    recovered = list_queries.recover_stale_rows(cur)
                    if recovered:
                        logger.info("Recovered %d stale rows", recovered)

                list_queries.promote_queued_list(cur)

                active = list_queries.get_processing_list(cur)
                if not active:
                    return

                list_id = active["id"]
                snapshot = active.get("settings_snapshot") or {}
                global_settings = get_all_settings(conn)
                merged = {**global_settings, **snapshot}
                concurrency = max(1, min(int(merged.get("concurrency", 10)), 50))
                time_budget = int(merged.get("chunk_time_budget_seconds", 50))

                vsettings = VerificationSettings.from_dict(merged)
                deadline = time.monotonic() + time_budget

                while time.monotonic() < deadline:
                    status = list_queries.get_list_status(cur, list_id)
                    if status in ("paused", "cancelled", "completed", "failed", "interrupted"):
                        return

                    rows = list_queries.claim_rows(cur, list_id, concurrency)
                    if not rows:
                        if list_queries.finalize_list_if_done(cur, list_id):
                            logger.info("List %s completed", list_id)
                        return

                    conn.commit()

                    results = _verify_batch_with_concurrency(rows, vsettings, concurrency)

                    with conn.cursor() as write_cur:
                        list_queries.write_row_results(write_cur, list_id, results)
                        list_queries.touch_list(write_cur, list_id)
                    conn.commit()

                    logger.debug(
                        "List %s: processed chunk of %d rows",
                        list_id,
                        len(results),
                    )

    except Exception:
        logger.exception("process_chunk failed")
