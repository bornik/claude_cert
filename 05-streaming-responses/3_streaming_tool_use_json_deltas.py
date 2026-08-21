"""
EXAMPLE 3: Streaming a Tool Call — Reconstructing input_json_delta Fragments

When Claude streams a tool call, the tool's input arguments don't arrive
as one JSON object. They arrive as a content block of type "tool_use"
whose input is built up over a series of content_block_delta events with
delta.type == "input_json_delta", each carrying a partial_json STRING
FRAGMENT — not a complete, independently-parseable JSON value. A fragment
can end mid-string, e.g. '{"city":"San' with the closing quote and brace
still to come in a later fragment.

This script reproduces exactly that failure and the fix:
  - demo_naive_parse_fails(): parses every partial_json fragment on its
    own, the instant it arrives. This throws on the first fragment for
    any argument longer than one chunk.
  - demo_correct_concatenation(): accumulates fragments in arrival order
    per content block, and only parses once, after content_block_stop.
  - demo_sdk_incremental_helper(): the same correctness, with no manual
    string-buffering at all — client.messages.stream()'s
    get_final_message() hands back a tool_use block whose .input is
    already a parsed dict.

Both (2) and (3) are the same underlying fix; (3) is what real code
should use, (2) exists to show what the SDK is doing for you.
"""

import json
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

MODEL = "claude-haiku-4-5"
PROMPT = "What's the weather in San Francisco?"
TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    }
]
# Forces the tool call so every run actually exercises input_json_delta,
# instead of leaving it up to the model whether to call a tool at all.
TOOL_CHOICE = {"type": "tool", "name": "get_weather"}


def demo_naive_parse_fails():
    print("\n" + "=" * 70)
    print("1. WRONG: parsing each partial_json fragment independently")
    print("=" * 70)
    print("(this is option 2 from the exam question — parse-then-merge)\n")

    fragment_count = 0
    first_failure = None

    with client.messages.create(
        model=MODEL,
        max_tokens=200,
        tools=TOOLS,
        tool_choice=TOOL_CHOICE,
        messages=[{"role": "user", "content": PROMPT}],
        stream=True,
    ) as stream:
        for event in stream:
            if event.type != "content_block_delta":
                continue
            if event.delta.type != "input_json_delta":
                continue
            fragment_count += 1
            fragment = event.delta.partial_json
            print(f"  fragment {fragment_count}: {fragment!r}")
            try:
                json.loads(fragment)
            except json.JSONDecodeError as e:
                if first_failure is None:
                    first_failure = (fragment, e)

    if first_failure:
        fragment, err = first_failure
        print(f"\n❌ json.loads({fragment!r}) raised: {err}")
        print(
            "Even the FIRST fragment alone isn't valid JSON to parse — "
            "there is nothing to 'merge after message_stop' here, because "
            "no individual fragment ever produced a parseable object in "
            "the first place. Option 2 fails before it can even start."
        )
    else:
        print(
            "\n(No fragment failed to parse on its own this run — the "
            "model happened to emit the whole thing in one chunk. Rerun "
            "it, or try a longer city name; chunking isn't guaranteed to "
            "split mid-string on every call, which is exactly why code "
            "that assumes each fragment IS the object is unsafe.)"
        )


def demo_correct_concatenation():
    print("\n" + "=" * 70)
    print("2. RIGHT (manual): concatenate fragments, parse once at content_block_stop")
    print("=" * 70)
    print("(this is the first half of the correct exam answer)\n")

    buffers = {}  # content block index -> accumulated JSON string
    block_meta = {}  # content block index -> {"name": ..., "id": ...}
    input_tokens = output_tokens = 0

    # Note: this uses the raw client.messages.create(stream=True) iterator,
    # NOT the client.messages.stream() helper — so there's no
    # get_final_message() here. Usage has to be read off message_start /
    # message_delta events directly, same as 2_streaming_with_progress.py.
    with client.messages.create(
        model=MODEL,
        max_tokens=200,
        tools=TOOLS,
        tool_choice=TOOL_CHOICE,
        messages=[{"role": "user", "content": PROMPT}],
        stream=True,
    ) as stream:
        for event in stream:
            if event.type == "content_block_start" and event.content_block.type == "tool_use":
                buffers[event.index] = ""
                block_meta[event.index] = {
                    "name": event.content_block.name,
                    "id": event.content_block.id,
                }

            elif event.type == "content_block_delta" and event.delta.type == "input_json_delta":
                buffers[event.index] += event.delta.partial_json

            elif event.type == "content_block_stop" and event.index in buffers:
                raw_json = buffers[event.index]
                tool_input = json.loads(raw_json)  # the full string, now valid
                meta = block_meta[event.index]
                print(f"✅ Reconstructed input for '{meta['name']}' (id={meta['id']}):")
                print(f"   raw accumulated string: {raw_json!r}")
                print(f"   parsed:                 {tool_input}")

            elif event.type == "message_start":
                input_tokens = event.message.usage.input_tokens
            elif event.type == "message_delta":
                if event.usage and event.usage.output_tokens is not None:
                    output_tokens = event.usage.output_tokens

    print(f"💰 Usage ({MODEL}): {input_tokens} in / {output_tokens} out")


def demo_sdk_incremental_helper():
    print("\n" + "=" * 70)
    print("3. RIGHT (SDK helper): no manual buffering at all")
    print("=" * 70)
    print("(this is the second half of the correct exam answer)\n")

    with client.messages.stream(
        model=MODEL,
        max_tokens=200,
        tools=TOOLS,
        tool_choice=TOOL_CHOICE,
        messages=[{"role": "user", "content": PROMPT}],
    ) as stream:
        for _ in stream:
            pass  # the SDK is accumulating input_json_delta fragments for us as these pass by
        final_message = stream.get_final_message()

    tool_use_block = next(b for b in final_message.content if b.type == "tool_use")
    print(f"final_message tool_use block: name={tool_use_block.name!r}")
    print(f"  .input is already a dict: {tool_use_block.input!r} (type={type(tool_use_block.input).__name__})")
    print(
        "\nWe never touched partial_json or json.loads() in this version — "
        "client.messages.stream()'s get_final_message() did the "
        "concatenate-then-parse work internally and handed back a normal "
        "tool_use block, .input already parsed."
    )
    print_usage(final_message, model=MODEL)


def explain_wrong_options():
    print("\n" + "=" * 70)
    print("Why the other two exam options don't work at all")
    print("=" * 70)
    print(
        "Option 3 (disable tools, get arguments as an ordinary text "
        "block): tool_choice/tools control whether Claude can call a "
        "tool at all. Turn tools off and there is no tool_use block and "
        "no input_json_delta to reconstruct — you'd get prose, not "
        "structured arguments; you would have solved a different problem, "
        "not this one.\n"
    )
    print(
        "Option 4 (ignore input_json_delta, use the final text response): "
        "a tool_use content block is not a text block. When Claude calls "
        "a tool, final_message.content holds a tool_use block with a "
        "structured .input — there generally isn't a plain-text block "
        "restating those same arguments to fall back to."
    )


def main():
    demo_naive_parse_fails()
    demo_correct_concatenation()
    demo_sdk_incremental_helper()
    explain_wrong_options()


if __name__ == "__main__":
    main()
