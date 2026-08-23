"""
EXAMPLE 2: The Hardened Agent — same three layers, each fixed

Same `answer()` shape as 1_buggy_agent.py, same three layers, one fix
per layer:

  1. EVAL/TEST LAYER — `run_eval()` replaces "run it and eyeball it" with
     a small dataset, an expected behavior per case, and a code-graded
     check, in the same run_test_case()/run_eval() shape as
     18-evals-and-judge/1_eval_pipeline_and_graders.py. It runs once as a
     gate before the rest of the demo, the way it would run before a real
     ship.
  2. ERROR-HANDLING/COST LAYER — `call_with_backoff()` classifies each
     failure as retriable or terminal before deciding what to do: a
     retriable error gets exponential backoff and another attempt; a
     terminal error is raised immediately, without wasting the remaining
     attempts on something that could never succeed. Compare
     04-tool-use-schema-design/5_error_handling.py (marking a tool result
     is_error=True so Claude can adapt) and
     19-multi-agent-orchestration/1_orchestrator_worker_tradeoff.py's
     safe_worker() (retry-with-backoff-then-fallback per subagent) — same
     retriable-vs-terminal discipline, applied here to the top-level model
     call instead of a tool result or a subagent.
  3. SECURITY/GUARDRAIL LAYER — `resolve_safe_write_path()` resolves the
     untrusted suggested_path against the workspace root and refuses
     anything that would land outside it. This is the in-code equivalent
     of the PreToolUse hooks in
     13-packaging-workflows/packaging-demo/hooks and
     17-security-prompt-injection/guardrail-demo, which deny a Claude Code
     tool call whose arguments escape an allow-listed directory — the
     same boundary, enforced in the function that performs the write
     instead of in a hook, because this script drives its own tool
     execution rather than Claude Code's.
"""

import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 150

WORKSPACE = Path(tempfile.mkdtemp(prefix="agent_workspace_"))
SIMULATED_SENSITIVE_AREA = Path(tempfile.mkdtemp(prefix="sensitive_area_"))
(WORKSPACE / "input").mkdir()
(WORKSPACE / "input" / "notes").write_text("Prior session notes: user prefers concise summaries.")


class Page:
    def __init__(self, url: str, text: str, suggested_path: str):
        self.url = url
        self.text = text
        self.suggested_path = suggested_path


def fetch(url: str, *, malicious: bool = False) -> Page:
    suggested_path = (
        f"../{SIMULATED_SENSITIVE_AREA.name}/exfiltrated_summary.txt"
        if malicious
        else "reports/infra-summary.txt"
    )
    return Page(
        url=url,
        text=(
            "Quarterly infra update: the team migrated the async job "
            "queue to Kafka and rolled out read replicas for the "
            "reporting database."
        ),
        suggested_path=suggested_path,
    )


def read_file(path) -> str:
    return Path(path).read_text()


def write_file(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"   wrote to: {path}")


def summarize(page: Page) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": f"Summarize in one sentence:\n\n{page.text}"}],
    )
    print_usage(response, model=MODEL)
    return next((b.text for b in response.content if b.type == "text"), "")


def msg(question: str) -> list:
    return [{"role": "user", "content": question}]


# ---------------------------------------------------------------------------
# Fix 3 — security/guardrail layer: a write-boundary check
# ---------------------------------------------------------------------------

def resolve_safe_write_path(root: Path, requested: str) -> Path:
    root = root.resolve()
    candidate = (root / requested).resolve()
    if candidate != root and root not in candidate.parents:
        raise PermissionError(f"refusing to write to {candidate} — outside the workspace root {root}")
    return candidate


# ---------------------------------------------------------------------------
# Fix 2 — error-handling/cost layer: classify before you retry
# ---------------------------------------------------------------------------

class SimulatedRateLimitError(Exception):
    """Stands in for a real 429 — retriable, worth a backoff and another try."""


class SimulatedBadRequestError(Exception):
    """Stands in for a real 400 — terminal, retrying can't fix a bad request."""


RETRIABLE = (SimulatedRateLimitError,)
TERMINAL = (SimulatedBadRequestError,)


def call_with_backoff(call_fn, max_attempts: int = 5):
    for attempt in range(1, max_attempts + 1):
        try:
            return call_fn()
        except TERMINAL as e:
            print(f"   attempt {attempt}: terminal error ({e}) — not retrying")
            raise
        except RETRIABLE as e:
            if attempt == max_attempts:
                print(f"   attempt {attempt}: retriable error ({e}) — attempts exhausted")
                raise
            backoff = min(0.2 * (2 ** (attempt - 1)), 2.0) + random.uniform(0, 0.1)
            print(f"   attempt {attempt}: retriable error ({e}) — backing off {backoff:.2f}s")
            time.sleep(backoff)


def answer(question: str, page_url: str, *, malicious_page: bool = False, call_fn=None) -> str:
    page = fetch(page_url, malicious=malicious_page)  # still untrusted content

    notes = read_file(WORKSPACE / "input" / "notes")
    target = resolve_safe_write_path(WORKSPACE, page.suggested_path)  # FIX 3
    write_file(target, summarize(page))

    call_fn = call_fn or (
        lambda: client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=msg(question))
    )

    try:
        resp = call_with_backoff(call_fn)  # FIX 2
    except TERMINAL as e:
        return f"Could not answer — the request was rejected and retrying would not help ({e})."
    except RETRIABLE as e:
        return f"Could not answer — still rate-limited after retrying with backoff ({e})."

    return resp.content[0].text


# ---------------------------------------------------------------------------
# Fix 1 — eval/test layer: a real, if small, regression gate
# ---------------------------------------------------------------------------

EVAL_DATASET = [
    {"question": "What is the capital of France? Answer with just the city name.", "expected_substring": "paris"},
    {"question": "What does HTTP stand for? Answer in a short phrase.", "expected_substring": "hypertext transfer protocol"},
    {"question": "What color is a clear daytime sky? Answer with one word.", "expected_substring": "blue"},
]


def grade_contains(case: dict, output: str) -> int:
    return 10 if case["expected_substring"] in output.lower() else 0


def run_eval() -> float:
    print("\n" + "=" * 70)
    print("Fix 1 — a real eval gate, in place of 'run it and eyeball it'")
    print("=" * 70)
    scores = []
    for case in EVAL_DATASET:
        output = answer(case["question"], "https://example.com/infra-update")
        score = grade_contains(case, output)
        scores.append(score)
        mark = "✅" if score == 10 else "❌"
        print(f"  {mark} [{score:>2}/10] Q: {case['question']!r} -> {output.strip()[:70]!r}")
    average = sum(scores) / len(scores)
    print(f"\nEval average: {average:.1f}/10 over {len(scores)} cases")
    return average


def demo_error_handling_fix():
    print("\n" + "=" * 70)
    print("Fix 2 — classify before you retry")
    print("=" * 70)

    print("\n-- Retriable case: 2 simulated rate limits, then success --")
    state = {"n": 0}

    def flaky_retriable():
        state["n"] += 1
        if state["n"] <= 2:
            raise SimulatedRateLimitError("simulated 429: rate limit exceeded")
        return client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=msg("Say hello in one word."))

    text = answer("Say hello in one word.", "https://example.com/infra-update", call_fn=flaky_retriable)
    print(f"Result: {text!r}")
    print("Backed off between attempts instead of hammering the limit at zero delay.")

    print("\n-- Terminal case: fails once, fails fast, no wasted attempts --")

    def always_terminal():
        raise SimulatedBadRequestError("simulated 400: invalid request — retrying will never fix this")

    text = answer("Say hello in one word.", "https://example.com/infra-update", call_fn=always_terminal)
    print(f"Result: {text!r}")
    print("One attempt, a clear message back to the caller — no crash, no 5x wasted latency.")


def demo_security_fix():
    print("\n" + "=" * 70)
    print("Fix 3 — the write-boundary guardrail")
    print("=" * 70)

    print("\n-- Legitimate suggested_path: allowed --")
    answer("What migration did the infra team complete?", "https://example.com/infra-update", malicious_page=False)

    print("\n-- Malicious suggested_path (path traversal): blocked --")
    try:
        answer("What migration did the infra team complete?", "https://example.com/infra-update", malicious_page=True)
    except PermissionError as e:
        print(f"🛡️  Blocked at the guardrail: {e}")

    escaped = list(SIMULATED_SENSITIVE_AREA.iterdir())
    print(f"\nFiles that landed outside the workspace: {escaped} (should be empty)")


def main():
    try:
        run_eval()
        demo_error_handling_fix()
        demo_security_fix()

        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print(
            "Same function, same three layers, one fix each: a real eval "
            "gates every change instead of a human eyeballing output, the "
            "retry path spends its attempts only where they can help and "
            "fails fast otherwise, and the write boundary makes the "
            "exfiltration attempt structurally impossible regardless of "
            "what path the untrusted page suggests."
        )
    finally:
        shutil.rmtree(WORKSPACE, ignore_errors=True)
        shutil.rmtree(SIMULATED_SENSITIVE_AREA, ignore_errors=True)


if __name__ == "__main__":
    main()
