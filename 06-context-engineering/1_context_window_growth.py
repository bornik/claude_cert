"""
EXAMPLE 1: Context Window Growth in a Multi-Step Tool Loop

Every tool_result Claude receives gets appended to the context window and
stays there for the rest of the session — it is never automatically
removed. In a single-turn prompt this is invisible. In a multi-step agent
session running many tool calls in a row, the window fills up fast.

This example runs a tool-use loop that repeatedly calls a tool returning
a chunk of "log data" and prints input_tokens after every turn, so you
can watch the context window grow turn over turn — the actual mechanism
behind "the agent either compacts or stalls" once the window fills.
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
        "name": "fetch_log_chunk",
        "description": "Fetch the next chunk of application log lines to search for the error.",
        "input_schema": {
            "type": "object",
            "properties": {"chunk_id": {"type": "integer"}},
            "required": ["chunk_id"],
        },
    }
]

# Fake but sizable "log data" — big enough that repeated tool_results
# visibly grow input_tokens turn over turn.
FAKE_LOG_CHUNK = "\n".join(
    f"2026-08-08 10:{i:02d}:00 INFO worker-{i} processed job ok" for i in range(200)
)

MAX_TURNS = 5


def run_loop():
    messages = [
        {
            "role": "user",
            "content": (
                "Search the logs across as many chunks as you need (call "
                "fetch_log_chunk with increasing chunk_id) to find any ERROR "
                "line. If none appears after 4 chunks, report that none was found."
            ),
        }
    ]

    for turn in range(1, MAX_TURNS + 1):
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            tools=TOOLS,
            messages=messages,
        )
        print(f"\n--- Turn {turn} ---")
        print_usage(response)

        messages.append({"role": "assistant", "content": response.content})

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            text = next((b.text for b in response.content if b.type == "text"), "")
            print(f"Final answer: {text!r}")
            break

        tool_results = []
        for tool_use in tool_uses:
            print(f"Called: {tool_use.name}({tool_use.input})")
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": f"Chunk {tool_use.input.get('chunk_id')}:\n{FAKE_LOG_CHUNK}",
                }
            )
        messages.append({"role": "user", "content": tool_results})


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Context Window Growth in a Multi-Step Tool Loop")
    print("=" * 70)
    run_loop()

    print("""
📝 Takeaway: watch the input_tokens number in the 💰 Usage line above —
it climbs every turn, because each fetch_log_chunk tool_result gets
appended to `messages` and resent in FULL on every subsequent call. None
of the earlier chunks are ever dropped by the API automatically. A real
agent doing 10-20 of these tool calls (not 5) will burn through a
meaningful fraction of the context window on tool results alone — that's
the concrete mechanism behind "the window fills up fast" from the lesson.
""")


if __name__ == "__main__":
    main()
