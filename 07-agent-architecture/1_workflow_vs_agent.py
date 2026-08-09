"""
EXAMPLE 1: Workflow vs. Agent

A "workflow" is code you write that calls Claude at fixed, predetermined
steps — the control flow is yours. An "agent" hands control flow to
Claude itself: it decides which tool to call next and when it's done,
in a loop that keeps going until Claude stops asking for tools.

Same task (classify a ticket, then look up the account, then decide
whether to escalate), implemented both ways, so the structural
difference is visible in the code, not just described in prose.
"""

import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

TICKET = "My payment failed three times and I was still charged each time. Account: acct_9001."

TOOLS = [
    {
        "name": "lookup_account",
        "description": "Look up billing details for an account by account id.",
        "input_schema": {
            "type": "object",
            "properties": {"account_id": {"type": "string"}},
            "required": ["account_id"],
        },
    },
    {
        "name": "escalate_to_billing_team",
        "description": "Escalate a confirmed billing issue to the human billing team.",
        "input_schema": {
            "type": "object",
            "properties": {"account_id": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["account_id", "reason"],
        },
    },
]


def execute_tool(name, tool_input):
    """Fake tool execution — stands in for real account/billing systems."""
    if name == "lookup_account":
        return f"Account {tool_input['account_id']}: 3 failed payment attempts, all 3 charged anyway. Total overcharge: $87."
    if name == "escalate_to_billing_team":
        return f"Escalated account {tool_input['account_id']} to billing team: {tool_input['reason']}"
    return "unknown tool"


def run_as_workflow():
    """WORKFLOW: fixed steps, decided by OUR code, not by Claude."""
    print("\n" + "=" * 70)
    print("APPROACH 1: Workflow (we decide the steps)")
    print("=" * 70)

    # Step 1 — classify (our code decides to call the classifier)
    classify = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        messages=[{"role": "user", "content": f"In one word, is this a billing issue or a technical issue? Ticket: {TICKET}"}],
    )
    print_usage(classify)
    category = classify.content[0].text.strip()
    print(f"Step 1 (our code called this): category = {category!r}")

    # Step 2 — our code decides: billing issues always get an account lookup
    account_info = execute_tool("lookup_account", {"account_id": "acct_9001"})
    print(f"Step 2 (our code called this, unconditionally): {account_info}")

    # Step 3 — our code decides: always escalate billing issues with overcharge
    result = execute_tool("escalate_to_billing_team", {"account_id": "acct_9001", "reason": account_info})
    print(f"Step 3 (our code called this, unconditionally): {result}")

    print("\n📝 Claude only ever answered a question — it never chose which tool to call or when to stop.")


def run_as_agent():
    """AGENT: Claude decides which tool to call and when it's done."""
    print("\n" + "=" * 70)
    print("APPROACH 2: Agent (Claude decides the steps)")
    print("=" * 70)

    messages = [
        {
            "role": "user",
            "content": (
                f"Handle this support ticket: {TICKET}\n"
                "Look up whatever account information you need, and escalate to the "
                "billing team only if you find a confirmed overcharge. Explain your "
                "final decision in one sentence."
            ),
        }
    ]

    for turn in range(1, 5):
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=400,
            tools=TOOLS,
            messages=messages,
        )
        print_usage(response)
        messages.append({"role": "assistant", "content": response.content})

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            text = next((b.text for b in response.content if b.type == "text"), "")
            print(f"Turn {turn}: Claude decided it was done. Final answer: {text!r}")
            break

        results = []
        for tool_use in tool_uses:
            print(f"Turn {turn}: Claude decided to call {tool_use.name}({tool_use.input})")
            output = execute_tool(tool_use.name, tool_use.input)
            results.append({"type": "tool_result", "tool_use_id": tool_use.id, "content": output})
        messages.append({"role": "user", "content": results})

    print("\n📝 We never told Claude to call lookup_account or escalate_to_billing_team —")
    print("   it chose both the sequence and the stopping point itself.")


def main():
    run_as_workflow()
    run_as_agent()

    print("""
======================================================================
KEY TAKEAWAY
======================================================================
Workflow: our Python code decided every step in advance (classify →
lookup → escalate, always in that order, always all three). Predictable,
cheap to reason about, but can't handle a case the code didn't anticipate
(e.g. a ticket where escalation ISN'T warranted).

Agent: Claude decided which tools to call, in what order, and when the
task was complete, based on what it actually found. More flexible, but
its behavior is less predictable and its stopping condition
(`stop_reason != "tool_use"`) is something you must trust or verify.

Use a workflow when the steps are always the same. Use an agent when the
right sequence of steps genuinely depends on what earlier steps find out.
""")


if __name__ == "__main__":
    main()
