# Processing

How bulk list verification works: chunk claiming, parallel SMTP checks, status transitions, and failure recovery.

---

## Processor overview

```
┌──────────────────────────────────────────────────┐
│  In-app tick loop (every 15 seconds)           │
│                                                  │
│  process_chunk()                                 │
│    ├─ promote_queued_list()                      │
│    ├─ while time_budget remaining:               │
│    │    ├─ claim_rows(concurrency)               │
│    │    ├─ verify_batch(rows)  ← parallel SMTP   │
│    │    └─ write_results(rows)                   │
│    └─ finalize_list_if_done()                    │
└──────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  pg_cron (maintenance, every 5 min / daily)      │
│    ├─ recover_stale_rows()                       │
│    ├─ mark_interrupted_lists()                   │
│    ├─ refresh_stats()                            │
│    └─ purge_old_lists()                          │
└──────────────────────────────────────────────────┘
```

The tick loop drives all verification work. pg_cron only cleans up edge cases.

---

## List status machine

```
                    ┌─────────┐
                    │  draft  │  CSV uploaded, not yet queued
                    └────┬────┘
                         │ user: Verify
                         ▼
                    ┌─────────┐
              ┌────▶│ queued  │◀──── resume (from paused)
              │     └────┬────┘
              │          │ processor: promote (if slot free)
              │          ▼
              │     ┌────────────┐
              │     │ processing │◀──┐
              │     └─────┬──────┘   │ processor: next chunk
              │           │          │
    user:     │     ┌─────┼─────┬────────┐
    pause ────┼────▶│paused│     │        │
              │     └─────┘     │        │
    user:     │           ┌─────┘        │
    cancel ───┼──────────▶│ cancelled    │
              │           │              │
              │           ▼              │
              │     ┌───────────┐  ┌─────┴──────┐
              └─────│ completed │  │ failed /   │
                    └───────────┘  │ interrupted│
                                   └────────────┘
```

| Transition | Trigger |
|---|---|
| `draft` → `queued` | User clicks Verify |
| `queued` → `processing` | Processor tick, no other list processing |
| `processing` → `completed` | Zero pending/processing rows remain |
| `processing` → `paused` | User clicks Pause (in-flight chunk finishes) |
| `paused` → `processing` | User clicks Resume |
| `processing` → `cancelled` | User clicks Cancel |
| `queued` → `cancelled` | User cancels before processing starts |
| `processing` → `interrupted` | pg_cron: no progress for 15 min, no active rows |
| `*` → `failed` | Unrecoverable error (DB write failure, corrupt CSV) |

---

## Row status machine

```
pending ──claim──▶ processing ──verify──▶ verified
                                      ├─▶ risky
                                      └─▶ failed

pending ──cancel──▶ skipped  (list cancelled)
processing ──stale recovery──▶ pending  (re-claimed on next tick)
```

| Row status | Meaning |
|---|---|
| `pending` | Uploaded, not yet checked |
| `processing` | Claimed by current chunk, SMTP in progress |
| `verified` | SMTP accepted (internal: `valid`) |
| `risky` | Inconclusive (internal: `risky`) |
| `failed` | Definite failure (internal: `invalid`) |
| `skipped` | List was cancelled before this row was reached |

---

## Chunk processing detail

### Step 1: Promote queued list

If no list is currently `processing`, atomically promote the oldest `queued` list. The partial unique index prevents two lists entering `processing` simultaneously.

Settings snapshot is frozen on the list at queue time — changing global settings mid-run does not affect an active list.

### Step 2: Claim rows

```python
rows = claim_rows(list_id, limit=settings.concurrency)
# Atomic UPDATE...RETURNING, see DATABASE.md
```

If zero rows returned:
- Check if list has any `pending` rows → another tick is mid-chunk, exit
- Check if list has zero `pending` and zero `processing` → finalize as `completed`

### Step 3: Verify batch

```python
with ThreadPoolExecutor(max_workers=concurrency) as pool:
    futures = {pool.submit(check_email, row.email, settings): row for row in rows}
    for future in as_completed(futures):
        row = futures[future]
        internal_status, reason = future.result()
        row.result_status = map_status(internal_status)
        row.reason = reason
```

`check_email()` receives per-list settings:
- `timeout_seconds`
- `retry_count`
- `smtp_helo_domain`

Status mapping:

| `check_email()` returns | Row status | CSV export label |
|---|---|---|
| `valid` | `verified` | Verified |
| `risky` | `risky` | Risky |
| `invalid` | `failed` | Failed |

Empty email in CSV row → `failed`, reason: `empty_email`. Row is still written to output.

### Step 4: Write results

Batch UPDATE rows and increment list counters in a single transaction:

```sql
BEGIN;
  UPDATE list_rows SET status = $2, reason = $3, checked_at = now()
    WHERE id = $1;
  UPDATE lists SET
    processed_rows = processed_rows + 1,
    verified_count = verified_count + CASE WHEN $2 = 'verified' THEN 1 ELSE 0 END,
    risky_count    = risky_count    + CASE WHEN $2 = 'risky'    THEN 1 ELSE 0 END,
    failed_count   = failed_count   + CASE WHEN $2 = 'failed'   THEN 1 ELSE 0 END,
    updated_at = now()
  WHERE id = $4;
COMMIT;
```

### Step 5: Inner loop

Repeat steps 2–4 until:
- No pending rows remain, OR
- Time budget exhausted (default 50 seconds)

This means a single 15-second tick interval can process many chunks. The tick interval controls how soon a newly queued list is picked up; the time budget controls throughput per invocation.

### Step 6: Finalize

If list has zero `pending` and zero `processing` rows:

```sql
UPDATE lists SET status = 'completed', completed_at = now(), updated_at = now()
WHERE id = $1 AND status = 'processing';
```

---

## Idempotency guarantees

| Scenario | Behavior |
|---|---|
| Tick runs twice while chunk in flight | Second claim returns 0 rows (already `processing`) — no-op |
| Container crashes mid-chunk | Rows stuck `processing` → pg_cron resets to `pending` after 10 min |
| Container restarts, list was `processing` | Next tick continues from remaining `pending` rows |
| User pauses mid-chunk | In-flight chunk completes; next tick sees `paused`, skips list |
| User cancels | List → `cancelled`; remaining `pending` → `skipped` |
| Same row claimed twice | Impossible: claim requires `status = 'pending'` |

No row is ever verified twice unless stale recovery resets it (which only happens after 10 min stuck, indicating the check never completed).

---

## Concurrency and rate limiting

Default concurrency: **10** parallel SMTP connections per chunk.

| Concurrency | UI behavior |
|---|---|
| 1–25 | Normal operation |
| 26–50 | Warning banner: "High concurrency may trigger rate limiting from Gmail, Outlook, and other providers" |
| 51+ | Blocked in settings validation |

Timeout per check: **15 seconds** (configurable).

Retry count: **1** (configurable) — applied only on ambiguous/greylist responses, not on definite failures.

---

## Time estimation

Shown on upload confirmation before user queues the list:

```
estimated_seconds = total_rows × avg_check_time / concurrency
avg_check_time    = 5 seconds (conservative default)
```

Example: 10,000 rows, concurrency 10 → ~5,000 seconds → ~83 minutes.

Display as human-readable range: "approximately 1h 20m – 2h 30m".

---

## Pause / Resume / Cancel

### Pause

```sql
UPDATE lists SET status = 'paused', updated_at = now()
WHERE id = $1 AND status = 'processing';
```

Current chunk finishes. Processor skips paused lists on subsequent ticks.

### Resume

```sql
UPDATE lists SET status = 'processing', updated_at = now()
WHERE id = $1 AND status = 'paused';
```

If no other list is processing, this list continues immediately on next tick. If another list is processing, resume re-queues:

```sql
UPDATE lists SET status = 'queued', updated_at = now()
WHERE id = $1 AND status = 'paused';
```

### Cancel

```sql
BEGIN;
  UPDATE lists SET status = 'cancelled', completed_at = now(), updated_at = now()
    WHERE id = $1 AND status IN ('queued', 'processing', 'paused');
  UPDATE list_rows SET status = 'skipped'
    WHERE list_id = $1 AND status = 'pending';
COMMIT;
```

In-flight `processing` rows complete their check but list is already cancelled — results still written for transparency.

---

## Container restart behavior

On app boot:

1. Run pending migrations
2. No automatic status changes — pg_cron handles stale recovery within 5 minutes
3. Processor tick starts immediately

A list mid-verification resumes automatically when the tick loop reclaims its pending rows. No user action required.

If user wants a clean restart: cancel the list manually, re-upload, verify again.

---

## Find Email & Verify (instant tools)

These bypass the list/chunk system entirely. Synchronous HTTP requests:

| Tool | Max duration | Concurrency |
|---|---|---|
| Verify single email | ~15s | 1 |
| Find by name (~18 permutations) | ~30–60s | min(10, permutation count) |
| Find by company (5 role addresses) | ~30s | 5 |

Not subject to one-list-at-a-time constraint. If a list is processing and user runs Find Email, both proceed — Find Email uses its own thread pool, not the chunk processor's concurrency slot.

Consideration: if list processing is active, Find Email concurrency is capped at `min(5, settings.concurrency)` to avoid SMTP overload. Documented behavior, not a hard block.
