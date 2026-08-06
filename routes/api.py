"""Flask API routes for lists, settings, and stats."""

import json
import time
from uuid import UUID

from flask import Blueprint, Response, jsonify, request, stream_with_context

from db.connection import get_connection
from db import repository as repo
from db.settings import get_all_settings, get_settings_snapshot, update_settings
from db.stats import get_stats
from services.csv_upload import UploadError, process_csv_upload
from services.export import export_filename, generate_csv
from utils.serializers import serialize_list

api = Blueprint("api", __name__, url_prefix="/api")


def _parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except (ValueError, TypeError):
        return None


def _error(code: str, message: str, status: int):
    return jsonify({"error": code, "message": message}), status


@api.route("/settings", methods=["GET"])
def get_settings():
    return jsonify(get_all_settings())


@api.route("/settings", methods=["PUT"])
def put_settings():
    body = request.get_json(silent=True) or {}
    if not body:
        return _error("invalid_body", "Request body must be JSON object", 400)
    try:
        return jsonify(update_settings(body))
    except ValueError as exc:
        return _error("validation_error", str(exc), 400)


@api.route("/stats", methods=["GET"])
def api_stats():
    return jsonify(get_stats())


@api.route("/lists", methods=["GET"])
def get_lists():
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)

    with get_connection() as conn:
        with conn.cursor() as cur:
            rows, total = repo.list_lists(cur, status=status, limit=limit, offset=offset)

    return jsonify({
        "lists": [serialize_list(r) for r in rows],
        "total": total,
    })


@api.route("/lists", methods=["POST"])
def create_list():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return _error("invalid_body", "List name is required", 400)

    with get_connection() as conn:
        with conn.cursor() as cur:
            row = repo.create_list(cur, name)

    result = serialize_list(row)
    return jsonify(result), 201


@api.route("/lists/<list_id>", methods=["GET"])
def get_list_detail(list_id):
    uid = _parse_uuid(list_id)
    if not uid:
        return _error("invalid_id", "Invalid list ID", 400)

    with get_connection() as conn:
        with conn.cursor() as cur:
            row = repo.get_list(cur, uid)

    if not row:
        return _error("not_found", "List not found", 404)
    return jsonify(serialize_list(row))


@api.route("/lists/<list_id>", methods=["DELETE"])
def delete_list(list_id):
    uid = _parse_uuid(list_id)
    if not uid:
        return _error("invalid_id", "Invalid list ID", 400)

    with get_connection() as conn:
        with conn.cursor() as cur:
            existing = repo.get_list(cur, uid)
            if not existing:
                return _error("not_found", "List not found", 404)
            if existing["status"] == "processing":
                return _error("conflict", "Cannot delete a list while it is processing", 409)
            deleted = repo.delete_list(cur, uid)

    if not deleted:
        return _error("conflict", "Cannot delete this list", 409)
    return "", 204


@api.route("/lists/<list_id>/upload", methods=["POST"])
def upload_csv(list_id):
    uid = _parse_uuid(list_id)
    if not uid:
        return _error("invalid_id", "Invalid list ID", 400)

    if "file" not in request.files:
        return _error("missing_file", "CSV file is required", 400)

    file_storage = request.files["file"]
    email_column = request.form.get("email_column") or None

    try:
        result = process_csv_upload(uid, file_storage, email_column)
        return jsonify(result)
    except UploadError as exc:
        status = 413 if exc.code == "file_too_large" else 422
        if exc.code == "not_found":
            status = 404
        if exc.code == "invalid_status":
            status = 409
        payload = {"error": exc.code, "message": exc.message}
        if exc.columns:
            payload["columns"] = exc.columns
        return jsonify(payload), status


@api.route("/lists/<list_id>/verify", methods=["POST"])
def verify_list(list_id):
    uid = _parse_uuid(list_id)
    if not uid:
        return _error("invalid_id", "Invalid list ID", 400)

    with get_connection() as conn:
        with conn.cursor() as cur:
            snapshot = get_settings_snapshot(conn)
            row = repo.queue_list(cur, uid, snapshot)
            if not row:
                existing = repo.get_list(cur, uid)
                if not existing:
                    return _error("not_found", "List not found", 404)
                return _error(
                    "conflict",
                    "List must be in draft status with uploaded rows before verifying",
                    409,
                )
            position = repo.get_queue_position(cur, uid)

    return jsonify({
        "id": str(row["id"]),
        "status": row["status"],
        "queue_position": position,
    })


@api.route("/lists/<list_id>/pause", methods=["POST"])
def pause_list(list_id):
    uid = _parse_uuid(list_id)
    if not uid:
        return _error("invalid_id", "Invalid list ID", 400)

    with get_connection() as conn:
        with conn.cursor() as cur:
            row = repo.pause_list(cur, uid)

    if not row:
        return _error("conflict", "List is not processing", 409)
    return jsonify({"status": row["status"]})


@api.route("/lists/<list_id>/resume", methods=["POST"])
def resume_list_route(list_id):
    uid = _parse_uuid(list_id)
    if not uid:
        return _error("invalid_id", "Invalid list ID", 400)

    with get_connection() as conn:
        with conn.cursor() as cur:
            row = repo.resume_list(cur, uid)

    if not row:
        return _error("conflict", "List is not paused", 409)
    return jsonify({"status": row["status"]})


@api.route("/lists/<list_id>/cancel", methods=["POST"])
def cancel_list_route(list_id):
    uid = _parse_uuid(list_id)
    if not uid:
        return _error("invalid_id", "Invalid list ID", 400)

    with get_connection() as conn:
        with conn.cursor() as cur:
            row = repo.cancel_list(cur, uid)

    if not row:
        return _error("conflict", "List cannot be cancelled in its current status", 409)
    return jsonify({"status": row["status"]})


@api.route("/lists/<list_id>/rows", methods=["GET"])
def list_rows(list_id):
    uid = _parse_uuid(list_id)
    if not uid:
        return _error("invalid_id", "Invalid list ID", 400)

    status = request.args.get("status")
    search = request.args.get("search")
    limit = min(int(request.args.get("limit", 100)), 500)
    offset = max(int(request.args.get("offset", 0)), 0)

    with get_connection() as conn:
        with conn.cursor() as cur:
            if not repo.get_list(cur, uid):
                return _error("not_found", "List not found", 404)
            rows, total = repo.get_list_rows(
                cur, uid, status=status, search=search, limit=limit, offset=offset
            )

    return jsonify({
        "rows": [serialize_list(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@api.route("/lists/<list_id>/export", methods=["GET"])
def export_list(list_id):
    uid = _parse_uuid(list_id)
    if not uid:
        return _error("invalid_id", "Invalid list ID", 400)

    filter_type = request.args.get("filter", "all")
    if filter_type not in ("all", "risky_failed"):
        return _error("invalid_filter", "filter must be 'all' or 'risky_failed'", 400)

    with get_connection() as conn:
        with conn.cursor() as cur:
            lst = repo.get_list(cur, uid)

    if not lst:
        return _error("not_found", "List not found", 404)

    filename = export_filename(lst["name"], filter_type)
    return Response(
        stream_with_context(generate_csv(uid, filter_type)),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api.route("/lists/<list_id>/progress", methods=["GET"])
def list_progress(list_id):
    uid = _parse_uuid(list_id)
    if not uid:
        return _error("invalid_id", "Invalid list ID", 400)

    def event_stream():
        terminal = {"completed", "cancelled", "failed", "interrupted"}
        while True:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    progress = repo.get_progress(cur, uid)
                    if not progress:
                        yield f"event: error\ndata: {json.dumps({'error': 'not_found'})}\n\n"
                        break

                    payload = {
                        "processed": progress["processed"],
                        "total": progress["total"],
                        "verified": progress["verified"],
                        "risky": progress["risky"],
                        "failed": progress["failed"],
                        "status": progress["status"],
                    }
                    status = progress["status"]
                    event_name = "complete" if status in terminal else "progress"
                    yield f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"

                    if status in terminal:
                        break

            time.sleep(2)

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
