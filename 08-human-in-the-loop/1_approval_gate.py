"""
EXAMPLE 1: Human-in-the-Loop — Gating a Dangerous Tool Call

Some tool calls are safe to auto-execute (read-only lookups). Others are
destructive or hard to reverse (deleting a resource, issuing a refund,
sending an email to a customer) and should pause for a human to approve
before your code actually runs them.

This example marks tools as "safe" or "dangerous" up front. Safe tools
execute immediately. Dangerous tools stop the loop, print exactly what
Claude wants to do, and wait for a (simulated) human decision before
either executing it or telling Claude the human declined.
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
        "name": "get_account_status",
        "description": "Look up whether an account is active, suspended, or closed.",
        "input_schema": {
            "type": "object",
            "properties": {"account_id": {"type": "string"}},
            "required": ["account_id"],
        },
    },
    {
        "name": "delete_account",
        "description": "Permanently delete an account and all its data. Irreversible.",
        "input_schema": {
            "type": "object",
            "properties": {"account_id": {"type": "string"}},
            "required": ["account_id"],
        },
    },
]

# The gate: which tools require a human to approve before executing.
DANGEROUS_TOOLS = {"delete_account"}


def execute_tool(name, tool_input):
    if name == "get_account_status":
        return f"Account {tool_input['account_id']}: status = closed, no activity in 3 years."
    if name == "delete_account":
        return f"Account {tool_input['account_id']} permanently deleted."
    return "unknown tool"


def ask_human_to_approve(tool_use):
    """Simulated human approval gate. In a real system this would block on
    a UI confirmation, a Slack approval, or a CLI prompt — not auto-approve."""
    print(f"\n🛑 APPROVAL REQUIRED: Claude wants to call {tool_use.name}({tool_use.input})")
    print("   This action is irreversible.")
    # Simulated decision — swap this for `input(...)` to make it interactive.
    decision = "approved"
    print(f"   Human decision (simulated): {decision}")
    return decision == "approved"


def run_loop(user_request):
    messages = [{"role": "user", "content": user_request}]

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
            print(f"Turn {turn}: final answer: {text!r}")
            break

        results = []
        for tool_use in tool_uses:
            if tool_use.name in DANGEROUS_TOOLS:
                if ask_human_to_approve(tool_use):
                    output = execute_tool(tool_use.name, tool_use.input)
                    print(f"   ✓ Executed after approval: {output}")
                else:
                    output = "Human declined this action. Do not retry it; ask the user for clarification instead."
                    print("   ✗ Declined — Claude will be told, not the executed result.")
            else:
                output = execute_tool(tool_use.name, tool_use.input)
                print(f"Turn {turn}: auto-executed {tool_use.name}({tool_use.input}) -> {output}")

            results.append({"type": "tool_result", "tool_use_id": tool_use.id, "content": output})

        messages.append({"role": "user", "content": results})


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Human-in-the-Loop — Approval Gate for Dangerous Actions")
    print("=" * 70)

    request = "Check account acct_5551's status, and if it's been inactive for over a year, delete it."
    print(f"\nRequest: {request!r}\n")
    run_loop(request)

    print("""
📝 Takeaway: the loop shape is identical to any other agent loop
(1_simple_loop.py in module 04) — the ONLY difference is one `if` check
before executing a tool: is this tool in DANGEROUS_TOOLS? Read-only or
easily-reversible tools (get_account_status) run immediately. Anything
irreversible (delete_account) pauses for a human decision BEFORE your
code executes it — not after, and not just before telling the user about
it. The gate lives in your application code, not in Claude's judgment —
Claude can still recommend the deletion, but it cannot cause it alone.
""")


if __name__ == "__main__":
    main()
