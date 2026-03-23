#!/usr/bin/env python3
"""
Fire parallel POST /verify-email requests to test MX behavior under concurrency.

Usage:
  python scripts/parallel_verify_email.py --url http://127.0.0.1:5050/verify-email --workers 10 --requests 20

  python scripts/parallel_verify_email.py --base https://api.example.com --workers 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Parallel POST /verify-email load probe")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--url",
        help="Full URL to POST (e.g. http://localhost:5050/verify-email)",
    )
    g.add_argument(
        "--base",
        help="Origin only; path /verify-email is appended",
    )
    p.add_argument(
        "--email",
        default="info@fusionsync.ai",
        help="Email in JSON body (default: %(default)s)",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Max parallel requests (default: %(default)s)",
    )
    p.add_argument(
        "--requests",
        type=int,
        default=None,
        help="Total requests (default: same as --workers)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP timeout per request in seconds (default: %(default)s)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.url:
        url = args.url.rstrip("/")
    else:
        url = args.base.rstrip("/") + "/verify-email"

    total = args.requests if args.requests is not None else args.workers
    body = {"email": args.email}

    print(f"URL:     {url}")
    print(f"Body:    {json.dumps(body)}")
    print(f"Parallel: {args.workers} workers, {total} total requests")
    print("-" * 60)

    session = requests.Session()
    headers = {"Content-Type": "application/json"}

    def one(i: int) -> tuple[int, float, str]:
        t0 = time.perf_counter()
        try:
            r = session.post(
                url,
                json=body,
                headers=headers,
                timeout=args.timeout,
            )
            dt = time.perf_counter() - t0
            snippet = r.text[:200].replace("\n", " ")
            return r.status_code, dt, f"#{i} HTTP {r.status_code} in {dt:.2f}s | {snippet}"
        except requests.RequestException as e:
            dt = time.perf_counter() - t0
            return -1, dt, f"#{i} ERROR in {dt:.2f}s | {type(e).__name__}: {e}"

    errors = 0
    slow = 0
    t_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(one, i): i for i in range(total)}
        for fut in as_completed(futures):
            code, dt, line = fut.result()
            print(line)
            if code != 200:
                errors += 1
            if dt > 20.0:
                slow += 1

    wall = time.perf_counter() - t_start
    print("-" * 60)
    print(f"Done: {total} requests in {wall:.2f}s wall time")
    print(f"Non-200 or errors: {errors}")
    print(f"Requests > 20s: {slow}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
