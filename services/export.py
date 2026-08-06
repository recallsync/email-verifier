"""CSV export generator for list results."""

import csv
import io
from uuid import UUID

from db.connection import get_connection
from db import repository as repo
from utils.status import ROW_TO_EXPORT


def _status_label(status: str) -> str:
    return ROW_TO_EXPORT.get(status, status.title())


def export_filename(list_name: str, filter_type: str) -> str:
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in list_name)
    suffix = "risky-failed" if filter_type == "risky_failed" else "verified"
    return f"{safe_name}-{suffix}.csv"


def generate_csv(list_id: UUID, filter_type: str = "all"):
    """Yield CSV content chunks for a list export."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            fieldnames: list[str] | None = None
            writer: csv.DictWriter | None = None

            for db_row in repo.iter_export_rows(cur, list_id, filter_type):
                if fieldnames is None:
                    fieldnames = list(db_row["raw_row"].keys()) + ["V Status", "V Reason"]
                    header = io.StringIO()
                    writer = csv.DictWriter(header, fieldnames=fieldnames, extrasaction="ignore")
                    writer.writeheader()
                    yield header.getvalue()

                row_data = dict(db_row["raw_row"])
                row_data["V Status"] = _status_label(db_row["status"])
                row_data["V Reason"] = db_row["reason"] or ""

                buf = io.StringIO()
                line_writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
                line_writer.writerow(row_data)
                yield buf.getvalue()

            if fieldnames is None:
                fieldnames = ["V Status", "V Reason"]
                header = io.StringIO()
                writer = csv.DictWriter(header, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                yield header.getvalue()
