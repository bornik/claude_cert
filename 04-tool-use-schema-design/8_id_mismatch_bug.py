"""
EXAMPLE 8: Spot and Fix the Schema Bug — Mismatched tool_use_id

Reproduces the certification checkpoint scenario live: an agent calls a
tool, gets a result back, and the NEXT API call fails with a validation
error — even though the schema is valid, the description is specific,
and the tool_result content itself is correct.

The bug: tool_use and tool_result blocks are matched by id, not by
position. If the tool_result's tool_use_id doesn't exactly match the id
on the assistant's tool_use block, the API treats it as a reference to a
tool_use that doesn't exist in the conversation at all.

One convention this relies on: tool_result blocks are sent in the
`user` role even though your application (not a person) generated the
content — `role` marks who is sending the message TO Claude, not who
authored it.
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
        "name": "get_account_balance",
        "description": "Look up the current balance for a bank account by its account ID.",
        "input_schema": {
            "type": "object",
            "properties": {"account_id": {"type": "string"}},
            "required": ["account_id"],
        },
    }
]

QUESTION = "What is the current balance for account A-4471?"


def get_real_tool_use_id():
    """Turn 1-2 of the trace: ask the question, get back the real tool_use
    block Claude actually issued, so we know the correct id to (mis)use."""
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        tools=TOOLS,
        messages=[{"role": "user", "content": QUESTION}],
    )
    print_usage(response)
    tool_use = next(b for b in response.content if b.type == "tool_use")
    print(f"Assistant issued tool_use id: {tool_use.id!r}")
    return response, tool_use


def try_broken_id(response, tool_use):
    """Turn 3-4 of the trace: send a tool_result with a WRONG tool_use_id
    (position-based guess instead of the real one) and watch it fail."""
    print("\n--- Broken: tool_result references a made-up id ---")
    fake_id = "toolu_02"  # deliberately wrong, mirrors the checkpoint trace
    print(f"Real id from Turn 2: {tool_use.id!r}")
    print(f"id we're (wrongly) using in the tool_result: {fake_id!r}")

    messages = [
        {"role": "user", "content": QUESTION},
        {"role": "assistant", "content": response.content},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": fake_id,
                    "content": "Balance: $1,240.18",
                }
            ],
        },
    ]

    try:
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            tools=TOOLS,
            messages=messages,
        )
        print("(unexpected: this call succeeded)")
    except Exception as e:
        print(f"❌ API rejected it: {e}")


def try_fixed_id(response, tool_use):
    """The fix: tool_use_id must match the assistant's tool_use.id exactly."""
    print("\n--- Fixed: tool_result references the REAL tool_use_id ---")
    messages = [
        {"role": "user", "content": QUESTION},
        {"role": "assistant", "content": response.content},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,  # matches exactly
                    "content": "Balance: $1,240.18",
                }
            ],
        },
    ]

    final = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        tools=TOOLS,
        messages=messages,
    )
    print_usage(final)
    text = next((b.text for b in final.content if b.type == "text"), None)
    print(f"✓ Success — Claude's final answer: {text!r}")


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Spot and Fix the Schema Bug — Mismatched tool_use_id")
    print("=" * 70)
    print(f"\nQuestion: {QUESTION!r}")

    response, tool_use = get_real_tool_use_id()
    try_broken_id(response, tool_use)
    try_fixed_id(response, tool_use)

    print("""
📝 Takeaway: tool_use and tool_result are matched by id, NOT by position
in the conversation. A tool_result with the wrong tool_use_id isn't a
"slightly wrong" result — the API treats it as a reference to a tool_use
that doesn't exist at all, and rejects the whole request. The schema,
description, and tool_result content can all be perfectly correct; this
bug lives purely in the id plumbing between turns.

Reminder: tool_result blocks are sent with role="user" even though your
application generated the content, not a person — role marks who is
sending the message to Claude, not who authored it.
""")


if __name__ == "__main__":
    main()
