# Module 01 — MSO Foundations

> Note: this is from a **different** certification track ("MSO Foundations") than the rest of this repo (which mostly follows *Production-Grade Prompting, Agents & Tool Use*). Numbered `01-` since you completed it first — folder order here just reflects when you took it, not a single course's sidebar.

Course sections covered: Orientation → How LLMs Behave → Models & Reasoning → Prompting Modes → Technical Substrate → Module Wrap-up.

## Files

| File | Purpose |
|---|---|
| `1_non_determinism.py` | Sends the same prompt 3 times — demonstrates the module-quiz point: identical prompts don't guarantee identical output |
| `2_prompting_modes.py` | Same question with no system prompt, with a system prompt, and in a multi-turn conversation — three ways context shapes the answer |

## Run it

```bash
uv run 01-mso-foundations/1_non_determinism.py
uv run 01-mso-foundations/2_prompting_modes.py
```

## Key concepts

- **Non-determinism ("How LLMs Behave")**: Claude samples each next token from a probability distribution rather than replaying a fixed script. Two calls with the identical prompt can produce different (but both valid) wording. This is why you should never rely on exact string matching against model output for anything beyond simple cases — check structure/meaning instead (see the JSON-parsing pattern in `02-prompting-craft/process_ticket.py`).
- **Prompting Modes**: `system` is a separate top-level API parameter (not a message) that sets persistent behavior for the whole conversation. Multi-turn conversations are just prior `user`/`assistant` messages resent on every request — the Messages API itself is stateless; *you* carry the history.

## Try this while studying

- Run `1_non_determinism.py` a few times — notice the *meaning* stays consistent even when wording differs.
- In `2_prompting_modes.py`, swap the system prompt for something wildly different (e.g. "Respond only in haiku") and see how much it changes the same question's answer.
- Log your takeaway in [`NOTES.md`](../NOTES.md).
