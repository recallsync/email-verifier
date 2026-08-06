"""Stream CSV upload into list_rows."""

import csv
import io
import json
import os
from uuid import UUID

from config import UPLOADS_DIR
from db.connection import get_connection
from db import repository as repo
from db.settings import get_all_settings
from utils.csv_helpers import detect_email_column, estimate_duration


BATCH_SIZE = 500


class UploadError(Exception):
    def __init__(self, code: str, message: str, columns: list[str] | None = None):
        self.code = code
        self.message = message
        self.columns = columns or []
        super().__init__(message)


def process_csv_upload(
    list_id: UUID,
    file_storage,
    email_column_override: str | None = None,
) -> dict:
    settings = get_all_settings()
    max_bytes = int(settings.get("max_upload_size_mb", 50)) * 1024 * 1024

    raw = file_storage.read()
    if len(raw) > max_bytes:
        raise UploadError("file_too_large", f"CSV exceeds {settings['max_upload_size_mb']}MB limit")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadError("invalid_encoding", "CSV must be UTF-8 encoded") from exc

    if not text.strip():
        raise UploadError("empty_csv", "CSV file is empty")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise UploadError("empty_csv", "CSV has no header row")

    columns = list(reader.fieldnames)
    email_column, error_code, candidates = detect_email_column(columns, email_column_override)
    if error_code:
        messages = {
            "ambiguous_email_column": "Multiple email-like columns found. Specify email_column.",
            "no_email_column": "No email column found. Specify email_column.",
            "invalid_email_column": "Specified email_column not found in CSV headers.",
        }
        raise UploadError(error_code, messages.get(error_code, error_code), candidates)

    upload_dir = os.path.join(UPLOADS_DIR, str(list_id))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, "original.csv")
    with open(file_path, "wb") as f:
        f.write(raw)

    batch: list[tuple[int, dict, str]] = []
    row_index = 0
    filename = file_storage.filename or "upload.csv"

    with get_connection() as conn:
        with conn.cursor() as cur:
            existing = repo.get_list(cur, list_id)
            if not existing:
                raise UploadError("not_found", "List not found")
            if existing["status"] != "draft":
                raise UploadError("invalid_status", "CSV can only be uploaded to draft lists")

            repo.clear_list_rows(cur, list_id)

            for row in reader:
                email = (row.get(email_column) or "").strip()
                batch.append((row_index, dict(row), email))
                row_index += 1

                if len(batch) >= BATCH_SIZE:
                    repo.insert_list_rows_batch(cur, list_id, batch)
                    batch = []

            if batch:
                repo.insert_list_rows_batch(cur, list_id, batch)

            if row_index == 0:
                raise UploadError("empty_csv", "CSV contains no data rows")

            repo.update_list_after_upload(
                cur, list_id, filename, email_column, row_index, file_path
            )

    concurrency = int(settings.get("concurrency", 10))
    return {
        "list_id": str(list_id),
        "filename": filename,
        "total_rows": row_index,
        "email_column": email_column,
        "estimated_duration": estimate_duration(row_index, concurrency),
        "columns": columns,
    }
