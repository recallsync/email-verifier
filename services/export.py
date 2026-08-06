"""CSV and XLSX export for list results."""

import csv
import io
from uuid import UUID

from openpyxl import Workbook

from db.connection import get_connection
from db import repository as repo
from utils.status import ROW_TO_EXPORT


def _status_label(status: str) -> str:
    return ROW_TO_EXPORT.get(status, status.title())


def _safe_name(list_name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in list_name)


def export_filename(list_name: str, filter_type: str, file_format: str = "csv") -> str:
    suffix = "risky-failed" if filter_type == "risky_failed" else "verified"
    ext = "xlsx" if file_format == "xlsx" else "csv"
    return f"{_safe_name(list_name)}-{suffix}.{ext}"


def _iter_export_rows(list_id: UUID, filter_type: str):
    """Collect export rows and fieldnames from the database."""
    fieldnames: list[str] | None = None
    rows_out: list[list[str]] = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            for db_row in repo.iter_export_rows(cur, list_id, filter_type):
                if fieldnames is None:
                    fieldnames = list(db_row["raw_row"].keys()) + ["V Status", "V Reason"]

                row_data = dict(db_row["raw_row"])
                row_data["V Status"] = _status_label(db_row["status"])
                row_data["V Reason"] = db_row["reason"] or ""
                rows_out.append([row_data.get(col, "") for col in fieldnames])

    if fieldnames is None:
        fieldnames = ["V Status", "V Reason"]

    return fieldnames, rows_out


def generate_csv(list_id: UUID, filter_type: str = "all"):
    """Yield CSV content chunks for a list export."""
    fieldnames, rows = _iter_export_rows(list_id, filter_type)

    header = io.StringIO()
    writer = csv.writer(header)
    writer.writerow(fieldnames)
    yield header.getvalue()

    for row in rows:
        buf = io.StringIO()
        line_writer = csv.writer(buf)
        line_writer.writerow(row)
        yield buf.getvalue()


def build_xlsx(list_id: UUID, filter_type: str = "all") -> bytes:
    """Build full XLSX workbook in memory."""
    fieldnames, rows = _iter_export_rows(list_id, filter_type)

    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Results")
    ws.append(fieldnames)
    for row in rows:
        ws.append(row)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
