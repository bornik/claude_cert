# Module 02 — Prompting Craft

Course section: *Production-Grade Prompting, Agents & Tool Use → Prompting Craft*

## Files

| File | Purpose |
|---|---|
| `process_ticket.py` | Prompt runner — classifies a support ticket into category + urgency |
| `system_prompt.txt` | The system prompt sent with each request — edit this to change behavior |
| `examples.json` | Sample ticket texts used as test inputs |

## Run it

```bash
uv run 02-prompting-craft/process_ticket.py                 # first example
uv run 02-prompting-craft/process_ticket.py "custom ticket"  # your own input
uv run 02-prompting-craft/process_ticket.py --all             # every example in examples.json
```

## Lesson notes

- **Watch Out — "The prompt that grew longer instead of better"**: a prompt can look production-ready and still fail quietly on edge cases. When that happens it's usually because a constraint wasn't specified precisely enough, not because the model is being careless.
- The lesson's running example (classify a ticket into billing/technical/escalation) is exactly what `process_ticket.py` + `system_prompt.txt` implement here — use it as your test bed.

## Try this while studying

- Copy `system_prompt.txt` before editing it (`cp system_prompt.txt system_prompt_v1.txt`) so you can diff versions as you apply each revision pass from the lesson.
- After each course screen about a new constraint, add a matching edge-case ticket to `examples.json` and re-run `--all` to see if the current prompt handles it.
