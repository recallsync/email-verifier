# 🔥 Robust Email Verifier & Finder

A production-ready email verification and finding tool with multi-layered validation, greylisting detection, and intelligent SMTP handling.

## 🚀 Features

✅ **Single Email Verification** - Verify individual emails with high accuracy  
✅ **Email Finder** - Find employee emails using 18 permutation patterns (parallel processing) ⚡  
✅ **Bulk CSV Verification** - Process thousands of emails with progress tracking  
✅ **Greylisting Detection** - Auto-retry with progressive backoff (3s → 8s → 15s)  
✅ **Smart SMTP Handling** - Handles providers that block verification (Namecheap, GoDaddy, GoHighLevel)  
✅ **Low False Negatives** - Risky status for inconclusive results (not invalid)

## 🎯 Problem Solved

**Issue:** Valid emails were marked as invalid because providers like Namecheap, GoDaddy, and GoHighLevel block SMTP verification attempts (anti-spam measure).

**Solution:** Multi-layered verification with intelligent retry logic and three-tier status system:

- ✅ `valid` - Confirmed deliverable
- ⚠️ `risky` - Inconclusive (might be valid, especially for business domains)
- ❌ `invalid` - Definite issues only

## 📦 Installation

```bash
# Clone/navigate to project
cd email-verifier

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## 🏃 Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Run server
python app.py
```

Server starts at: `http://localhost:5050`

## 📡 API Endpoints

### 1. Verify Single Email

```bash
POST /verify-email
Content-Type: application/json

{
  "email": "shubham@fusionsync.ai"
}
```

**Response:**

```json
{
  "email": "shubham@fusionsync.ai",
  "status": "risky",
  "reason": "smtp_550_possible_valid",
  "message": "Email verification completed: risky"
}
```

### 2. Find Email by Name & Website

```bash
POST /find-email
Content-Type: application/json

{
  "name": "Shubham Kashyap",
  "website": "https://fusionsync.ai"
}
```

**Response:**

```json
{
  "name": "Shubham Kashyap",
  "website": "https://fusionsync.ai",
  "total_permutations": 18,
  "valid_email": "shubham@fusionsync.ai",
  "found": true,
  "permutations_tested": [...]
}
```

### 3. Bulk CSV Verification

```bash
POST /verify
Content-Type: multipart/form-data

file: <csv_file>
```

Monitor progress: `GET /progress?job_id=<id>`  
Download results: `GET /download?job_id=<id>&type=all`

## 📊 Understanding Results

### Status Values

#### ✅ `valid`

- Email passed SMTP verification (code 250)
- Safe to send emails

#### ⚠️ `risky` (IMPORTANT!)

**Many legitimate emails return "risky"!** This happens when:

- Provider blocks SMTP verification (Namecheap, GoDaddy, GoHighLevel)
- Greylisting detected
- Temporary connection issues
- Rate limiting

**Recommendation:** Treat "risky" emails from known business domains as **likely valid**.

#### ❌ `invalid`

- Definite syntax errors
- No MX records
- Disposable email services
- Confirmed non-existent (SMTP 551, 552, 553)

### Common Reason Codes

| Reason                    | Status  | Meaning                                       |
| ------------------------- | ------- | --------------------------------------------- |
| `smtp_ok`                 | valid   | ✅ Verified successfully                      |
| `smtp_550_possible_valid` | risky   | ⚠️ Server blocks verification (likely valid!) |
| `greylist_code_450`       | risky   | ⚠️ Greylisting (retry later)                  |
| `smtp_timeout`            | risky   | ⚠️ Connection timeout                         |
| `bad_syntax`              | invalid | ❌ Invalid format                             |
| `no_mx`                   | invalid | ❌ No mail servers                            |

## 🧪 Testing

### Test Your Emails

```bash
# Activate venv
source venv/bin/activate

# Run test script
python test_verification.py
```

### API Testing

```bash
# Test verification
curl -X POST http://localhost:5050/verify-email \
  -H "Content-Type: application/json" \
  -d '{"email": "info@fusionsync.ai"}'

# Test email finder
curl -X POST http://localhost:5050/find-email \
  -H "Content-Type: application/json" \
  -d '{"name": "Shubham Kashyap", "website": "fusionsync.ai"}'
```

## 🏗️ Project Structure

```
email-verifier/
├── app.py                    # Main Flask application
├── utils/
│   ├── __init__.py
│   ├── email_utils.py        # Verification logic (DRY principle)
│   └── email_permutations.py # Email permutation generator
├── test_verification.py      # Test script
├── README.md                 # This file
├── API_DOCS.md              # Detailed API documentation
├── IMPROVEMENTS.md          # Technical improvements explained
└── venv/                     # Virtual environment
```

## 🔧 Technical Highlights

### Multi-Layered Verification

1. **Syntax Validation** - Regex pattern matching
2. **DNS/MX Validation** - Domain has mail servers
3. **SMTP Verification** - Mailbox existence check
4. **Retry Logic** - Up to 3 attempts with backoff
5. **Error Classification** - Smart status assignment

### Retry Strategy

```
Attempt 1: Immediate (0s delay)
Attempt 2: 3s delay
Attempt 3: 8s delay
Attempt 4: 15s delay
```

### Valid Sender Domain

Uses `gmail.com` for SMTP verification to avoid rejections from servers that block unknown/invalid sender domains.

## 📈 Performance

- **Single verification:** 2-20 seconds (depends on retries)
- **Email finder:** 5-30 seconds (tests 18 permutations **in parallel** with 10 concurrent workers) ⚡
- **Bulk processing:** Varies by list size

**NEW:** Email finder now runs verifications in parallel, making it 5-10x faster!

## 🎯 Use Cases

### 1. Your GoHighLevel/Namecheap Emails

```
Input: shubham@fusionsync.ai, info@fusionsync.ai
Expected: "risky" status with "smtp_550_possible_valid"
Action: ✅ These are valid emails!
```

### 2. Finding Employee Emails

```
Input: "John Doe" @ "company.com"
Output: Tests 18 variations, returns first valid match
```

### 3. List Cleaning

```
Input: CSV with 10,000 emails
Output: Filtered CSV with only valid/risky emails
```

## 📚 Documentation

- `API_DOCS.md` - Complete API reference with examples
- `IMPROVEMENTS.md` - Technical details of verification improvements
- `API_EXAMPLES.md` - Original API examples

## 🐛 Troubleshooting

### "Risky" status for known valid emails

**This is expected!** Many providers block SMTP verification. Treat as likely valid.

### Slow verification

Retry logic adds up to 26 seconds. For faster results without SMTP, implement DNS-only mode.

### Connection timeouts

Increase timeout in `utils/email_utils.py` (currently 15s).

## 🤝 Contributing

This tool follows the DRY (Don't Repeat Yourself) principle:

- All verification logic in `utils/email_utils.py`
- All permutation logic in `utils/email_permutations.py`
- Clean separation of concerns

## 📄 License

Use freely for your projects!

---

**🔥 Built with best practices from industry research on email verification, greylisting, and SMTP validation.**

---
The hosted server have limits based on VPS IP so not ideal to use the hosted api 

instead its more suited to local - either repository clone or a desktop app 


Testing: 

LOCAL
Host: http://127.0.0.1:5050
Endpoint: http://127.0.0.1:5050/verify-email
python scripts/parallel_verify_email.py --url http://127.0.0.1:5050/verify-email --workers 50 --requests 300

Run NGROK Server Pointed to 5050 (app is running here by default) - run in terminal
`npx ngrok http --domain=deservedly-underaccommodated-maryrose.ngrok-free.dev 5050`
This will route the requests from ngrok domain to localhost (PORT 5050)

NGROK
Host: https://deservedly-underaccommodated-maryrose.ngrok-free.dev
Endpoint: http://127.0.0.1:5050/verify-email
python scripts/parallel_verify_email.py --url https://deservedly-underaccommodated-maryrose.ngrok-free.dev/verify-email --workers 50 --requests 100



