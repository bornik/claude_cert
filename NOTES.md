# Study Notes

One line per course screen: the takeaway, and what you ran to test it. Cheap to keep, becomes a study guide by the end.

Format:
```
## [Module] Screen N/29 — Title
Takeaway: ...
Tried: `uv run ...`
```

---

## Prompting Craft — Screen 3/29 — "The prompt that grew longer instead of better"
Takeaway: A prompt can look production-ready and still fail quietly on edge cases — usually because a constraint wasn't specified precisely enough, not because the model was careless.
Tried: `uv run 02-prompting-craft/prompt_iteration.py` — watched the same ticket go from free-form prose to clean JSON across 6 constraint passes; also `uv run 02-prompting-craft/process_ticket.py --diff` to compare bare vs. refined prompts side by side.
