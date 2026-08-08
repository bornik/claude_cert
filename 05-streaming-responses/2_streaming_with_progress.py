"""
EXAMPLE 2: Streaming Responses — Raw Events and Progress Tracking

Below the text_stream helper is a raw event stream you can inspect directly.
This shows the event types Claude sends and how to track token usage as it
grows during generation.

Key event types: message_start, content_block_delta (the actual text
chunks), message_delta (usage updates), message_stop.
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Streaming — Raw Events and Progress")
    print("=" * 70)

    print("\n📨 Prompt: List 5 tips for writing clean code.\n")

    event_counts = {}
    output_tokens = 0

    with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": "List 5 tips for writing clean code."}],
    ) as stream:
        for event in stream:
            event_counts[event.type] = event_counts.get(event.type, 0) + 1

            if event.type == "content_block_delta" and event.delta.type == "text_delta":
                print(event.delta.text, end="", flush=True)

            elif event.type == "message_delta":
                if event.usage and event.usage.output_tokens is not None:
                    output_tokens = event.usage.output_tokens

    print(f"\n\n📊 Event counts: {event_counts}")
    print(f"📊 Final output tokens: {output_tokens}")


if __name__ == "__main__":
    main()
