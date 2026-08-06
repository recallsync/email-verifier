import csv
import io
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from db.connection import check_connection
from db.settings import get_all_settings
from routes.api import api
from utils.email_utils import check_email
from utils.email_permutations import generate_email_permutations
from utils.verification_settings import VerificationSettings

app = Flask(__name__)
CORS(app)
app.register_blueprint(api)

# Legacy in-memory job store (deprecated — use /api/lists)
data = {}

COMPANY_ROLE_PREFIXES = ("info", "contact", "sales", "support", "hello")


def _verification_settings() -> VerificationSettings:
    return VerificationSettings.from_dict(get_all_settings())


@app.route("/verify-email", methods=["POST"])
def verify_email():
    """Verify a single email address"""
    try:
        json_data = request.get_json()
        if not json_data or "email" not in json_data:
            return jsonify({"error": "Missing 'email' field in request body"}), 400

        email = json_data["email"].strip()

        if not email:
            return jsonify({
                "email": email,
                "status": "invalid",
                "reason": "empty_email",
                "message": "Email address is empty",
            }), 200

        status, reason = check_email(email, settings=_verification_settings())

        return jsonify({
            "email": email,
            "status": status,
            "reason": reason,
            "message": f"Email verification completed: {status}",
        }), 200

    except Exception as e:
        return jsonify({
            "error": "An error occurred during verification",
            "details": str(e),
        }), 500


@app.route("/find-email", methods=["POST"])
def find_email():
    """Find a valid email address for a person by testing permutations in parallel"""
    try:
        json_data = request.get_json()

        if not json_data or "name" not in json_data or "website" not in json_data:
            return jsonify({
                "error": "Missing required fields. Please provide 'name' and 'website' in request body",
            }), 400

        name = json_data["name"].strip()
        website = json_data["website"].strip()

        if not name or not website:
            return jsonify({"error": "Both 'name' and 'website' must be non-empty"}), 400

        permutations = generate_email_permutations(name, website)

        if not permutations:
            return jsonify({
                "error": "Could not generate email permutations",
                "name": name,
                "website": website,
            }), 400

        settings = _verification_settings()
        max_workers = min(10, len(permutations))
        results = []
        valid_email_found = None
        best_risky = None

        def verify_single_email(email):
            status, reason = check_email(email, settings=settings)
            return {"email": email, "status": status, "reason": reason}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_email = {
                executor.submit(verify_single_email, email): email for email in permutations
            }

            for future in as_completed(future_to_email):
                result = future.result()
                results.append(result)

                if result["status"] == "valid" and not valid_email_found:
                    valid_email_found = result["email"]
                elif result["status"] == "risky" and not best_risky:
                    best_risky = result["email"]

        email_to_result = {r["email"]: r for r in results}
        results = [email_to_result[email] for email in permutations]

        domain = website.replace("https://", "").replace("http://", "").split("/")[0]
        if domain.startswith("www."):
            domain = domain[4:]

        response = {
            "name": name,
            "website": website,
            "domain": domain,
            "total_permutations": len(permutations),
            "permutations_tested": results,
            "valid_email": valid_email_found,
            "found": valid_email_found is not None,
        }
        if not valid_email_found and best_risky:
            response["best_guess"] = best_risky

        return jsonify(response), 200

    except Exception as e:
        return jsonify({
            "error": "An error occurred during email finding",
            "details": str(e),
        }), 500


@app.route("/find-email/company", methods=["POST"])
def find_email_company():
    """Find best role-based contact email for a company domain."""
    try:
        json_data = request.get_json() or {}
        domain = (json_data.get("domain") or "").strip()
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
        if domain.startswith("www."):
            domain = domain[4:]

        if not domain:
            return jsonify({"error": "Missing required field: domain"}), 400

        settings = _verification_settings()
        emails = [f"{prefix}@{domain}" for prefix in COMPANY_ROLE_PREFIXES]
        results = []
        best_email = None
        best_risky = None

        def verify_single(email):
            status, reason = check_email(email, settings=settings)
            return {"email": email, "status": status, "reason": reason}

        with ThreadPoolExecutor(max_workers=len(emails)) as executor:
            futures = [executor.submit(verify_single, email) for email in emails]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if result["status"] == "valid" and not best_email:
                    best_email = result["email"]
                elif result["status"] == "risky" and not best_risky:
                    best_risky = result["email"]

        order = {email: i for i, email in enumerate(emails)}
        results.sort(key=lambda r: order.get(r["email"], 999))

        return jsonify({
            "domain": domain,
            "found": best_email is not None,
            "best_email": best_email or best_risky,
            "emails_tested": results,
        }), 200

    except Exception as e:
        return jsonify({
            "error": "An error occurred during company email finding",
            "details": str(e),
        }), 500


# --- Deprecated legacy CSV endpoints ---

@app.route("/verify", methods=["POST"])
def verify():
    job_id = str(uuid.uuid4())
    file = request.files["file"]
    content = file.read().decode("utf-8")
    reader = list(csv.DictReader(io.StringIO(content)))
    total = len(reader)
    email_field = next((f for f in reader[0].keys() if f.lower().strip() == "email"), None)

    output = io.StringIO()
    fieldnames = list(reader[0].keys()) + ["status", "reason"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    settings = _verification_settings()

    data[job_id] = {
        "progress": 0,
        "row": 0,
        "total": total,
        "log": "",
        "cancel": False,
        "output": output,
        "writer": writer,
        "records": reader,
        "email_field": email_field,
        "filename": file.filename,
    }

    def run():
        for i, row in enumerate(reader, start=1):
            if data[job_id]["cancel"]:
                data[job_id]["log"] = f"Canceled job {job_id}"
                break
            email = (row.get(email_field) or "").strip()
            if not email:
                status, reason = "invalid", "empty_email"
            else:
                status, reason = check_email(email, settings=settings)
            row["status"], row["reason"] = status, reason
            writer.writerow(row)
            percent = int((i / total) * 100)
            data[job_id].update({
                "progress": percent,
                "row": i,
                "log": f"{email} -> {status} ({reason})",
            })

    import threading
    threading.Thread(target=run, daemon=True).start()

    return jsonify({"job_id": job_id})


@app.route("/progress")
def progress():
    job_id = request.args.get("job_id")
    d = data.get(job_id, {})
    return jsonify({
        "percent": d.get("progress", 0),
        "row": d.get("row", 0),
        "total": d.get("total", 0),
    })


@app.route("/log")
def log():
    job_id = request.args.get("job_id")
    return Response(data.get(job_id, {}).get("log", ""), mimetype="text/plain")


@app.route("/cancel", methods=["POST"])
def cancel():
    job_id = request.args.get("job_id")
    if job_id in data:
        data[job_id]["cancel"] = True
    return "", 204


@app.route("/download")
def download():
    job_id = request.args.get("job_id")
    filter_type = request.args.get("type", "all")
    job = data.get(job_id)
    if not job:
        return "Invalid job ID", 404

    job["output"].seek(0)
    reader = list(csv.DictReader(job["output"]))

    if filter_type == "valid":
        filtered = [row for row in reader if row["status"] == "valid"]
    elif filter_type == "risky":
        filtered = [row for row in reader if row["status"] == "risky"]
    elif filter_type == "risky_invalid":
        filtered = [row for row in reader if row["status"] in ("risky", "invalid")]
    else:
        filtered = reader

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=reader[0].keys())
    writer.writeheader()
    for row in filtered:
        writer.writerow(row)

    output.seek(0)
    download_name = f"{filter_type}-{job['filename']}"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={download_name}"},
    )


@app.route("/health")
def health():
    db_ok = check_connection()
    status = "healthy" if db_ok else "degraded"
    code = 200 if db_ok else 503
    return jsonify({
        "status": status,
        "service": "email-verifier",
        "database": "connected" if db_ok else "disconnected",
    }), code


if __name__ == "__main__":
    app.run(debug=True, port=5050)
