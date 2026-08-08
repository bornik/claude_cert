# Module 02 — Prompting Craft

Course section: *Production-Grade Prompting, Agents & Tool Use → Prompting Craft*

## Files

| File | Purpose |
|---|---|
| `process_ticket.py` | Prompt runner — classifies a support ticket. Supports `--prompt-version` and `--diff` |
| `prompt_iteration.py` | Runs the same ticket through 6 progressively constrained prompts (the lesson's "revision passes") |
| `system_prompt.txt` | The "refined" system prompt — edit this to change behavior |
| `system_prompt_bare.txt` | The lesson's bare/unconstrained prompt, for comparison |
| `examples.json` | Sample ticket texts used as test inputs |

## Run it

```bash
uv run 02-prompting-craft/process_ticket.py                          # first example, refined prompt
uv run 02-prompting-craft/process_ticket.py "custom ticket"          # your own input
uv run 02-prompting-craft/process_ticket.py --all                    # every example in examples.json
uv run 02-prompting-craft/process_ticket.py --prompt-version bare "custom ticket"  # use the bare prompt
uv run 02-prompting-craft/process_ticket.py --diff "custom ticket"   # bare vs refined, side by side

uv run 02-prompting-craft/prompt_iteration.py                        # 6-pass revision walkthrough
```

## Lesson notes

- **Watch Out — "The prompt that grew longer instead of better"**: a prompt can look production-ready and still fail quietly on edge cases. When that happens it's usually because a constraint wasn't specified precisely enough, not because the model is being careless.
- The lesson's running example (classify a ticket into billing/technical/escalation) is exactly what `process_ticket.py` + `system_prompt.txt` implement here — use it as your test bed.

## Try this while studying

- Run `prompt_iteration.py` to see the lesson's 6 revision passes on a real ticket — watch the output go from free-form prose to clean, parseable JSON.
- Run `process_ticket.py --diff` on a few different tickets to see how much the bare prompt varies run-to-run compared to the refined one.
- Copy `system_prompt.txt` before editing it (`cp system_prompt.txt system_prompt_v1.txt`) so you can diff versions as you apply your own revision pass.
- After each course screen about a new constraint, add a matching edge-case ticket to `examples.json` and re-run `--all` to see if the current prompt handles it.
- Log the screen and takeaway in [`NOTES.md`](../NOTES.md) after you finish here.
