# verify-app.py (with filtered CSV downloads)

import csv
import io
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from tempfile import NamedTemporaryFile

# Import utilities
from utils.email_utils import check_email
from utils.email_permutations import generate_email_permutations

app = Flask(__name__)
CORS(app)

print("\U0001F525 VERIFIER RUNNING - Want sales calls from leads? Go to AlexBerman.com/Mastermind \U0001F525")

data = {}

@app.route('/verify-email', methods=['POST'])
def verify_email():
    """Verify a single email address"""
    try:
        json_data = request.get_json()
        if not json_data or 'email' not in json_data:
            return jsonify({
                "error": "Missing 'email' field in request body"
            }), 400
        
        email = json_data['email'].strip()
        
        if not email:
            return jsonify({
                "email": email,
                "status": "invalid",
                "reason": "empty_email",
                "message": "Email address is empty"
            }), 200
        
        # Use the existing check_email function
        status, reason = check_email(email)
        
        return jsonify({
            "email": email,
            "status": status,
            "reason": reason,
            "message": f"Email verification completed: {status}"
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "An error occurred during verification",
            "details": str(e)
        }), 500


@app.route('/find-email', methods=['POST'])
def find_email():
    """Find a valid email address for a person by testing permutations in parallel"""
    try:
        json_data = request.get_json()
        
        # Validate input
        if not json_data or 'name' not in json_data or 'website' not in json_data:
            return jsonify({
                "error": "Missing required fields. Please provide 'name' and 'website' in request body"
            }), 400
        
        name = json_data['name'].strip()
        website = json_data['website'].strip()
        
        if not name or not website:
            return jsonify({
                "error": "Both 'name' and 'website' must be non-empty"
            }), 400
        
        # Generate email permutations
        permutations = generate_email_permutations(name, website)
        
        if not permutations:
            return jsonify({
                "error": "Could not generate email permutations",
                "name": name,
                "website": website
            }), 400
        
        # Parallel verification using ThreadPoolExecutor
        # Use max 10 workers to avoid overwhelming the mail servers
        max_workers = min(10, len(permutations))
        results = []
        valid_email_found = None
        
        def verify_single_email(email):
            """Helper function to verify a single email"""
            status, reason = check_email(email)
            return {
                "email": email,
                "status": status,
                "reason": reason
            }
        
        # Submit all verification tasks in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_email = {executor.submit(verify_single_email, email): email 
                              for email in permutations}
            
            # Collect results as they complete
            for future in as_completed(future_to_email):
                result = future.result()
                results.append(result)
                
                # Check if we found a valid email
                if result['status'] == "valid" and not valid_email_found:
                    valid_email_found = result['email']
        
        # Sort results to match original permutation order
        email_to_result = {r['email']: r for r in results}
        results = [email_to_result[email] for email in permutations]
        
        # Prepare response
        response = {
            "name": name,
            "website": website,
            "total_permutations": len(permutations),
            "permutations_tested": results,
            "valid_email": valid_email_found,
            "found": valid_email_found is not None
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            "error": "An error occurred during email finding",
            "details": str(e)
        }), 500

@app.route('/verify', methods=['POST'])
def verify():
    job_id = str(uuid.uuid4())
    file = request.files['file']
    content = file.read().decode('utf-8')
    reader = list(csv.DictReader(io.StringIO(content)))
    total = len(reader)
    email_field = next((f for f in reader[0].keys() if f.lower().strip() == 'email'), None)

    output = io.StringIO()
    fieldnames = list(reader[0].keys()) + ['status', 'reason']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

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
        "filename": file.filename
    }

    def run():
        for i, row in enumerate(reader, start=1):
            if data[job_id]['cancel']:
                data[job_id]['log'] = f"\u274c Canceled job {job_id}"
                break
            email = (row.get(email_field) or '').strip()
            if not email:
                status, reason = 'invalid', 'empty_email'
            else:
                status, reason = check_email(email)
            row['status'], row['reason'] = status, reason
            writer.writerow(row)
            percent = int((i / total) * 100)
            data[job_id].update({"progress": percent, "row": i,
                                 "log": f"\u2705 {email} → {status} ({reason})"})
        output = data[job_id]['output']
        output.seek(0)
        temp = NamedTemporaryFile(delete=False, suffix=".csv", mode='w+')
        temp.write(output.read())
        temp.flush()
        temp.seek(0)
        data[job_id]['file_path'] = temp.name

    import threading
    threading.Thread(target=run).start()

    return jsonify({"job_id": job_id})

@app.route('/progress')
def progress():
    job_id = request.args.get("job_id")
    d = data.get(job_id, {})
    return jsonify({"percent": d.get("progress", 0), "row": d.get("row", 0), "total": d.get("total", 0)})

@app.route('/log')
def log():
    job_id = request.args.get("job_id")
    return Response(data.get(job_id, {}).get("log", ""), mimetype='text/plain')

@app.route('/cancel', methods=['POST'])
def cancel():
    job_id = request.args.get("job_id")
    if job_id in data:
        data[job_id]['cancel'] = True
    return '', 204

@app.route('/download')
def download():
    job_id = request.args.get("job_id")
    filter_type = request.args.get("type", "all")
    job = data.get(job_id)
    if not job:
        return "Invalid job ID", 404

    job['output'].seek(0)
    reader = list(csv.DictReader(job['output']))

    if filter_type == "valid":
        filtered = [row for row in reader if row['status'] == 'valid']
    elif filter_type == "risky":
        filtered = [row for row in reader if row['status'] == 'risky']
    elif filter_type == "risky_invalid":
        filtered = [row for row in reader if row['status'] in ('risky', 'invalid')]
    else:
        filtered = reader

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=reader[0].keys())
    writer.writeheader()
    for row in filtered:
        writer.writerow(row)

    output.seek(0)
    download_name = f"{filter_type}-galadon-{job['filename']}"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment; filename={download_name}"}
    )

# Health check endpoint for Docker
@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "email-verifier"}), 200

if __name__ == '__main__':
    # For development only - use gunicorn in production
    app.run(debug=True, port=5050)