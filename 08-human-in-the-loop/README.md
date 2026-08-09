# Module 08 — Human-in-the-Loop

**Note:** this module's structure is reconstructed from general course-page/documentation descriptions, not a verified screen-by-screen syllabus. Update as real course screens confirm or correct the details.

## Files

### 1️⃣ `1_approval_gate.py` — Pausing Before an Irreversible Action
**What:** A tool-use loop where most tools auto-execute, but tools marked dangerous (here, `delete_account`) stop and wait for a human decision before your code runs them — not just before telling the user about it.

**Key concepts:**
- The gate is a single `if tool_use.name in DANGEROUS_TOOLS` check in your application code — Claude can still *ask* for the action, but cannot cause it
- If declined, Claude is told the human declined (as a `tool_result`), not given a fake success — it reasons from there
- Live run: Claude called `get_account_status` freely, but `delete_account` stopped for approval before executing

**When to use:** Any tool whose effect is destructive, hard to reverse, or costly if wrong (deletes, refunds, external emails, financial transactions)

```bash
uv run 08-human-in-the-loop/1_approval_gate.py
```
