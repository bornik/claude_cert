"""
EXAMPLE 2: HITL Insertion Points — Not Just "Before a Destructive Call"

1_approval_gate.py covers one insertion point: pausing before a
destructive tool call. The lesson names two more, each addressing a
different risk:

  - After a planning step: the agent has generated a plan and is about
    to start executing it. Risk: an incorrect plan that would produce
    the wrong outcome even if every step executes correctly.
  - On unexpected output: a tool result contains an error flag, an empty
    result, or a value outside expected bounds. Risk: failure modes that
    retry logic alone won't resolve.

This example runs a small "refund investigation" agent and exercises
both checkpoints live: one where Claude's plan is shown to a human
before any tool executes, and one where a tool deliberately returns an
out-of-bounds value that triggers a human check instead of auto-continuing.
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
        "name": "make_plan",
        "description": "Propose a step-by-step plan for investigating and resolving a refund request, before executing any of it.",
        "input_schema": {
            "type": "object",
            "properties": {"steps": {"type": "array", "items": {"type": "string"}}},
            "required": ["steps"],
        },
    },
    {
        "name": "get_refund_amount",
        "description": "Look up the amount to refund for a given order.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "issue_refund",
        "description": "Issue a refund for the given order and amount.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}},
            "required": ["order_id", "amount"],
        },
    },
]

# A refund amount that's WAY outside a sane bound for this order — the
# "unexpected output" trigger. In a real system this might be a bug in
# the upstream service, a data-corruption issue, or a sign of fraud.
UNEXPECTED_REFUND_AMOUNT = 48000.00
REASONABLE_UPPER_BOUND = 500.00


def ask_human(prompt):
    try:
        decision = input(f"   {prompt} [y/N]: ").strip().lower()
    except EOFError:
        print("   (no input available — defaulting to decline)")
        decision = "n"
    return decision == "y"


def approve_plan(steps):
    """Insertion point: after a planning step, before execution begins."""
    print("\n🛑 PLAN REVIEW (before any tool executes):")
    for i, step in enumerate(steps, 1):
        print(f"   {i}. {step}")
    approved = ask_human("Approve this plan?")
    print(f"   Human decision: {'approved' if approved else 'rejected'}")
    return approved


def flag_unexpected_output(order_id, amount):
    """Insertion point: on unexpected output — a value outside expected bounds."""
    if amount > REASONABLE_UPPER_BOUND:
        print(f"\n🛑 UNEXPECTED OUTPUT: refund amount ${amount:.2f} for {order_id} exceeds "
              f"the ${REASONABLE_UPPER_BOUND:.2f} sanity bound for this account tier.")
        approved = ask_human("Approve this refund anyway?")
        print(f"   Human decision: {'approve anyway' if approved else 'block'}")
        return approved
    return True  # within bounds, no human check needed


def run():
    messages = [
        {
            "role": "user",
            "content": (
                "Handle a refund request for order ORD-4471. First propose your plan, "
                "then look up the refund amount, then issue the refund."
            ),
        }
    ]

    for turn in range(1, 6):
        response = client.messages.create(
            model="claude-haiku-4-5", max_tokens=400, tools=TOOLS, messages=messages
        )
        print_usage(response)
        messages.append({"role": "assistant", "content": response.content})

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            text = next((b.text for b in response.content if b.type == "text"), "")
            print(f"Turn {turn}: final answer: {text!r}")
            break

        results = []
        for tool_use in tool_uses:
            if tool_use.name == "make_plan":
                approve_plan(tool_use.input["steps"])
                output = "Plan approved by human reviewer. Proceed."

            elif tool_use.name == "get_refund_amount":
                # Deliberately return an out-of-bounds amount to exercise
                # the "unexpected output" checkpoint.
                output = f"Refund amount for {tool_use.input['order_id']}: ${UNEXPECTED_REFUND_AMOUNT:.2f}"
                print(f"Turn {turn}: called get_refund_amount -> {output}")

            elif tool_use.name == "issue_refund":
                amount = tool_use.input["amount"]
                order_id = tool_use.input["order_id"]
                if flag_unexpected_output(order_id, amount):
                    output = f"Refund of ${amount:.2f} issued for {order_id}."
                    print(f"   ✓ Executed: {output}")
                else:
                    output = "Human blocked this refund pending manual review. Do not retry automatically."
                    print("   ✗ Blocked.")
            else:
                output = "unknown tool"

            results.append({"type": "tool_result", "tool_use_id": tool_use.id, "content": output})

        messages.append({"role": "user", "content": results})


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 2: HITL Insertion Points — Planning and Unexpected Output")
    print("=" * 70)
    run()

    print("""
📝 Takeaway: two insertion points beyond "before a destructive call":
  - After planning, before execution: catches a WRONG PLAN even if every
    step would later execute correctly — the check happens before any
    tool call, not after the damage from a bad plan is already underway.
  - On unexpected output: `flag_unexpected_output()` doesn't trust the
    tool result at face value — it checks the value against a sanity
    bound BEFORE letting the agent act on it. A retry would have just
    gotten the same bad number back; only a bounds check catches it.
Both checks live in application code around the tool execution, not in
a system-prompt instruction asking Claude to "be careful" — the model
cannot enforce a guarantee about its own output; your code can.
""")


if __name__ == "__main__":
    main()
