"""
EXAMPLE 1: The Buggy Agent — three planted defects, one per production layer

Real production failures rarely arrive one layer at a time. This script
runs the lesson's `answer()` function close to verbatim, with its three
planted defects intact, one per layer this whole course has hardened
separately:

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

  1. EVAL/TEST LAYER    — there is no eval. `main()` below runs `answer()`
     a few times and prints the output for a human to eyeball, which is
     exactly how the lesson describes the buggy version being "tested."
     Nothing here would catch a regression if the prompt or model changed.
  2. ERROR-HANDLING/COST LAYER — the retry loop catches bare `Exception`
     and retries identically, instantly (`time.sleep(0)`), whether the
     failure is retriable (a rate limit) or terminal (a bad request that
     will never succeed no matter how many times it's retried).
  3. SECURITY/GUARDRAIL LAYER — `write_file(page.suggested_path, ...)`
     writes to a path taken from `page`, which came from `fetch()` —
     untrusted, attacker-controlled content. Nothing stops that path from
     escaping the intended workspace.

Each defect below is demonstrated in isolation, in a fully sandboxed
temp workspace, so the vulnerable write path can be run for real without
ever touching a real filesystem location outside this script's own temp
directories.
"""

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


def fetch(url: str) -> Page:
    """Stands in for an HTTP fetch. `suggested_path` is attacker-controlled
    -- it comes from the fetched page, the way a crafted filename or a
    frontmatter field in a scraped page could be. It escapes WORKSPACE via
    '..' and lands in SIMULATED_SENSITIVE_AREA, a temp directory this
    script owns for the demo -- nothing here ever touches a real system
    path, so the vulnerable code path below is safe to actually execute."""
    return Page(
        url=url,
        text=(
            "Quarterly infra update: the team migrated the async job "
            "queue to Kafka and rolled out read replicas for the "
            "reporting database."
        ),
        suggested_path=f"../{SIMULATED_SENSITIVE_AREA.name}/exfiltrated_summary.txt",
    )


def read_file(path) -> str:
    return Path(path).read_text()


def write_file(path, content: str) -> None:
    Path(path).write_text(content)
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


class SimulatedRateLimitError(Exception):
    """Stands in for a real 429 -- retrying this after a wait is correct."""


class SimulatedBadRequestError(Exception):
    """Stands in for a real 400 -- retrying this is never going to help."""


def answer(question: str, page_url: str, call_fn=None) -> str:
    page = fetch(page_url)  # untrusted content

    notes = read_file(WORKSPACE / "input" / "notes")
    target = WORKSPACE / page.suggested_path  # DEFECT 3: no boundary check
    write_file(target, summarize(page))

    call_fn = call_fn or (
        lambda: client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=msg(question))
    )

    resp = None
    for i in range(5):  # DEFECT 2: no retriable/terminal distinction, no backoff
        try:
            resp = call_fn()
            break
        except Exception as e:
            print(f"   attempt {i + 1} failed ({e.__class__.__name__}: {e}); retrying immediately")
            time.sleep(0)

    return resp.content[0].text  # crashes with AttributeError if every attempt failed


def demo_security_defect():
    print("\n" + "=" * 70)
    print("Defect 3 — security/guardrail layer: unbounded write_file path")
    print("=" * 70)
    print(f"\nWorkspace root: {WORKSPACE}")
    print(f"'Sensitive area' this run should never be able to reach: {SIMULATED_SENSITIVE_AREA}")

    answer("What migration did the infra team complete?", "https://example.com/infra-update")

    written = list(SIMULATED_SENSITIVE_AREA.iterdir())
    if written:
        print(f"\n🚨 The untrusted page's suggested_path escaped the workspace: {written[0]}")
        print("Nothing in write_file() checked that the resolved path stayed inside WORKSPACE.")


def demo_eval_defect():
    print("\n" + "=" * 70)
    print("Defect 1 — eval/test layer: 'success' is three manual reads")
    print("=" * 70)
    print(
        "\nNo dataset, no expected outputs, no grader. The only signal "
        "this loop produces is a human reading the printed text below "
        "and deciding it 'looks right' -- exactly what the lesson calls "
        "out as having nothing to fail a regression against."
    )
    for question in ["What is 2 + 2?", "Name the largest planet in our solar system."]:
        text = answer(question, "https://example.com/infra-update")
        print(f"  Q: {question}\n  A: {text}\n")


def demo_error_handling_defect():
    print("\n" + "=" * 70)
    print("Defect 2 — error-handling/cost layer: retry blind to error type")
    print("=" * 70)

    print("\n-- Retriable case: 2 simulated rate limits, then success --")
    state = {"n": 0}

    def flaky_retriable():
        state["n"] += 1
        if state["n"] <= 2:
            raise SimulatedRateLimitError("simulated 429: rate limit exceeded")
        return client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=msg("Say hello in one word."))

    text = answer("Say hello in one word.", "https://example.com/infra-update", call_fn=flaky_retriable)
    print(f"Eventually succeeded: {text!r}")
    print(
        "It got there, but each retry fired instantly (time.sleep(0)) -- "
        "against a real rate limit, hammering it with zero delay deepens "
        "the limit instead of letting it clear."
    )

    print("\n-- Terminal case: every attempt fails the same way, and always will --")

    def always_terminal():
        raise SimulatedBadRequestError("simulated 400: invalid request — retrying will never fix this")

    try:
        answer("Say hello in one word.", "https://example.com/infra-update", call_fn=always_terminal)
    except AttributeError as e:
        print(f"❌ Crashed after burning all 5 attempts on an error that could never succeed: {e}")
        print(
            "The loop can't tell a 400 from a 429, so it spends the same "
            "5 instant retries on a request that was never going to work, "
            "then crashes on `resp.content` because `resp` is still None "
            "-- no clear error ever reaches the caller."
        )


def main():
    try:
        demo_eval_defect()
        demo_error_handling_defect()
        demo_security_defect()

        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print(
            "Three defects, three layers, one function: no eval to catch a "
            "regression, a retry loop that can't tell a wait-and-succeed "
            "failure from a never-going-to-work one, and a write target "
            "trusted straight from attacker-controlled content. See "
            "2_hardened_agent.py for the fix to each."
        )
    finally:
        shutil.rmtree(WORKSPACE, ignore_errors=True)
        shutil.rmtree(SIMULATED_SENSITIVE_AREA, ignore_errors=True)


if __name__ == "__main__":
    main()
