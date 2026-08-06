#!/usr/bin/env python3
"""
Dev helper: create a test list with sample rows and queue it for processing.

Usage:
  python scripts/seed_test_list.py
  python scripts/seed_test_list.py --emails test@example.com invalid@
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_connection
from db.settings import get_settings_snapshot


def seed_list(name: str, emails: list[str]) -> str:
    snapshot = get_settings_snapshot()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO lists (name, filename, status, email_column, total_rows, settings_snapshot)
                VALUES (%s, %s, 'queued', 'email', %s, %s::jsonb)
                RETURNING id
                """,
                (name, "seed.csv", len(emails), json.dumps(snapshot)),
            )
            list_id = cur.fetchone()["id"]

            for idx, email in enumerate(emails):
                raw = {"email": email, "name": f"Contact {idx + 1}"}
                cur.execute(
                    """
                    INSERT INTO list_rows (list_id, row_index, raw_row, email, status)
                    VALUES (%s, %s, %s::jsonb, %s, 'pending')
                    """,
                    (list_id, idx, json.dumps(raw), email),
                )

    return str(list_id)


def main():
    parser = argparse.ArgumentParser(description="Seed a test list for chunk processor")
    parser.add_argument("--name", default="Seed Test List")
    parser.add_argument(
        "--emails",
        nargs="*",
        default=["test@gmail.com", "not-an-email", "noreply@google.com"],
    )
    args = parser.parse_args()

    list_id = seed_list(args.name, args.emails)
    print(f"Created queued list: {list_id}")
    print(f"Rows: {len(args.emails)}")
    print("Processor will pick it up on the next tick.")


if __name__ == "__main__":
    main()
