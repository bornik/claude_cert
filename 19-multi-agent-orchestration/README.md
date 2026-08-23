# Module 19 — Multi-Agent Orchestration as a Deliberate Tradeoff

An orchestrator-worker pattern is a hiring decision, not a free upgrade:
a lead agent decomposes a task and hands slices to several subagents
that each spend their own tokens in their own context, running in
parallel, before the lead compiles what they found. This module measures
that tradeoff with real API calls instead of taking the ~15x multiplier
on faith.

## Files

```
19-multi-agent-orchestration/
├── README.md
└── 1_orchestrator_worker_tradeoff.py
```

### 1️⃣ `1_orchestrator_worker_tradeoff.py`

```bash
uv run 19-multi-agent-orchestration/1_orchestrator_worker_tradeoff.py
```

**What it does:** implements the pattern's three pieces —
`lead_plan()` decomposes a task, `worker_run_grounded()` researches one
subtopic, `lead_synthesize()` compiles the findings, wired together in
`orchestrate()` exactly as the lesson's pseudocode shows (`plan` ->
`asyncio.gather(...)` -> `synthesize`) — then runs four demos:

1. **Genuine parallel task** — a broad survey question (compare four
   backend-scaling techniques) run as a single agent vs. the full
   orchestrator-worker pipeline, same model throughout so only the
   architecture's cost is being measured. A sample run showed **5.1x**
   more tokens for the multi-agent version.
2. **Wasted multiplier** — the identical pipeline forced onto a single
   factual lookup ("What year was HTTP/2 published?"). Same architecture,
   same cost shape (**21.9x** more tokens in a sample run), but the
   answer is no better than the one-call version — the decomposition
   step invents subtopics because it was told to, not because the
   question needed them.
3. **Model tiering** — the genuine survey task again, comparing an
   all-`claude-sonnet-5` assignment against a `claude-sonnet-5` lead with
   `claude-haiku-4-5` workers. The tiered run cut cost by roughly a third
   in testing, without touching the two calls where coordination quality
   matters (decomposition and synthesis).
4. **Failure handling under fan-out** — one subagent simulates a
   transient rate limit on its first attempt. A naive
   `asyncio.gather()` with no per-task handling propagates the exception
   before synthesis ever runs — and the script explicitly drains the
   sibling tasks afterward to show they finished anyway, their tokens
   spent on results nobody uses. A second run wraps each subagent in its
   own retry-with-backoff-then-fallback, so the fan-out survives and the
   lead synthesizes from three real findings plus one recovered-after-
   retry finding.

**Key concepts:**
- Demos 1 and 2 hold the model constant on purpose, so the measured
  multiplier reflects the *architecture* (paying for a plan call + N
  worker calls + a synthesis call instead of one) rather than a
  model-choice decision — that's demo 3's variable instead.
- The lead's decomposition prompt insists each subtopic be
  **self-contained** — no subtopic may say "these four techniques" and
  assume a subagent can see the original task or the other subtopics.
  An earlier version of this script skipped that instruction and one
  subagent, seeing only a vague meta-question, answered about an
  unrelated domain entirely (ML model-compression techniques instead of
  backend scaling) — a concrete illustration of why subagents need
  grounding, not just a task to do. `worker_run_grounded()` adds a second
  layer of defense by also passing the original task alongside the
  subtopic.
- Demo 2's forced decomposition is the concrete version of the lesson's
  warning: "if the question was a single lookup dressed up as research,
  you paid the multiplier for nothing." The script doesn't assert this —
  it measures both runs and lets the token counts and the (identical)
  correct answer make the point.
- Demo 3 demonstrates the lesson's model-choice tip directly: routing the
  plan/synthesize calls to the stronger model while downgrading the
  parallel lookups, rather than paying frontier-model rates for every
  context.
- Demo 4's naive path uses `asyncio.create_task()` explicitly (rather
  than relying on `gather()` to schedule the coroutines) so the sibling
  tasks can be located and drained after the exception propagates —
  without that, their `print_usage()` output would leak into whatever
  ran next, muddying which section spent which tokens. `asyncio.gather()`
  does **not** cancel sibling tasks when one raises; they keep running
  and keep costing tokens whether or not anything is left to use their
  result.
- The retry-then-fallback in `safe_worker()` mirrors the retriable-vs-
  terminal failure handling from
  [`18-evals-and-judge/example-design-doc.md`](../18-evals-and-judge/example-design-doc.md):
  a transient error gets a backoff and a second attempt; only after
  attempts are exhausted does the subagent degrade to a placeholder
  finding, and only then does the lead proceed with a
  slightly-degraded-but-complete synthesis instead of no answer at all.

## What's *not* re-demonstrated here

- **Real rate limits or network failures** — `SimulatedRateLimitError` is
  injected in code so the failure is deterministic and reproducible on
  every run, the same approach
  [`04-tool-use-schema-design/5_error_handling.py`](../04-tool-use-schema-design/5_error_handling.py)
  uses for a hardcoded failed tool result instead of waiting for a real
  one.
- **Full adversarial/refuter-style multi-agent review** (independent
  judges voting on the same output) — this module's subagents each own a
  disjoint slice of the task; a panel of subagents redundantly checking
  the *same* claim is a different pattern, covered conceptually in the
  lesson but not built here.
