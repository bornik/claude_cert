"""
EXAMPLE 1: Evals and a Calibrated Judge — turning "looks right" into a
tracked score

Before this module, "done" meant trying a prompt by hand a few times and
eyeballing the output. An eval replaces that feeling with a number: a
fixed set of input cases, an expected behavior per case, and a grader
that scores each output against it. The number on its own isn't good or
bad — what matters is whether it moves when you change one thing at a
time.

This script builds the same tiny pipeline the lesson describes —
run_test_case() -> run_eval() — then reuses it across three demos, one
per grading method, because the right grader depends on the SHAPE of the
output, not on how hard the task feels:

  1. EXACT/STRING MATCH   — a support-ticket urgency classifier. There is
     exactly one correct label per ticket, so character comparison is
     cheap and sufficient.
  2. CODE-GRADED CHECK    — "list three capital cities" as JSON. There is
     no single correct STRING (the three cities can come back in any
     order), so exact match fails valid answers. A parse-then-check
     grader fixes that.
  3. LLM-AS-JUDGE         — a one-paragraph recommendation rationale.
     Quality here is open-ended; no code rule can check "did this cite
     the numbers it was given?" the way a second model prompted with a
     rubric can.

The script then does the two things that make a judge trustworthy instead
of decorative:

  - CALIBRATION: run the judge on outputs a human already scored, and
    measure how often the judge's score agrees with the human's. A judge
    nobody has checked against a human is just a confident-looking
    random number.
  - THE ITERATION LOOP: change ONE lever (the system prompt) and re-run
    the same eval, so the score's movement is attributable to that one
    change instead of several tangled ones.
"""

import json
import re
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

MODEL = "claude-haiku-4-5"


def ask(prompt: str, *, system: str | None = None, max_tokens: int = 300) -> str:
    kwargs = dict(model=MODEL, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}])
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    print_usage(response, model=MODEL)
    return next((b.text for b in response.content if b.type == "text"), "").strip()


# ---------------------------------------------------------------------------
# The eval pipeline itself — same shape regardless of task or grader.
# grade_fn may return a plain number (exact/code graders) or a dict with a
# "score" key plus reasoning (the judge) — run_test_case normalizes either.
# ---------------------------------------------------------------------------

def run_test_case(test_case: dict, run_fn, grade_fn) -> dict:
    """Run one case through the feature, then grade the result."""
    output = run_fn(test_case)
    grade = grade_fn(test_case, output)
    score = grade["score"] if isinstance(grade, dict) else grade
    return {"test_case": test_case, "output": output, "grade": grade, "score": score}


def run_eval(dataset: list, run_fn, grade_fn, label: str = "") -> tuple:
    """Run every case and report the average score."""
    results = [run_test_case(c, run_fn, grade_fn) for c in dataset]
    average = sum(r["score"] for r in results) / len(results)
    tag = f" ({label})" if label else ""
    print(f"\nAverage score{tag}: {average:.1f}/10")
    return results, average


# ---------------------------------------------------------------------------
# Demo 1 — Exact/string match: one correct label, zero ambiguity
# ---------------------------------------------------------------------------

URGENCY_DATASET = [
    {"ticket": "My card was charged twice for the same order, please refund immediately.", "expected": "high"},
    {"ticket": "Is there a dark mode planned for the mobile app?", "expected": "low"},
    {"ticket": "Production API keys stopped authenticating for all our users right now.", "expected": "high"},
    {"ticket": "Could you update the shipping address on an order I placed yesterday?", "expected": "medium"},
    {"ticket": "Just wanted to say the new dashboard redesign looks great.", "expected": "low"},
]

CLASSIFY_SYSTEM = (
    "Classify the support ticket's urgency as exactly one word: high, "
    "medium, or low. Reply with only that word, nothing else."
)


def run_classifier(case: dict) -> str:
    return ask(case["ticket"], system=CLASSIFY_SYSTEM, max_tokens=5)


def grade_exact_match(case: dict, output: str) -> int:
    return 10 if output.strip().lower() == case["expected"] else 0


def demo_exact_match():
    print("\n" + "=" * 70)
    print("1. Exact/string match — urgency classifier, one correct label")
    print("=" * 70)

    results, _ = run_eval(URGENCY_DATASET, run_classifier, grade_exact_match, label="urgency classifier")
    for r in results:
        mark = "✅" if r["score"] == 10 else "❌"
        print(f"  {mark} expected={r['test_case']['expected']:<6} got={r['output']!r:<10} "
              f"— {r['test_case']['ticket'][:55]}...")
    print(
        "\nThis grader costs nothing per case and runs in microseconds — "
        "fine here because the task has exactly one right answer. It would "
        "be the wrong tool the moment two phrasings could both be correct."
    )


# ---------------------------------------------------------------------------
# Demo 2 — Code-graded check: a structural rule, not one fixed string
# ---------------------------------------------------------------------------

CAPITALS_DATASET = [
    {
        "region": "the three Baltic states (Estonia, Latvia, Lithuania)",
        "expected_set": {"tallinn", "riga", "vilnius"},
    },
    {
        "region": "the three Benelux countries (Belgium, Netherlands, Luxembourg)",
        "expected_set": {"brussels", "amsterdam", "luxembourg"},
    },
]

CAPITALS_SYSTEM = (
    "Reply with ONLY a JSON array of three strings — the capital cities "
    "requested. No prose, no markdown fences, no explanation."
)


def run_capitals(case: dict) -> str:
    return ask(f"List the capital cities of {case['region']}.", system=CAPITALS_SYSTEM, max_tokens=100)


def grade_exact_string(case: dict, output: str) -> int:
    """What a naive eval reaches for first: compare against one hardcoded
    reference string. Fails the instant the model returns a correct
    answer in a different order."""
    reference = json.dumps(sorted(case["expected_set"]))
    return 10 if output.strip() == reference else 0


def grade_json_membership(case: dict, output: str) -> int:
    """Parses the output and checks the SET of cities, not their order or
    the surrounding characters — a structural rule instead of a fixed
    string."""
    try:
        cities = json.loads(output.strip())
    except json.JSONDecodeError:
        return 0
    if not isinstance(cities, list) or len(cities) != 3:
        return 0
    got = {str(c).strip().lower() for c in cities}
    return 10 if got == case["expected_set"] else 0


def demo_code_graded():
    print("\n" + "=" * 70)
    print("2. Code-graded check — same outputs, two graders, different verdicts")
    print("=" * 70)

    for case in CAPITALS_DATASET:
        output = run_capitals(case)
        exact_score = grade_exact_string(case, output)
        struct_score = grade_json_membership(case, output)
        print(f"\nRegion: {case['region']}")
        print(f"  Output: {output}")
        print(f"  Exact-string grader:   {exact_score}/10 "
              f"{'(passed)' if exact_score else '(FAILED — order or formatting differs from the reference string)'}")
        print(f"  JSON-membership grader: {struct_score}/10 "
              f"{'(passed — all three cities present, order irrelevant)' if struct_score else '(FAILED — wrong or malformed content)'}")
    print(
        "\nBoth graders looked at the identical model output. The exact-"
        "string grader penalizes a correct answer for being ordered "
        "differently than the one reference string it was written against; "
        "the code grader validates the STRUCTURE (valid JSON, three items, "
        "the right set) and doesn't care about order. This is the class of "
        "failure a code-graded check exists to avoid."
    )


# ---------------------------------------------------------------------------
# Demo 3, 4, 5 — LLM-as-judge: open-ended quality, calibration, iteration
# ---------------------------------------------------------------------------

RECOMMENDATION_DATASET = [
    {"task": "Recommend caching or not for an endpoint hit 5000 times/minute where the underlying data changes every 24 hours."},
    {"task": "Recommend caching or not for an endpoint hit 3 times/day where the underlying data changes every 30 seconds."},
    {"task": "Recommend synchronous or asynchronous processing for a report that renders a 50-page PDF and takes 4 minutes."},
]

BARE_SYSTEM = "Answer the question."

IMPROVED_SYSTEM = (
    "Answer in one paragraph. State your recommendation first, then justify "
    "it by citing the specific numbers given in the question (request "
    "rate, data-change interval, or processing time). Do not give a "
    "generic answer that would apply regardless of which numbers were given."
)


def make_run_fn(system: str):
    def run_fn(case: dict) -> str:
        return ask(case["task"], system=system, max_tokens=200)
    return run_fn


def grade_by_model(case: dict, output: str) -> dict:
    eval_prompt = f"""
You are an expert reviewer. Evaluate the solution for the task.
Task: {case['task']}
Solution: {output}

Return ONLY JSON with:
  "strengths":  array of 1-3 points
  "weaknesses": array of 1-3 points
  "reasoning":  a one to two sentence explanation, 50 words maximum
  "score":      a number from 1 to 10 — 10 means the answer states a
                clear recommendation AND justifies it using the specific
                numbers given in the task; 1 means a generic answer that
                ignores those numbers entirely.
"""
    raw = ask(eval_prompt, max_tokens=300)
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"strengths": [], "weaknesses": [], "reasoning": "judge output did not parse as JSON", "score": 0}


def demo_llm_judge():
    print("\n" + "=" * 70)
    print("3. LLM-as-judge — open-ended rationale, no code rule can grade this")
    print("=" * 70)

    for case in RECOMMENDATION_DATASET:
        output = ask(case["task"], system=BARE_SYSTEM, max_tokens=200)
        grade = grade_by_model(case, output)
        print(f"\nTask: {case['task']}")
        print(f"  Answer: {output}")
        print(f"  Score: {grade['score']}/10 — {grade['reasoning']}")
        print(f"  Strengths: {grade['strengths']}")
        print(f"  Weaknesses: {grade['weaknesses']}")
    print(
        "\nNotice the judge is asked for strengths/weaknesses/reasoning "
        "BEFORE the score. Ask for the score alone and models tend to "
        "drift to a safe middle number regardless of quality — reasoning "
        "first is what anchors the number to something specific."
    )


# Outputs a human already scored, paired with the score they gave. This
# stands in for "someone on the team hand-labeled these" — the set the
# judge gets calibrated against, not generated live.
CALIBRATION_DATASET = [
    {
        "task": RECOMMENDATION_DATASET[0]["task"],
        "output": "Cache it. At 5000 requests/minute against data that only "
                   "changes every 24 hours, an uncached endpoint would "
                   "recompute an unchanged result thousands of times between "
                   "updates.",
        "human_score": 9,
    },
    {
        "task": RECOMMENDATION_DATASET[0]["task"],
        "output": "It depends on your infrastructure and requirements; "
                   "caching can help performance in many systems.",
        "human_score": 2,
    },
    {
        "task": RECOMMENDATION_DATASET[1]["task"],
        "output": "Don't cache — at 3 requests/day against data that "
                   "changes every 30 seconds, a cache would almost always "
                   "be serving stale data.",
        "human_score": 9,
    },
    {
        "task": RECOMMENDATION_DATASET[1]["task"],
        "output": "Caching is generally a good idea for improving "
                   "performance and reducing load.",
        "human_score": 1,
    },
    {
        "task": RECOMMENDATION_DATASET[2]["task"],
        "output": "Process it asynchronously and email the result — a "
                   "4-minute render would block or time out a synchronous "
                   "request/response cycle.",
        "human_score": 8,
    },
]


def demo_calibrate_judge():
    print("\n" + "=" * 70)
    print("4. Calibrating the judge — does it agree with a human?")
    print("=" * 70)
    print(
        "A judge score is not evidence until it's been checked against a "
        "human on cases where the right answer is already known.\n"
    )

    agreements = 0
    for case in CALIBRATION_DATASET:
        grade = grade_by_model(case, case["output"])
        diff = abs(grade["score"] - case["human_score"])
        agrees = diff <= 2
        agreements += agrees
        mark = "✅ agree" if agrees else "❌ disagree"
        print(f"  human={case['human_score']} judge={grade['score']} (Δ{diff}) {mark} — {grade['reasoning']}")

    rate = agreements / len(CALIBRATION_DATASET)
    print(f"\nAgreement rate (within 2 points): {rate:.0%}")
    if rate < 0.8:
        print(
            "Below 80% — the rubric needs work before these scores can be "
            "trusted: tighten what each end of the scale means, add a "
            "worked good/bad example to the prompt, then re-measure."
        )
    else:
        print("80%+ agreement — calibrated enough to trust for tracking a score over time.")


def demo_prompt_iteration_loop():
    print("\n" + "=" * 70)
    print("5. The iteration loop — change one lever, re-run, compare")
    print("=" * 70)

    print("\n-- Bare system prompt --")
    bare_results, bare_avg = run_eval(
        RECOMMENDATION_DATASET, make_run_fn(BARE_SYSTEM), grade_by_model, label="bare prompt"
    )
    for r in bare_results:
        print(f"  [{r['score']:>2}/10] {r['test_case']['task'][:60]}...")

    print("\n-- Improved system prompt (only change: the system prompt) --")
    improved_results, improved_avg = run_eval(
        RECOMMENDATION_DATASET, make_run_fn(IMPROVED_SYSTEM), grade_by_model, label="improved prompt"
    )
    for r in improved_results:
        print(f"  [{r['score']:>2}/10] {r['test_case']['task'][:60]}...")

    print(f"\nOne lever changed (system prompt only): {bare_avg:.1f}/10 -> {improved_avg:.1f}/10")
    if improved_avg > bare_avg:
        verdict = "The score went up — evidence the format/citation constraint helped, not just a guess."
    elif improved_avg < bare_avg:
        verdict = "The score went DOWN — evidence this particular change hurt, worth reverting rather than keeping on a hunch."
    else:
        verdict = (
            "The score didn't move. That's information too: a capable model "
            "may already do what the improved prompt asked for even under "
            "the bare one, so the bottleneck is elsewhere — read the "
            "per-case output above (e.g. truncated answers) for where to "
            "look next, rather than assuming this lever was the right one."
        )
    print(
        f"{verdict} Because exactly one thing changed between the two runs, "
        "that result is attributable to this change specifically. If the "
        "model, the prompt, and max_tokens had all changed at once, this "
        "average couldn't tell you which change caused it — or whether one "
        "change helped while another quietly hurt."
    )


def main():
    demo_exact_match()
    demo_code_graded()
    demo_llm_judge()
    demo_calibrate_judge()
    demo_prompt_iteration_loop()

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(
        "Three graders, chosen by the shape of the output, not the task's "
        "difficulty: exact match for the classifier's one correct label, a "
        "code check for the capitals task's structural rule, and a judge "
        "for the rationale task's open-ended quality. The judge only "
        "became trustworthy after being checked against human scores on "
        "known cases — before that, its number looked rigorous but meant "
        "nothing. And the only reason the prompt-iteration run's score "
        "movement is meaningful is that exactly one lever changed between "
        "the two calls to run_eval()."
    )


if __name__ == "__main__":
    main()
