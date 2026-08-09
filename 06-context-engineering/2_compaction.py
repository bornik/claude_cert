"""
EXAMPLE 2: Compaction — Summarizing Tool Results Instead of Keeping Them Raw

Example 1 showed input_tokens growing every turn because each raw
tool_result stays in `messages` forever. Compaction is the fix: once a
tool_result has served its purpose, replace it with a short summary
before the next API call, instead of carrying the full payload forward.

This runs the SAME log-search task as example 1, but after each tool
call, replaces the raw chunk in history with a one-line summary
("chunk 0: no errors") rather than keeping the full log text. Compare
the final input_tokens number to example 1's.
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

FAKE_LOG_CHUNK = "\n".join(
    f"2026-08-08 10:{i:02d}:00 INFO worker-{i} processed job ok" for i in range(200)
)

MAX_TURNS = 5


def summarize(chunk_id, raw_chunk_text):
    """Compaction step: collapse a large tool_result down to the one fact
    that matters for the task (does this chunk contain an ERROR line?)."""
    has_error = "ERROR" in raw_chunk_text
    return f"Chunk {chunk_id}: {'ERROR line found' if has_error else 'no errors, all INFO'}"


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
            chunk_id = tool_use.input.get("chunk_id")
            print(f"Called: {tool_use.name}({tool_use.input})")
            # Compaction: we never put FAKE_LOG_CHUNK itself into history —
            # only the summarized fact Claude actually needs going forward.
            summary = summarize(chunk_id, FAKE_LOG_CHUNK)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": summary,
                }
            )
        messages.append({"role": "user", "content": tool_results})


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Compaction — Summarize Tool Results Before They Persist")
    print("=" * 70)
    run_loop()

    print("""
📝 Takeaway: compare the input_tokens growth here to 1_context_window_growth.py.
Same task, same number of tool calls — but here each tool_result is ~10
tokens ("Chunk 2: no errors...") instead of a multi-hundred-token raw log
dump, so input_tokens barely grows turn over turn.

The tradeoff is real, though: compaction only works if the summary keeps
everything the LATER steps of the task actually need. Here we only needed
a yes/no per chunk. If a later step needed to quote an exact log line, a
too-aggressive summary would silently throw away the answer — compaction
is a deliberate choice about what's safe to drop, not a free win.
""")


if __name__ == "__main__":
    main()
