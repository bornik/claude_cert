"""
EXAMPLE 2: Choosing the Right Memory Scope — and What Happens When You Don't

Reproduces the certification checkpoint's three use cases and matches each
to its correct memory scope, live:

  1. A support agent assisting the SAME user across multiple days.
     Wrong scope: in-context (each session starts fresh, state is lost).
     Right scope: external storage (write state at session end, read it
     back at session start).
  2. A document formatter that runs independent, one-shot jobs.
     Right scope: stateless (no persistence needed — nothing to carry).
  3. A coding assistant working one long session that never continues.
     Right scope: in-context (external storage would be pure overhead for
     a session that ends when the developer logs off).

The postmortem this reproduces: "in-context" isn't wrong in general — it's
wrong for use case 1 and right for use case 3. The failure mode from the
lesson (a session-four agent that filled its context window) comes from
using in-context memory for a MULTI-SESSION use case: naively re-supplying
growing history every session inflates input tokens session over session,
until it eats the budget before the first tool call. This script measures
that growth directly via input_tokens, then shows external storage holding
input tokens flat across the same number of sessions.
"""

import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

MODEL = "claude-haiku-4-5"

# Each day's check-in adds real content — a naive in-context implementation
# just keeps appending these to one growing messages[] list across "sessions."
DAILY_CHECKINS = [
    "Day 1: My invoice #4471 shows a charge for a plan I cancelled last month. Can you look into it?",
    "Day 2: Following up on invoice #4471 — support said it'd be refunded within 3-5 business days, still waiting.",
    "Day 3: Refund for #4471 finally landed, thanks. Separate issue now: my API key stopped authenticating this morning.",
    "Day 4: The API key issue turned out to be an expired key — rotated it myself. New question: can I get a spending alert at 80% of my monthly quota?",
]


def demo_in_context_across_sessions():
    """WRONG scope for use case 1: naively treats every day's check-in as
    more turns in the same list. Input tokens climb session over session
    because the full history is resent every time — the exact 'session
    four' failure shape from the postmortem."""
    print("\n" + "=" * 70)
    print("WRONG SCOPE FOR USE CASE 1: in-context memory across daily sessions")
    print("=" * 70)

    messages = []
    for day, checkin in enumerate(DAILY_CHECKINS, start=1):
        messages.append({"role": "user", "content": checkin})
        response = client.messages.create(model=MODEL, max_tokens=150, messages=messages)
        print(f"\n--- 'Session' {day} (really: turn {day} of one giant list) ---")
        print_usage(response)
        messages.append({"role": "assistant", "content": response.content})

    print("\n📝 input_tokens climbed every session because the FULL prior history")
    print("   (every earlier check-in, verbatim) got resent as part of the same")
    print("   messages[] list — this is what 'session four' looks like at scale.")


def demo_external_storage_across_sessions():
    """RIGHT scope for use case 1: each day is a genuinely fresh messages[]
    list. Only a small stored STATE string (what a database would return)
    is injected via the system prompt. Input tokens stay roughly flat
    across sessions instead of climbing."""
    print("\n" + "=" * 70)
    print("RIGHT SCOPE FOR USE CASE 1: external storage, re-injected each session")
    print("=" * 70)

    stored_state = ""  # what our fake "database" holds between sessions
    for day, checkin in enumerate(DAILY_CHECKINS, start=1):
        system_prompt = (
            f"Known case state from prior sessions (from storage): {stored_state}"
            if stored_state
            else "No prior case state stored yet."
        )
        response = client.messages.create(
            model=MODEL,
            max_tokens=150,
            system=system_prompt,
            messages=[{"role": "user", "content": checkin}],  # fresh list every session
        )
        print(f"\n--- Session {day} (fresh messages[], stored state re-injected) ---")
        print_usage(response)

        # Our code condenses this session down to a short state update and
        # writes it back to "storage" — NOT the full conversation text.
        stored_state = f"Day {day} summary: {checkin[:60]}..."

    print("\n📝 input_tokens stayed roughly flat session over session — each session")
    print("   only paid for a short condensed state string, not the full history.")
    print("   The tradeoff: our code had to do the condensing/writing (the")
    print("   'engineering work of read and write logic' the lesson calls out).")


def demo_stateless_independent_jobs():
    """RIGHT scope for use case 2: independent one-shot jobs with no
    continuity requirement. No storage, no injected history — and a
    direct demonstration of the tradeoff it accepts: a follow-up that
    references a prior job gets no context at all."""
    print("\n" + "=" * 70)
    print("RIGHT SCOPE FOR USE CASE 2: stateless — independent formatting jobs")
    print("=" * 70)

    job_1 = "Reformat this into a bulleted list: 'apples, bananas, and pears; then oranges.'"
    r1 = client.messages.create(model=MODEL, max_tokens=100, messages=[{"role": "user", "content": job_1}])
    print_usage(r1)
    print(f"Job 1: {r1.content[0].text.strip()}")

    job_2_followup = "Add 'grapes' to the list from the previous job."
    r2 = client.messages.create(model=MODEL, max_tokens=100, messages=[{"role": "user", "content": job_2_followup}])
    print_usage(r2)
    print(f"Job 2 (new, unrelated session): {r2.content[0].text.strip()}")
    print("\n📝 Job 2 has no idea what 'the previous job' was — that's the cost")
    print("   stateless accepts. It's the RIGHT cost here because real formatting")
    print("   jobs in this use case don't reference each other; paying storage")
    print("   read/write overhead for continuity nothing needs would be waste.")


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Memory Scope — Matching Use Case to Scope, Live")
    print("=" * 70)

    demo_in_context_across_sessions()
    demo_external_storage_across_sessions()
    demo_stateless_independent_jobs()

    print("""
======================================================================
CHECKPOINT MAPPING
======================================================================
1. Support agent, same user, across daily sessions
   → External storage. In-context resets every session — day two would
     open as a first contact, forcing the user to re-explain everything.
     Demonstrated above: naive in-context input_tokens climbed every
     session; external storage held flat by re-injecting only condensed
     state.

2. Document formatter, independent one-shot jobs
   → Stateless. External storage would add read/write calls for
     continuity this use case never needs — nothing breaks, but every
     run pays a cost for state that's never reused.

3. Coding assistant, one long session that never continues
   → In-context. External storage is unnecessary overhead for a session
     that ends when the developer logs off, and a summarized layer would
     compress out exact code-level detail the developer still needs
     later in the SAME session.

The general lesson: "in-context" isn't inherently the wrong or right
choice — it's wrong for a use case shaped like #1 (state must survive
session boundaries) and right for one shaped like #3 (state never needs
to survive a boundary because there isn't one). Matching scope to shape
is a design-time decision; get it wrong and the fix under production
pressure is the same one-hour refactor the postmortem describes, just
done later and under a deadline.
""")


if __name__ == "__main__":
    main()
