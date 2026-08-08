# Module 03 — Extended Thinking

Course section: *Production-Grade Prompting, Agents & Tool Use → Extended Thinking*

## Files

| File | Purpose |
|---|---|
| `1_basic_thinking.py` | Enable extended thinking and read the separate `thinking` content block |
| `2_thinking_budget_comparison.py` | Same hard question at a small vs. large `budget_tokens`, side by side |

## Run it

```bash
uv run 03-extended-thinking/1_basic_thinking.py
uv run 03-extended-thinking/2_thinking_budget_comparison.py
```

## Key concepts

- Extended thinking makes Claude reason step-by-step in a dedicated `thinking` content block before writing its final `text` answer — inspect `response.content` for both block types.
- These examples use `claude-haiku-4-5`, so thinking is configured the classic way: `thinking={"type": "enabled", "budget_tokens": N}`. `budget_tokens` must be **less than** `max_tokens` and **at least 1024**.
- Newer models (Opus 4.6+/Sonnet 4.6+) replace this with **adaptive thinking** (`thinking={"type": "adaptive"}` + `output_config={"effort": ...}`) — no fixed budget, Claude decides how much to think. Worth knowing the newer form exists even though these examples use the older, cheaper one.
- A bigger `budget_tokens` doesn't always mean a better answer on an easy problem — try tweaking the question in `2_thinking_budget_comparison.py` to something genuinely hard and see the gap widen.

## Try this while studying

- Change the question in `1_basic_thinking.py` to something trivial (e.g. "what's 2+2?") and see how short the thinking block gets.
- Print `response.usage` in either script to see how thinking tokens are billed separately from output tokens.
- Log your takeaway in [`NOTES.md`](../NOTES.md).
