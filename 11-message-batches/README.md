# Module 11 — Message Batches API

## Files

### 1️⃣ `1_message_batches.py` — Async Bulk Processing
**What:** Submits 3 independent ticket-classification requests as a single batch, polls `batches.retrieve()` until it ends, then streams results back matched by `custom_id`.

**Key concepts:**
- One `batches.create()` call queues many independent requests; you poll for status instead of blocking synchronously on each one
- `custom_id` maps a result back to its request — results can arrive in any order
- Live run: the batch went `in_progress` → `ended` in about 90 seconds for 3 tiny requests; large real-world batches can take much longer (up to 24h), which is why the design is poll-based, not blocking
- Not for latency-sensitive single requests — use `messages.create()` for those

```bash
uv run 11-message-batches/1_message_batches.py
```
