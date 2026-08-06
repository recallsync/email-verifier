# UI Specification

Single-page application served at `localhost:5050`. Dark mode default. Dev-tool aesthetic (n8n, Uptime Kuma) — not consumer SaaS.

Built with **React + Vite + shadcn/ui + Tailwind**. React Router for navigation. All API calls to `/api/*`.

---

## Global layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo] Email Verifier          [Tools] [Settings] [Theme]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                      Main content area                      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  ⓘ Local SMTP verification cannot fully confirm mailboxes  │
│    on Gmail, Outlook, and similar providers. Risky results  │
│    are expected — export them for a second pass if needed.  │
└─────────────────────────────────────────────────────────────┘
```

### Navigation

| Nav item | Route | Description |
|---|---|---|
| Lists (default) | `/` | Dashboard — all lists |
| Tools | `/tools` | Find email + single verify |
| Settings | `/settings` | Configuration |

Persistent footer note about SMTP limitations. Calm tone, not a warning banner. Collapsible after first read (preference stored in localStorage).

### Theme

- Default: **dark** (shadcn/ui CSS variables, toggled via settings + header button)
- Status colors: Verified `#22c55e`, Risky `#f59e0b`, Failed `#ef4444`
- Light/dark mode persisted via `PUT /api/settings` (`theme` key)

---

## Screen 1: Dashboard (Lists)

**Route:** `/`

### Header section

- Page title: "Lists"
- Primary CTA button: **+ New List**
- Stats pill (top right): "245,000 emails verified" (from `/api/stats`)

### Active processing banner

If a list is currently `processing`, show a prominent but non-blocking banner:

```
▶ Verifying: Q1 Dental Leads — 4,500 / 10,000 (45%)
  Verified: 2,800  Risky: 900  Failed: 800
  [View] [Pause]
```

If lists are queued:

```
⏳ Queue: "March Leads" waiting (position 1)
```

### Lists table

| Column | Content |
|---|---|
| Name | List name, linked to detail |
| File | Original filename |
| Status | Badge: draft, queued, processing, paused, completed, cancelled, failed, interrupted |
| Rows | total_rows |
| Results | Verified / Risky / Failed counts (if started) |
| Created | Relative date |
| Actions | View, Export (if completed), Delete |

Sort: newest first. Filter tabs above table: All | Active | Completed.

Empty state: illustration + "Upload your first lead list to get started" + New List button.

---

## Screen 2: New List / Upload

**Route:** `/lists/new`

### Step 1: Name

- Text input: "List name" (required)
- Placeholder: "e.g. Q1 Dental Leads"

### Step 2: Upload CSV

- Drag-and-drop zone (dashed border, file icon)
- "or click to browse"
- Accepts `.csv` only
- On drop: upload via `POST /api/lists/:id/upload`

### Step 3: Column confirmation (if needed)

If API returns `ambiguous_email_column`:

- Radio list of detected columns
- User selects email column, re-submits

### Step 4: Confirmation

After successful upload:

```
✓ dental_leads.csv uploaded
  10,000 rows detected
  Email column: "Email"
  Estimated time: ~1h 20m – 2h 30m

  [Start Verification]    [Upload Different File]
```

"Start Verification" calls `POST /api/lists/:id/verify` → redirect to list detail.

---

## Screen 3: List Detail

**Route:** `/lists/:id`

### Processing state

Progress section (visible when status is `queued`, `processing`, or `paused`):

```
Q1 Dental Leads                                    [Pause] [Cancel]
━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░  45%  (4,500 / 10,000)

  ✓ Verified    2,800  (62%)
  ⚠ Risky       900   (20%)
  ✗ Failed      800   (18%)
```

- Progress bar driven by SSE (`/api/lists/:id/progress`)
- Counts update live
- Pause/Cancel buttons with confirmation dialog on cancel

Queued state: "Waiting in queue (position 1)..." with spinner.

Paused state: "Paused at 4,500 / 10,000" + Resume button.

### Completed state

Summary cards:

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  10,000  │  │  6,200   │  │  2,100   │  │  1,700   │
│  Total   │  │ Verified │  │  Risky   │  │  Failed  │
│          │  │   62%    │  │   21%    │  │   17%    │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```

Failure reason breakdown (horizontal bar chart or table):

| Reason | Count |
|---|---|
| smtp_ok | 6200 |
| smtp_550_verification_blocked | 1200 |
| smtp_timeout | 400 |
| no_mx | 300 |
| smtp_550_mailbox_not_found | 900 |
| ... | |

### Results table

Filter tabs: All | Verified | Risky | Failed

Search box: filter by email.

Paginated table (100 rows per page):

| # | Email | V Status | V Reason | (original columns...) |
|---|---|---|---|---|

Status badges with color coding. Reason shown as secondary text below status.

### Export buttons

Two buttons, side by side:

1. **Download Full CSV** — all rows with V Status + V Reason columns
2. **Export Risky + Failed** — subset only, with helper text: "3,800 rows — send these to a paid verifier for extra certainty"

Both available once at least one row is checked (not just on completion).

---

## Screen 4: Tools

**Route:** `/tools`

Tabbed interface inspired by standard email finder UX (Hunter.io pattern):

```
┌──────────────────┬──────────────────┬──────────────────┐
│  Find by Name    │  Find by Company │  Verify Email    │
└──────────────────┴──────────────────┴──────────────────┘
```

---

### Tab: Find by Name

Headline: "Find the verified email address of any professional."

Input bar (single horizontal row):

```
┌─────────────────────────┬───┬─────────────────────┬────────┐
│  Enter a full name...   │ @ │  company.com        │  Find  │
└─────────────────────────┴───┴─────────────────────┴────────┘
```

- Name field: text input, required
- `@` separator: visual divider (not editable)
- Domain field: text input, placeholder "company.com", required
- Find button: triggers `POST /find-email`

**Loading state:** spinner + "Testing 18 email patterns..."

**Results state:**

If found:

```
✓ john.smith@acme.com — Verified
  Found via SMTP verification (pattern: first.last@domain)
```

If best guess (risky):

```
⚠ jsmith@acme.com — Risky
  Verification inconclusive. Provider may be blocking checks.
  18 patterns tested.
```

Expandable section: "All patterns tested" — table of all permutations with status badges.

If not found:

```
✗ No verified email found for John Smith at acme.com
  18 patterns tested. 0 verified, 3 risky, 15 failed.
  [Show all results]
```

---

### Tab: Find by Company

Headline: "Find the best contact email for a company."

Input bar:

```
┌─────────────────────────────┬────────┐
│  company.com                │  Find  │
└─────────────────────────────┴────────┘
```

Triggers `POST /find-email/company`.

**Results state:**

Table of tested role addresses:

| Email | Status | Reason |
|---|---|---|
| info@acme.com | Verified | smtp_ok |
| contact@acme.com | Verified | smtp_ok |
| sales@acme.com | Risky | smtp_550_verification_blocked |
| support@acme.com | Failed | smtp_550_mailbox_not_found |
| hello@acme.com | Failed | smtp_550_mailbox_not_found |

Best match highlighted at top: "Best match: info@acme.com"

---

### Tab: Verify Email

Headline: "Verify any email address."

Input bar:

```
┌─────────────────────────────────────┬────────┐
│  email@company.com                  │ Verify │
└─────────────────────────────────────┴────────┘
```

Triggers `POST /verify-email`.

**Results state:**

Large status card:

```
┌─────────────────────────────────────────┐
│  john@acme.com                          │
│                                         │
│  ✓ Verified                             │
│  SMTP accepted — mailbox likely exists  │
│                                         │
│  Reason: smtp_ok                        │
└─────────────────────────────────────────┘
```

Status-specific styling and copy:

| Status | Icon | Copy |
|---|---|---|
| Verified | ✓ green | "SMTP accepted — mailbox likely exists" |
| Risky | ⚠ amber | "Inconclusive — provider may use catch-all or greylisting" |
| Failed | ✗ red | "Definite issue — see reason below" |

---

## Screen 5: Settings

**Route:** `/settings`

Grouped form sections:

### Verification

| Setting | Control | Default | Notes |
|---|---|---|---|
| Concurrency | Number input + slider | 10 | Warning above 25 |
| Timeout | Number input (seconds) | 15 | Range 5–60 |
| Retry count | Number input | 1 | Range 0–3 |
| SMTP HELO domain | Text input | empty | Optional. Placeholder: "mail.yourdomain.com" |

Warning banner (shown when concurrency > 25):

> High concurrency may trigger rate limiting from Gmail, Outlook, and other major providers. Recommended: 10–15 for most lists.

### Appearance

| Setting | Control | Default |
|---|---|---|
| Theme | Toggle: Dark / Light | Dark |

### Data

| Setting | Control | Default |
|---|---|---|
| Retention | Display only | "Lists older than 90 days are auto-purged" |

Save button persists via `PUT /api/settings`. Auto-save on change (debounced 500ms) is acceptable alternative.

---

## UX rules

### Never drop rows

Export row count must always equal upload row count. UI displays row count at upload and on completion — if they differ, that's a bug.

### Always show the why

Every Risky and Failed row displays its `reason` in the results table. No status-only display.

### No blocking modals during processing

User can navigate away from a processing list to Dashboard, Tools, or Settings. Processing continues. Banner on Dashboard shows active list.

### Honest limits

- No "100% accurate" language anywhere
- Footer note always accessible
- Risky results explained inline, not hidden
- Export Risky + Failed presented as workflow optimization, not upsell

### Zero-config first run

App works with defaults. Settings screen is optional. First visit: Dashboard empty state → New List → upload → verify.

### Responsive

Desktop-first (primary use case). Functional on tablet. Mobile not a priority but layout should not break.

---

## Component inventory

| Component | Used on |
|---|---|
| `StatusBadge` | Lists table, results table, find results |
| `ProgressBar` | List detail |
| `CountCards` | List detail summary |
| `FileDropZone` | New list upload |
| `ListsTable` | Dashboard |
| `ResultsTable` | List detail |
| `TabBar` | Tools screen |
| `FindInputBar` | Tools — all three tabs |
| `ReasonBreakdown` | List detail completed state |
| `ExportButtons` | List detail |
| `ActiveBanner` | Dashboard |
| `SettingsForm` | Settings |
| `HonestLimitsFooter` | Global layout |
| `Toast` | Success/error notifications |

---

## Copy guidelines

| Context | Tone | Example |
|---|---|---|
| Verified | Confident but not absolute | "SMTP accepted — mailbox likely exists" |
| Risky | Honest, actionable | "Inconclusive — provider may block verification" |
| Failed | Direct | "Mailbox not found" / "No MX records" |
| Processing | Informative | "Verifying 4,500 of 10,000..." |
| Empty states | Encouraging, brief | "Upload your first lead list to get started" |
| Limits footer | Calm, factual | "Local SMTP verification cannot fully confirm..." |

Never use: "100%", "guaranteed", "accurate", "verified deliverable".
