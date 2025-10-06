# Email Verifier & Finder API Documentation

## Base URL

```
http://localhost:5050
```

---

## 1. Single Email Verification

**Endpoint:** `POST /verify-email`

Verify a single email address to check if it's valid, risky, or invalid.

### Request Body

```json
{
  "email": "user@example.com"
}
```

### Response

```json
{
  "email": "user@example.com",
  "status": "valid",
  "reason": "smtp_ok",
  "message": "Email verification completed: valid"
}
```

### Status Values

- `valid` - Email is verified and deliverable
- `invalid` - Email is not valid or doesn't exist
- `risky` - Email might be valid but has issues

### Example Reasons

- `smtp_ok` - Email verified via SMTP
- `bad_syntax` - Invalid email format
- `no_mx` - No MX records found for domain
- `smtp_reject` - SMTP server rejected the email
- `disposable_domain` - Disposable email service
- `role_based` - Role-based email (info@, support@, etc.)
- `domain_accepts_all` - Domain accepts any email (catch-all)

### cURL Example

```bash
curl -X POST http://localhost:5050/verify-email \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

---

## 2. Email Finder

**Endpoint:** `POST /find-email`

Find a valid email address for a person by testing multiple permutations.

### Request Body

```json
{
  "name": "Shubham Kashyap",
  "website": "https://fusionsync.ai"
}
```

### Response

```json
{
  "name": "Shubham Kashyap",
  "website": "https://fusionsync.ai",
  "total_permutations": 18,
  "permutations_tested": [
    {
      "email": "shubham@fusionsync.ai",
      "status": "invalid",
      "reason": "smtp_reject"
    },
    {
      "email": "kashyap@fusionsync.ai",
      "status": "valid",
      "reason": "smtp_ok"
    },
    ...
  ],
  "valid_email": "kashyap@fusionsync.ai",
  "found": true
}
```

### Email Permutations Generated

For name "Shubham Kashyap" and domain "fusionsync.ai", the following 18 permutations are tested:

1. `shubham@fusionsync.ai`
2. `kashyap@fusionsync.ai`
3. `shubham.kashyap@fusionsync.ai`
4. `kashyap.shubham@fusionsync.ai`
5. `shubham_kashyap@fusionsync.ai`
6. `kashyap_shubham@fusionsync.ai`
7. `shubhamkashyap@fusionsync.ai`
8. `kashyapshubham@fusionsync.ai`
9. `s.kashyap@fusionsync.ai`
10. `shubham.k@fusionsync.ai`
11. `k.shubham@fusionsync.ai`
12. `kashyap.s@fusionsync.ai`
13. `sk@fusionsync.ai`
14. `ks@fusionsync.ai`
15. `skashyap@fusionsync.ai`
16. `kshubham@fusionsync.ai`
17. `shubham-kashyap@fusionsync.ai`
18. `kashyap-shubham@fusionsync.ai`

### cURL Example

```bash
curl -X POST http://localhost:5050/find-email \
  -H "Content-Type: application/json" \
  -d '{"name": "Shubham Kashyap", "website": "https://fusionsync.ai"}'
```

---

## 3. Bulk Email Verification (CSV)

**Endpoint:** `POST /verify`

Upload a CSV file with emails for bulk verification.

### Request

- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` field with CSV file

### Response

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### Check Progress

```
GET /progress?job_id=<job_id>
```

### Download Results

```
GET /download?job_id=<job_id>&type=all
```

Filter types: `all`, `valid`, `risky`, `risky_invalid`

---

## Project Structure

```
email-verifier/
├── app.py                          # Main Flask application
├── utils/
│   ├── __init__.py
│   ├── email_utils.py              # Email verification logic (DRY)
│   └── email_permutations.py      # Email permutation generator (DRY)
├── venv/                           # Virtual environment
└── API_EXAMPLES.md                 # This file
```

## Running the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run the server
python app.py
```

Server will start on `http://localhost:5050`
