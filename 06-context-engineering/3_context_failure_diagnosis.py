"""
EXAMPLE 3: Diagnose the Context Failure — Degrading Tool Selection

Reproduces the certification checkpoint scenario: an agent correctly
calls fetch_policy_document across several turns, each returning a large
result. By the time the task actually needs apply_coverage_rule, tool
selection degrades — Claude falls back to search_knowledge_base instead.

The checkpoint's diagnosis: this isn't a schema problem (the same tools
were selected correctly in turns 1-4) and it isn't a max_tokens problem
(there's room to respond) — it's accumulated context from large tool
results crowding out the current instructions by the time the critical
turn arrives. The fix is pruning/compaction of old tool results BEFORE
the turn that needs a precise tool choice, not a schema rewrite.

This script runs the SAME task two ways: once letting every large
fetch_policy_document result accumulate in full, and once pruning each
one down to a short summary right after it's used. We compare whether
Claude reaches for apply_coverage_rule correctly at the end.
"""

import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

TOOLS = [
    {
        "name": "fetch_policy_document",
        "description": "Fetch the full text of an insurance policy document by policy number.",
        "input_schema": {
            "type": "object",
            "properties": {"policy_number": {"type": "string"}},
            "required": ["policy_number"],
        },
    },
    {
        "name": "apply_coverage_rule",
        "description": "Apply the coverage rule engine to a specific claim, using policy terms already retrieved in this session, to determine whether the claim is covered.",
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_number": {"type": "string"},
                "claim_description": {"type": "string"},
            },
            "required": ["policy_number", "claim_description"],
        },
    },
    {
        "name": "search_knowledge_base",
        "description": "Search general help-center articles about insurance concepts and terminology.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]

POLICY_NUMBERS = ["POL-1001", "POL-1002", "POL-1003", "POL-1004"]

# A large-ish fake policy document — big enough that 4 of them accumulating
# raw genuinely crowds the context window, mirroring the checkpoint's
# "2,400 tokens per turn" trace.
FAKE_POLICY_TEXT = "\n".join(
    f"Section {i}: Standard exclusions and terms clause {i} apply to this policy under "
    f"general provisions, subject to state-specific riders and amendment schedules."
    for i in range(150)
)

FINAL_CLAIM_REQUEST = (
    "Now determine whether this claim is covered under POL-1004: water damage from "
    "a burst pipe in the kitchen. Use the coverage rule engine on the policy terms "
    "you already have — don't just search generic articles about it."
)


def build_initial_turns(prune):
    """Runs 4 fetch_policy_document calls, either keeping full results
    (prune=False) or replacing each with a short summary (prune=True)."""
    messages = [
        {
            "role": "user",
            "content": (
                "Fetch the policy documents for these policy numbers, one at a time: "
                + ", ".join(POLICY_NUMBERS)
            ),
        }
    ]

    for turn in range(1, 5):
        response = client.messages.create(
            model="claude-haiku-4-5", max_tokens=300, tools=TOOLS, messages=messages
        )
        print_usage(response)
        messages.append({"role": "assistant", "content": response.content})

        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_use:
            break

        policy_number = tool_use.input.get("policy_number", POLICY_NUMBERS[turn - 1])
        print(f"  Turn {turn}: called {tool_use.name}({tool_use.input})")

        if prune:
            content = f"{policy_number}: standard terms, no unusual exclusions (summarized)."
        else:
            content = f"Policy {policy_number} full text:\n{FAKE_POLICY_TEXT}"

        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": tool_use.id, "content": content}
                ],
            }
        )

    return messages


def run_scenario(label, prune):
    print("\n" + "=" * 70)
    print(f"{label}")
    print("=" * 70)

    messages = build_initial_turns(prune)
    messages.append({"role": "user", "content": FINAL_CLAIM_REQUEST})

    response = client.messages.create(
        model="claude-haiku-4-5", max_tokens=300, tools=TOOLS, messages=messages
    )
    print_usage(response)

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use:
        correct = tool_use.name == "apply_coverage_rule"
        marker = "✓ correct" if correct else "❌ WRONG tool"
        print(f"Final turn: called {tool_use.name}({tool_use.input}) — {marker}")
        return correct
    else:
        text = next((b.text for b in response.content if b.type == "text"), "")
        print(f"Final turn: no tool call, answered directly: {text!r} — ❌ (should have called a tool)")
        return False


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Diagnose the Context Failure")
    print("=" * 70)

    unpruned_correct = run_scenario(
        "Scenario A: 4 raw policy documents accumulate in full (no pruning)", prune=False
    )
    pruned_correct = run_scenario(
        "Scenario B: each policy document pruned to a summary right after use", prune=True
    )

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Unpruned (Scenario A) picked apply_coverage_rule correctly: {unpruned_correct}")
    print(f"Pruned   (Scenario B) picked apply_coverage_rule correctly: {pruned_correct}")

    print("""
📝 Takeaway (from the checkpoint): tool selection degrading after several
turns of CORRECT selection is not a schema problem — the schema and
descriptions here never changed between scenarios. It's accumulated raw
tool-result context (four ~2000+ token policy dumps) crowding out the
final instruction by the time a precise tool choice mattered. The fix is
pruning/compacting old tool results before they pile up — not rewriting
apply_coverage_rule's description and not raising max_tokens.

Honesty note: claude-haiku-4-5 may or may not reproduce the exact
degradation on every run — model robustness varies. If both scenarios
above picked correctly, that doesn't invalidate the mechanism; it means
this run's accumulated context (a few hundred tokens x4) wasn't yet large
enough to reach the tipping point the checkpoint describes at real scale
(thousands of tokens across many more turns). Try increasing FAKE_POLICY_TEXT
or POLICY_NUMBERS to push it further if you want to see it break here.
""")


if __name__ == "__main__":
    main()
