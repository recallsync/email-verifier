# 🔥 Robust Email Verifier & Finder API

## Base URL

```
http://localhost:5050
```

---

## 🚀 Advanced Multi-Layered Verification System

This verifier implements industry best practices to **minimize false negatives** and handle challenging scenarios like:

### Key Improvements:

✅ **Greylisting Detection** - Automatically retries with progressive backoff (3s → 8s → 15s)  
✅ **Valid Sender Domains** - Uses legitimate domains (gmail.com) to avoid anti-spam rejections  
✅ **Smart SMTP 550 Handling** - Treats SMTP 550 as "risky" not "invalid" (many providers block verification)  
✅ **Role-Based Email Support** - info@, support@ are valid business emails, not auto-rejected  
✅ **Retry Logic** - Up to 3 attempts for temporary failures  
✅ **Connection Resilience** - Handles timeouts, disconnections, rate limiting

---

## 📊 Understanding Status Values

### ✅ `valid`

**Safe to use** - Email passed all verification checks

- SMTP server accepted the email (code 250)
- Domain has valid MX records
- Mailbox exists and can receive emails

### ⚠️ `risky`

**IMPORTANT:** Many legitimate emails return "risky" status!

This happens when:

- **SMTP Verification Blocked** - Providers like Namecheap, GoDaddy, GoHighLevel block verification attempts (even for valid emails)
- **Greylisting** - Server temporarily rejects unknown senders
- **Rate Limiting** - Too many verification requests
- **Connection Issues** - Timeouts or temporary failures

**✨ Recommendation:** Treat "risky" emails as **potentially valid**, especially for business domains like fusionsync.ai

### ❌ `invalid`

**Do not use** - Email has definite issues

- Syntax errors in email format
- Domain has no MX records (can't receive emails)
- Disposable/temporary email service
- Mailbox confirmed non-existent (SMTP 551, 552, 553)

---

## 1. Single Email Verification

**Endpoint:** `POST /verify-email`

### Request

```json
{
  "email": "info@fusionsync.ai"
}
```

### Response Examples

#### Example 1: Valid Email

```json
{
  "email": "user@gmail.com",
  "status": "valid",
  "reason": "smtp_ok",
  "message": "Email verification completed: valid"
}
```

#### Example 2: Risky But Likely Valid (Common with Namecheap/GoHighLevel)

```json
{
  "email": "info@fusionsync.ai",
  "status": "risky",
  "reason": "smtp_550_possible_valid",
  "message": "Email verification completed: risky"
}
```

#### Example 3: Invalid Email

```json
{
  "email": "fake@nonexistentdomain123.com",
  "status": "invalid",
  "reason": "no_mx",
  "message": "Email verification completed: invalid"
}
```

### Reason Codes Reference

#### ✅ Valid Reasons:

| Reason    | Meaning                              |
| --------- | ------------------------------------ |
| `smtp_ok` | Email verified successfully via SMTP |

#### ⚠️ Risky Reasons (May Still Be Valid):

| Reason                       | Meaning                                                                         | Action                          |
| ---------------------------- | ------------------------------------------------------------------------------- | ------------------------------- |
| `smtp_550_possible_valid`    | SMTP 550 rejection (common for valid emails on Namecheap, GoDaddy, GoHighLevel) | ✅ Likely valid, consider using |
| `greylist_code_450`          | Greylisting detected after retries                                              | ✅ Might be valid, retry later  |
| `greylist_code_451`          | Temporary rejection (greylisting)                                               | ✅ Might be valid, retry later  |
| `smtp_timeout`               | Server didn't respond in time                                                   | ⚠️ Try again later              |
| `smtp_connection_failed`     | Couldn't connect to mail server                                                 | ⚠️ Temporary issue              |
| `rate_limited_or_temp_error` | Too many requests or server busy                                                | ⚠️ Retry with delay             |
| `smtp_inconclusive`          | Verification was inconclusive                                                   | ⚠️ Unable to confirm            |

#### ❌ Invalid Reasons:

| Reason                     | Meaning                            |
| -------------------------- | ---------------------------------- |
| `bad_syntax`               | Email format is incorrect          |
| `no_mx`                    | Domain has no mail servers         |
| `disposable_domain`        | Temporary/disposable email service |
| `smtp_551` / `552` / `553` | Mailbox definitely doesn't exist   |

### cURL Example

```bash
curl -X POST http://localhost:5050/verify-email \
  -H "Content-Type: application/json" \
  -d '{"email": "info@fusionsync.ai"}'
```

---

## 2. Email Finder ⚡

**Endpoint:** `POST /find-email`

Find valid email addresses by testing common permutations **in parallel** (up to 10 concurrent checks).

### Request

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
  "valid_email": "shubham@fusionsync.ai",
  "found": true,
  "permutations_tested": [
    {
      "email": "shubham@fusionsync.ai",
      "status": "valid",
      "reason": "smtp_ok"
    },
    {
      "email": "kashyap@fusionsync.ai",
      "status": "risky",
      "reason": "smtp_550_possible_valid"
    },
    ...
  ]
}
```

### 18 Email Permutations Generated

For "Shubham Kashyap" @ fusionsync.ai:

1. `shubham@fusionsync.ai` ← First name
2. `kashyap@fusionsync.ai` ← Last name
3. `shubham.kashyap@fusionsync.ai` ← first.last
4. `kashyap.shubham@fusionsync.ai` ← last.first
5. `shubham_kashyap@fusionsync.ai` ← first_last
6. `kashyap_shubham@fusionsync.ai` ← last_first
7. `shubhamkashyap@fusionsync.ai` ← firstlast
8. `kashyapshubham@fusionsync.ai` ← lastfirst
9. `s.kashyap@fusionsync.ai` ← f.last
10. `shubham.k@fusionsync.ai` ← first.l
11. `k.shubham@fusionsync.ai` ← l.first
12. `kashyap.s@fusionsync.ai` ← last.f
13. `sk@fusionsync.ai` ← fl
14. `ks@fusionsync.ai` ← lf
15. `skashyap@fusionsync.ai` ← flast
16. `kshubham@fusionsync.ai` ← lfirst
17. `shubham-kashyap@fusionsync.ai` ← first-last
18. `kashyap-shubham@fusionsync.ai` ← last-first

### cURL Example

```bash
curl -X POST http://localhost:5050/find-email \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Shubham Kashyap",
    "website": "https://fusionsync.ai"
  }'
```

---

## 3. Bulk Email Verification (CSV)

**Endpoint:** `POST /verify`

Upload CSV file for bulk verification.

### Request

- **Method:** POST
- **Content-Type:** multipart/form-data
- **File field:** `file`

### Response

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### Monitor Progress

```bash
curl "http://localhost:5050/progress?job_id=<job_id>"
```

### Download Results

```bash
curl "http://localhost:5050/download?job_id=<job_id>&type=all" -o results.csv
```

**Filter Types:**

- `all` - All emails
- `valid` - Only valid emails
- `risky` - Only risky emails
- `risky_invalid` - Risky + Invalid emails

---

## 🎯 Common Use Cases

### Case 1: Email from GoHighLevel/Namecheap

```bash
# Your emails: shubham@fusionsync.ai, info@fusionsync.ai
# Expected result: "risky" with reason "smtp_550_possible_valid"
# Action: ✅ These are valid emails, the server blocks verification
```

### Case 2: Finding Employee Email

```bash
# POST /find-email
# Input: "John Doe" @ "company.com"
# Result: Tests 18 permutations and returns first valid one
```

### Case 3: Bulk List Cleaning

```bash
# POST /verify (upload CSV)
# Download filtered results with type=valid
# Get only verified emails
```

---

## 📁 Project Structure

```
email-verifier/
├── app.py                    # Main Flask application
├── utils/
│   ├── email_utils.py        # Robust verification logic (DRY)
│   └── email_permutations.py # Email permutation generator (DRY)
├── API_DOCS.md              # This documentation
└── venv/                     # Virtual environment
```

---

## 🚀 Running the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if needed)
pip install flask flask-cors dnspython

# Run server
python app.py
```

Server starts at: `http://localhost:5050`

---

## ⚡ Performance Notes

- **Single verification:** 2-20 seconds (depends on SMTP retry logic)
- **Email finder:** 5-30 seconds (tests up to 18 permutations **in parallel** with 10 workers) 🚀
- **Bulk verification:** Varies by list size

**NEW:** Email finder now uses parallel processing (ThreadPoolExecutor), making it **5-10x faster** than sequential verification!

**Tip:** For even faster results without SMTP checks, consider implementing DNS-only mode (syntax + MX record validation).
