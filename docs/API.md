# API Reference

Base URL: `http://localhost:5050`

All JSON responses use `Content-Type: application/json`. CSV exports use `text/csv`.

---

## Status values

### Internal (API response bodies)

| Value | Meaning |
|---|---|
| `valid` / `verified` | SMTP confirmed |
| `risky` | Inconclusive |
| `invalid` / `failed` | Definite failure |

List row endpoints return row status: `verified`, `risky`, `failed`, `pending`, `processing`, `skipped`.

### Human-readable reasons

Every non-verified result includes a `reason` string. Examples:

| Reason | Status | Meaning |
|---|---|---|
| `smtp_ok` | verified | SMTP 250 accepted |
| `bad_syntax` | failed | Invalid email format |
| `no_mx` | failed | Domain has no MX records |
| `disposable_domain` | failed | Known disposable provider |
| `empty_email` | failed | Blank email in CSV row |
| `smtp_550_mailbox_not_found` | failed | Mailbox confirmed absent |
| `smtp_550_verification_blocked` | risky | Provider blocked verification |
| `greylist_code_451` | risky | Temporary rejection |
| `smtp_timeout` | risky | Connection timed out |
| `smtp_inconclusive` | risky | Could not determine |

---

## Health

### `GET /health`

Docker healthcheck. No auth.

**Response 200:**

```json
{
  "status": "healthy",
  "service": "email-verifier",
  "database": "connected"
}
```

---

## Settings

### `GET /api/settings`

Returns all settings as key-value pairs.

**Response 200:**

```json
{
  "concurrency": 10,
  "timeout_seconds": 15,
  "retry_count": 1,
  "smtp_helo_domain": "",
  "chunk_time_budget_seconds": 50,
  "theme": "dark",
  "max_upload_size_mb": 50
}
```

### `PUT /api/settings`

Partial update. Only supplied keys are changed.

**Request:**

```json
{
  "concurrency": 15,
  "timeout_seconds": 20
}
```

**Response 200:** Updated settings object.

**Validation errors 400:**

- `concurrency` must be 1–50
- `timeout_seconds` must be 5–60
- `retry_count` must be 0–3

---

## Lists

### `GET /api/lists`

Dashboard / history. Returns all lists, newest first.

**Query params:**

| Param | Type | Description |
|---|---|---|
| `status` | string | Filter by status (optional) |
| `limit` | int | Default 50, max 200 |
| `offset` | int | Pagination offset |

**Response 200:**

```json
{
  "lists": [
    {
      "id": "uuid",
      "name": "Q1 Dental Leads",
      "filename": "dental_leads.csv",
      "status": "completed",
      "total_rows": 10000,
      "processed_rows": 10000,
      "verified_count": 6200,
      "risky_count": 2100,
      "failed_count": 1700,
      "skipped_count": 0,
      "created_at": "2026-08-06T10:00:00Z",
      "started_at": "2026-08-06T10:01:00Z",
      "completed_at": "2026-08-06T11:30:00Z"
    }
  ],
  "total": 12
}
```

### `POST /api/lists`

Create a new list.

**Request:**

```json
{
  "name": "Q1 Dental Leads"
}
```

**Response 201:**

```json
{
  "id": "uuid",
  "name": "Q1 Dental Leads",
  "status": "draft",
  "created_at": "2026-08-06T10:00:00Z"
}
```

### `GET /api/lists/:id`

Single list detail with progress.

**Response 200:** List object (same shape as above, includes `settings_snapshot`, `email_column`).

**Response 404:** List not found.

### `DELETE /api/lists/:id`

Delete a list and all its rows. Allowed for any status except `processing`.

**Response 204:** Deleted.

**Response 409:** Cannot delete a list currently processing.

---

## List upload

### `POST /api/lists/:id/upload`

Upload CSV file. Multipart form data.

**Form fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | yes | CSV file |
| `email_column` | string | no | Column name override. Auto-detected if omitted. |

**Auto-detection:** looks for column named `email` (case-insensitive). If multiple candidates or none found, returns 422 with detected columns for user selection.

**Response 200:**

```json
{
  "list_id": "uuid",
  "filename": "dental_leads.csv",
  "total_rows": 10000,
  "email_column": "Email",
  "estimated_duration": "1h 20m – 2h 30m",
  "columns": ["Name", "Company", "Email", "Phone"]
}
```

**Response 422:**

```json
{
  "error": "ambiguous_email_column",
  "columns": ["Email Address", "Work Email", "Name"],
  "message": "Multiple email-like columns found. Specify email_column."
}
```

After upload, list remains in `draft` until user calls verify.

---

## List actions

### `POST /api/lists/:id/verify`

Queue list for verification.

**Preconditions:**
- List status is `draft`
- `total_rows > 0`
- Valid `email_column` set

**Response 200:**

```json
{
  "id": "uuid",
  "status": "queued",
  "queue_position": 1
}
```

If another list is processing, `queue_position` indicates FIFO position.

**Response 409:** List not in draft status, or no rows uploaded.

### `POST /api/lists/:id/pause`

Pause a processing list.

**Response 200:** `{ "status": "paused" }`

**Response 409:** List not processing.

### `POST /api/lists/:id/resume`

Resume a paused list.

**Response 200:** `{ "status": "processing" }` or `{ "status": "queued" }` if another list is active.

**Response 409:** List not paused.

### `POST /api/lists/:id/cancel`

Cancel a queued, processing, or paused list.

**Response 200:** `{ "status": "cancelled" }`

---

## List results

### `GET /api/lists/:id/rows`

Paginated row results.

**Query params:**

| Param | Type | Description |
|---|---|---|
| `status` | string | Filter: `verified`, `risky`, `failed`, `pending`, `skipped` |
| `search` | string | Filter by email substring |
| `limit` | int | Default 100, max 500 |
| `offset` | int | Pagination offset |

**Response 200:**

```json
{
  "rows": [
    {
      "row_index": 0,
      "email": "john@acme.com",
      "status": "verified",
      "reason": "smtp_ok",
      "raw_row": { "Name": "John", "Company": "Acme", "Email": "john@acme.com" },
      "checked_at": "2026-08-06T10:05:00Z"
    }
  ],
  "total": 10000,
  "limit": 100,
  "offset": 0
}
```

### `GET /api/lists/:id/export`

Download CSV export.

**Query params:**

| Param | Values | Description |
|---|---|---|
| `filter` | `all` (default), `risky_failed` | Which rows to include |

**Response 200:** `text/csv` stream.

Columns: all original CSV columns + `V Status` + `V Reason`.

Content-Disposition: `attachment; filename="{list_name}-verified.csv"`

### `GET /api/lists/:id/progress`

Server-Sent Events stream for live progress.

**Response:** `text/event-stream`

```
event: progress
data: {"processed": 4500, "total": 10000, "verified": 2800, "risky": 900, "failed": 800, "status": "processing"}

event: progress
data: {"processed": 4600, "total": 10000, "verified": 2860, "risky": 920, "failed": 820, "status": "processing"}

event: complete
data: {"processed": 10000, "total": 10000, "verified": 6200, "risky": 2100, "failed": 1700, "status": "completed"}
```

Events emitted every 2 seconds while processing. Connection closes after `complete` or `cancelled` event.

---

## Stats

### `GET /api/stats`

Dashboard all-time numbers.

**Response 200:**

```json
{
  "total_emails_verified": 245000,
  "total_lists_completed": 38,
  "total_lists": 42
}
```

---

## Tools — Verify Email

### `POST /verify-email`

Verify a single email address. Synchronous.

**Request:**

```json
{
  "email": "john@acme.com"
}
```

**Response 200:**

```json
{
  "email": "john@acme.com",
  "status": "valid",
  "reason": "smtp_ok",
  "message": "Email verification completed: valid"
}
```

Status values: `valid`, `risky`, `invalid` (legacy naming preserved for API compat).

---

## Tools — Find Email

### `POST /find-email`

Find email by full name and company domain/website. Tests permutations in parallel.

**Request:**

```json
{
  "name": "John Smith",
  "website": "acme.com"
}
```

`website` accepts bare domain or full URL.

**Response 200:**

```json
{
  "name": "John Smith",
  "website": "acme.com",
  "domain": "acme.com",
  "total_permutations": 18,
  "found": true,
  "valid_email": "john.smith@acme.com",
  "permutations_tested": [
    { "email": "john.smith@acme.com", "status": "valid", "reason": "smtp_ok" },
    { "email": "jsmith@acme.com", "status": "risky", "reason": "smtp_550_verification_blocked" },
    { "email": "john@acme.com", "status": "invalid", "reason": "smtp_550_mailbox_not_found" }
  ]
}
```

Results sorted by confidence: first `valid` result is `valid_email`. If none valid, best `risky` result returned with `found: false` and `best_guess` field.

### `POST /find-email/company`

Find best contact email for a company domain. Tests common role-based addresses.

**Request:**

```json
{
  "domain": "acme.com"
}
```

**Response 200:**

```json
{
  "domain": "acme.com",
  "found": true,
  "emails_tested": [
    { "email": "info@acme.com", "status": "valid", "reason": "smtp_ok" },
    { "email": "contact@acme.com", "status": "valid", "reason": "smtp_ok" },
    { "email": "sales@acme.com", "status": "risky", "reason": "smtp_550_verification_blocked" },
    { "email": "support@acme.com", "status": "invalid", "reason": "smtp_550_mailbox_not_found" },
    { "email": "hello@acme.com", "status": "invalid", "reason": "smtp_550_mailbox_not_found" }
  ],
  "best_email": "info@acme.com"
}
```

Role addresses tested: `info`, `contact`, `sales`, `support`, `hello`.

---

## Error format

All error responses:

```json
{
  "error": "error_code",
  "message": "Human-readable description"
}
```

| HTTP | When |
|---|---|
| 400 | Invalid request body or parameters |
| 404 | Resource not found |
| 409 | Invalid state transition |
| 413 | CSV file exceeds max upload size |
| 422 | Unprocessable (ambiguous email column, empty CSV) |
| 500 | Internal server error |

---

## Legacy endpoints

These paths are preserved unchanged for backward compatibility with existing integrations:

| Endpoint | Status |
|---|---|
| `POST /verify-email` | Active |
| `POST /find-email` | Active |
| `POST /verify` | **Deprecated** — replaced by `/api/lists/:id/upload` + `/verify` |
| `GET /progress` | **Deprecated** — replaced by `/api/lists/:id/progress` |
| `GET /download` | **Deprecated** — replaced by `/api/lists/:id/export` |

Deprecated endpoints remain functional until v2.0.

---

## External access via ngrok

When ngrok is configured, all public API endpoints are accessible over HTTPS:

```
https://abc123.ngrok.io/verify-email
https://abc123.ngrok.io/find-email
https://abc123.ngrok.io/api/lists
```

No authentication in v1. Users exposing via ngrok should treat the URL as sensitive.

Internal processor endpoints do not exist over HTTP — chunk processing is in-process only.
