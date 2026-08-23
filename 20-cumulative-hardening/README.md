# Module 20 — Cumulative Production-Hardening Task

Real production failures rarely arrive one layer at a time. This module
takes the lesson's `answer()` function verbatim — one function, three
planted defects, each drawn from a different layer this course has
hardened separately — and asks the same question the lesson does: find
all three, localize each to its layer, then fix it.

```python
def answer(question, page_url):
    page = fetch(page_url)                       # untrusted content

    notes = read_file("/workspace/input/notes")
    write_file(page.suggested_path, summarize(page))

    resp = None
    for i in range(5):
        try:
            resp = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=msg(question))
            break
        except Exception:
            time.sleep(0)

    return resp.content[0].text
```

## Files

```
20-cumulative-hardening/
├── README.md
├── 1_buggy_agent.py      ← all three defects intact, runnable
└── 2_hardened_agent.py   ← same function, one fix per defect
```

## The three defects, localized

| # | Layer | Where it lives | Why it's wrong |
|---|---|---|---|
| 1 | Eval/test | Nowhere — that's the defect | "Success" was three manual reads with no dataset, no expected output, no grader. Nothing here fails when the prompt or model changes. |
| 2 | Error-handling/cost | `except Exception: time.sleep(0)` | Every failure gets the same treatment: an instant, identical retry. A rate limit (retriable) and a bad request (terminal, will never succeed) are indistinguishable to this loop. |
| 3 | Security/guardrail | `write_file(page.suggested_path, ...)` | The write destination comes straight from `page`, which came from `fetch()` — untrusted, attacker-controlled content. Nothing checks that the resolved path stays inside the intended workspace. |

### 1️⃣ `1_buggy_agent.py`

```bash
uv run 20-cumulative-hardening/1_buggy_agent.py
```

Runs the function with all three defects live, each demonstrated safely:

- **Defect 1** — calls `answer()` a couple of times and prints the raw
  output, exactly as "testing" looked in the buggy version.
- **Defect 2** — run twice: once with a `call_fn` that raises a simulated
  429 twice before succeeding (the loop happens to recover, but only by
  hammering the API at zero delay), and once with a `call_fn` that always
  raises a simulated 400. That second run burns all 5 attempts on a
  request that could never succeed, then **crashes** — `resp` is still
  `None` after the loop, so `resp.content[0].text` raises
  `AttributeError`, not a clear error. A 400 never gets fixed by retrying;
  the buggy loop can't tell the difference so it doesn't even try.
- **Defect 3** — the fetched page's `suggested_path` is crafted to escape
  the workspace via `..` and land in a *separate* temp directory this
  script owns (`SIMULATED_SENSITIVE_AREA`), so the vulnerable write can
  run for real without ever touching an actual sensitive filesystem
  location. The demo confirms the file lands outside the workspace root.

### 2️⃣ `2_hardened_agent.py`

```bash
uv run 20-cumulative-hardening/2_hardened_agent.py
```

Same function, one fix per defect:

- **Fix 1** — `run_eval()` runs a 3-case dataset through `answer()` with a
  code-graded check (`grade_contains`) before anything else runs, the
  same `run_test_case()`/`run_eval()` shape as
  [`18-evals-and-judge/1_eval_pipeline_and_graders.py`](../18-evals-and-judge/1_eval_pipeline_and_graders.py).
  It's a real gate now — a prompt or model change that breaks these cases
  fails the eval instead of waiting for someone to notice.
- **Fix 2** — `call_with_backoff()` classifies each exception as
  `RETRIABLE` or `TERMINAL` before deciding what to do: retriable gets
  exponential backoff and another attempt; terminal raises immediately,
  and `answer()` turns that into a clear message instead of crashing on
  `None`. Same discipline as
  [`04-tool-use-schema-design/5_error_handling.py`](../04-tool-use-schema-design/5_error_handling.py)
  (mark a tool failure `is_error=True` so Claude can adapt instead of
  treating every failure alike) and
  [`19-multi-agent-orchestration/1_orchestrator_worker_tradeoff.py`](../19-multi-agent-orchestration/1_orchestrator_worker_tradeoff.py)'s
  `safe_worker()` (retry-with-backoff-then-fallback per subagent) —
  applied here to the top-level model call instead of a tool result or a
  subagent.
- **Fix 3** — `resolve_safe_write_path()` resolves the untrusted path
  against the workspace root and raises `PermissionError` if the result
  would land outside it — checked *before* `summarize()` ever spends a
  token on the malicious page. This is the in-code version of the
  `PreToolUse` hooks in
  [`13-packaging-workflows/packaging-demo/hooks`](../13-packaging-workflows/packaging-demo/hooks/hooks.json)
  and
  [`17-security-prompt-injection/guardrail-demo`](../17-security-prompt-injection/guardrail-demo),
  which deny a Claude Code tool call whose arguments escape an
  allow-listed directory, and the same shape as
  [`17-security-prompt-injection/1_indirect_prompt_injection.py`](../17-security-prompt-injection/1_indirect_prompt_injection.py)'s
  `is_allowed_recipient()` least-privilege check on `send_email`. All
  three enforce the boundary in code, deterministically, regardless of
  what the untrusted content asks for — this script just does it in the
  function that performs the write, since it drives its own tool
  execution instead of going through Claude Code's hook system.

**Key concept:** the three fixes are independent of each other — you
could ship any one without the others — which is exactly why a single
demo run showing all three defects is realistic. Production systems
don't fail one layer at a time just because your hardening work happened
one layer at a time.

## What's *not* re-demonstrated here

- **A real rate limit or a real 400** — both are simulated via injected
  exceptions (`SimulatedRateLimitError`, `SimulatedBadRequestError`), the
  same deterministic-failure approach used throughout this repo (e.g.
  [`04-tool-use-schema-design/5_error_handling.py`](../04-tool-use-schema-design/5_error_handling.py),
  [`19-multi-agent-orchestration/1_orchestrator_worker_tradeoff.py`](../19-multi-agent-orchestration/1_orchestrator_worker_tradeoff.py)).
  A real hardened version should also treat the SDK's own
  `anthropic.RateLimitError` / `APIStatusError` (5xx) as retriable and
  `anthropic.BadRequestError` / `AuthenticationError` /
  `PermissionDeniedError` as terminal.
- **An LLM-as-judge grader** for Fix 1 — the eval's three cases all have
  one correct short answer, so a code-graded substring check is the
  right tool per
  [`18-evals-and-judge`](../18-evals-and-judge/README.md)'s
  grader-selection guidance; nothing here is open-ended enough to need a
  judge.
