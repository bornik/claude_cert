"""
EXAMPLE 6: The Boundary-Case Failure — "Why does Claude keep calling
search_docs when the answer is already in the context?"

This reproduces the exact diagnostic scenario from the lesson: two tools
whose descriptions both just say "find information" — search_docs (look up
new content) and get_context_summary (retrieve something already in this
session). A schema like this can pass every happy-path test and still fail
the moment a question lands near the boundary between the two tools.

The boundary case here: the answer to the user's question is ALREADY in
the conversation history. A well-designed schema should make Claude prefer
get_context_summary (or answer directly, no tool needed) instead of
re-searching. We test this live, then apply the fix from the lesson — one
exclusion sentence per tool — and check again.
"""

import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

# The conversation already contains the answer — this is the boundary case.
CONVERSATION = [
    {"role": "user", "content": "What's our refund window?"},
    {"role": "assistant", "content": "Our refund window is 30 days from the purchase date."},
    {"role": "user", "content": "And how many days is the refund window, again?"},
]

OVERLAPPING_TOOLS = [
    {
        "name": "search_docs",
        "description": "Use this to find information about the product.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_context_summary",
        "description": "Use this to retrieve relevant information from the current session.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]

# The fix from the lesson: one exclusion sentence per tool, naming the boundary.
FIXED_TOOLS = [
    {
        "name": "search_docs",
        "description": (
            "Use this to find information about the product, when the user asks a "
            "question that requires looking up content not already present in this "
            "conversation. Do not call this if the answer is available in the "
            "current session context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_context_summary",
        "description": (
            "Retrieve relevant information from the current session. Only use this "
            "if the answer is already present in the current session. Do not use "
            "this to look up new information."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


def ask(tools, tool_choice):
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        tools=tools,
        tool_choice=tool_choice,
        messages=CONVERSATION,
    )
    print_usage(response)
    tool_call = next((b for b in response.content if b.type == "tool_use"), None)
    text = next((b.text for b in response.content if b.type == "text"), None)
    return tool_call, text


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 6: The Boundary-Case Failure")
    print("=" * 70)

    print("\nConversation so far:")
    for msg in CONVERSATION:
        print(f"  {msg['role']}: {msg['content']}")

    print("\n(The refund window was already answered above — this is the boundary case.)")

    print("\n--- Round 1: tool_choice='auto' (Claude may skip tools entirely) ---")
    for label, tools in [("❌ Overlapping descriptions", OVERLAPPING_TOOLS), ("✓ With exclusion sentences", FIXED_TOOLS)]:
        tool_call, text = ask(tools, {"type": "auto"})
        if tool_call:
            print(f"{label}: called {tool_call.name}({tool_call.input})")
        else:
            print(f"{label}: answered directly, no tool call: {text!r}")

    print("\n--- Round 2: tool_choice='any' (forced to pick a tool — many production")
    print("    agents force this, so this is the case that actually breaks in the wild) ---")
    for label, tools in [("❌ Overlapping descriptions", OVERLAPPING_TOOLS), ("✓ With exclusion sentences", FIXED_TOOLS)]:
        tool_call, text = ask(tools, {"type": "any"})
        print(f"{label}: called {tool_call.name}({tool_call.input})")
        if tool_call.name == "search_docs":
            print("   ⚠️  Re-searched for something it already knew — the exact bug from the lesson.")

    print("""
📝 Takeaway: "Use this to find information" and "Use this to retrieve
information" are the same instruction from Claude's perspective — nothing
tells it when NOT to call each one. One exclusion sentence per tool (naming
the boundary) is usually the whole fix. If the boundary still can't be
drawn cleanly, the two tools may need to be merged into one with a
parameter instead.

Note on this run: claude-haiku-4-5 handled this particular short, clean
conversation correctly even with the overlapping descriptions — its tool
NAMES (search_docs vs get_context_summary) already hint at the distinction,
and the context here is small and unambiguous. The failure from the lesson
is real, but it shows up more reliably with longer/noisier conversation
history, more similar tool names, or a less capable model — not on every
short toy example. That's exactly why "it passed my tests" isn't proof a
schema is safe: try pushing this example toward failure yourself — longer
history, near-identical tool names, or a query with less obvious phrasing.
""")


if __name__ == "__main__":
    main()
