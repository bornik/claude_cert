# Module 18 — Defining Done Before You Ship: Evals & a Calibrated Judge

Before this module, "done" means a feature was tried by hand a few times
and looked right. An eval replaces that feeling with a number: a fixed
set of input cases, an expected behavior per case, and a grader that
scores each output against it. The number by itself isn't good or bad —
what matters is whether it moves as the prompt, the tools, or the model
change.

## Files

```
18-evals-and-judge/
├── README.md
├── example-design-doc.md
└── 1_eval_pipeline_and_graders.py
```

### 0️⃣ `example-design-doc.md`

Not a script — a filled-in example of the four decisions the lesson says
to write down *before* implementation (success criteria, failure
handling, cost/latency budget, trust boundary), for the exact classifier
demo 1 of the script below evaluates. Read this first: the eval's
dataset, the error-handling table, and the tool footprint all trace back
to this one page.

### 1️⃣ `1_eval_pipeline_and_graders.py`

```bash
uv run 18-evals-and-judge/1_eval_pipeline_and_graders.py
```

**What it does:** builds the same minimal pipeline the lesson describes —
`run_test_case()` runs one case and grades it, `run_eval()` runs a whole
dataset and averages the scores — then reuses it across five demos:

1. **Exact/string match** — a support-ticket urgency classifier
   (`high`/`medium`/`low`). One correct label per ticket, so character
   comparison is cheap and sufficient.
2. **Code-graded check** — "list the three capital cities of a region" as
   JSON. The *same* model output is scored by two graders side by side:
   an exact-string grader (fails the instant the cities come back in a
   different order than one hardcoded reference) and a parse-then-check
   grader (passes because it validates the JSON structure and the set of
   cities, not their order).
3. **LLM-as-judge** — a one-paragraph "cache or not?" recommendation,
   graded by a second model call asked for strengths, weaknesses, and
   reasoning *before* a 1–10 score, per `grade_by_model()`.
4. **Calibrating the judge** — the same judge is run against five
   pre-written outputs that already carry a human-assigned score, and the
   script reports how often the judge's score lands within 2 points of
   the human's.
5. **The iteration loop** — the recommendation task is run twice, with
   exactly one change between runs (a bare system prompt vs. one that
   demands citing the numbers given), so whatever the score does —
   improves, drops, or holds flat — is attributable to that one change
   and not to several tangled ones.

**Key concepts:**
- The grader follows from the output's shape, not the task's difficulty.
  A classifier with one correct label (demo 1) doesn't need a judge; an
  open-ended rationale (demo 3) can't be graded any other way. Reaching
  for a judge when a code check would do adds cost and noise for no gain
  — reaching for exact match on an open-ended answer fails valid
  paraphrases.
- Demo 2 makes the "exact match is the wrong tool for anything
  open-ended" point concrete with one output scored two ways: the
  exact-string grader marks a fully correct answer as a failure purely
  because of ordering; the code-graded check marks the same output
  correct because it checks the *set*, not the *string*.
- `grade_by_model()` asks for `strengths`/`weaknesses`/`reasoning` before
  `score`. Ask a model to grade without that scaffolding and it tends to
  drift toward a safe middle number regardless of quality — reasoning
  first is what anchors the score to something specific in the output.
- A judge is not evidence until demo 4 checks it against human labels.
  An agreement rate below ~80% means the rubric needs work (tighten what
  each end of the scale means, add a worked good/bad example) before any
  score it produces should be trusted for tracking a regression.
- Demo 5's two `run_eval()` calls differ in exactly one input — the
  system prompt. That discipline is what makes whatever the average does
  next a causal claim instead of a coincidence, including a *flat*
  result: on a capable model, the bare prompt can already score close to
  the improved one, which is itself useful information (the bottleneck
  is elsewhere, not this lever) rather than a failed demo. Changing the
  prompt, the model, and `max_tokens` together in one pass would leave
  you unable to say which change moved the number, or whether one change
  helped while another quietly hurt.
- The per-case printout under each `run_eval()` call matters as much as
  the average — a steady average can hide a change that fixed three
  cases and broke three others. Reading which specific case failed, and
  why (a formatting miss vs. a factual miss vs. an instruction-following
  miss), is what turns a low score into a targeted next fix instead of a
  guess.

## What's *not* re-demonstrated here

- **Judge-generated eval cases from a small labeled seed set** — the
  lesson mentions having Claude generate additional cases from a few
  hand-labeled ones and spot-checking them; this script's datasets are
  small and hand-written on purpose, to keep every case's expected
  behavior legible at a glance rather than demonstrating the generation
  step itself.
- **Adversarial or refuter-style judge panels** (multiple judges voting,
  one prompted to argue against a finding) — demo 4 calibrates a single
  judge against human labels, which is the prerequisite the lesson asks
  for; running several judges in parallel is a further step this module
  doesn't cover.
